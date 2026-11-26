"""Le site vu par satellite : indices spectraux Sentinel-2 par parcelle de l'emprise, comparés au voisinage.

Données : Copernicus Sentinel-2 niveau 2A (ESA), cloud-optimised GeoTIFF en open data sur AWS, catalogue STAC
Earth Search (Element 84). Réflectance = valeur × 0,0001 : le décalage BOA introduit par l'ESA en 2022 est déjà
retiré dans cette collection (Element84/earth-search, ticket GitHub n° 71), et les valeurs lues le confirment.
Nuages : masque de classification de scène (SCL) ; seuls les pixels « végétation », « sol non végétalisé » et « eau »
sont gardés.
Formules : catalogue « Awesome Spectral Indices » (Montero et al., 2023, Scientific Data 10:197,
doi:10.1038/s41597-023-02096-0).

Les règles d'interprétation (sol nu probable, cycles de végétation) sont des repères indicatifs de l'outil, affichés
comme tels : elles aident la lecture, elles ne remplacent pas l'observation de terrain.
"""
from __future__ import annotations

import io
import json
import math
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import geopandas as gpd
import numpy as np
import pandas as pd

from .http import DataSourceError, disk_cache

STAC_URL = "https://earth-search.aws.element84.com/v1"
COLLECTION = "sentinel-2-l2a"
ECHELLE = 1e-4
SCL_VALIDES = (4, 5, 6)  # végétation, sol non végétalisé, eau (nuages, ombres, cirrus et neige écartés)
ASSETS = {"B": "blue", "G": "green", "R": "red", "N": "nir", "S1": "swir16"}
RES = 10.0  # mètres
SEUIL_VALIDE = 0.6  # part minimale de pixels non nuageux sur l'emprise pour garder une date


@dataclass(frozen=True)
class Indice:
    code: str
    nom: str
    formule: str
    bandes: str
    montre: str
    lecture: str
    limites: str
    reference: str
    vmin: float
    vmax: float


INDICES: dict[str, Indice] = {
    "NDVI": Indice(
        "NDVI", "Indice de végétation par différence normalisée", "(PIR − Rouge) / (PIR + Rouge)", "(B08 − B04) / (B08 + B04)",
        "La quantité de végétation verte et active.",
        "Proche de 0 ou négatif : sol nu, bâti ou eau ; il monte quand la culture lève et culmine à la floraison, "
        "puis redescend à la maturité et à la récolte. Une courbe en cloche par an signe une culture annuelle ; "
        "une courbe haute toute l'année, une prairie.",
        "Sature sur les couverts très denses ; sensible au sol visible quand la végétation est clairsemée.",
        "Rouse et al. (1974), NASA, https://ntrs.nasa.gov/citations/19740022614", -0.2, 1.0),
    "BSI": Indice(
        "BSI", "Indice de sol nu (Bare Soil Index)", "((SWIR1 + Rouge) − (PIR + Bleu)) / ((SWIR1 + Rouge) + (PIR + Bleu))",
        "((B11 + B04) − (B08 + B02)) / ((B11 + B04) + (B08 + B02))",
        "Les périodes où le sol est découvert : labour, semis, après récolte, interculture nue.",
        "Positif : le sol domine ; négatif : la végétation domine. Combiné à un NDVI bas, il signale un sol nu.",
        "Les sols humides ou sombres le font baisser ; à interpréter avec le NDVI.",
        "Rikimaru et al. (2002), « BI » dans le catalogue Awesome Spectral Indices", -0.6, 0.4),
    "NDMI": Indice(
        "NDMI", "Indice d'humidité par différence normalisée (NDWI de Gao)", "(PIR − SWIR1) / (PIR + SWIR1)", "(B08 − B11) / (B08 + B11)",
        "L'eau contenue dans la végétation : un couvert bien alimenté ou en stress hydrique.",
        "Élevé : végétation riche en eau ; bas ou négatif en été : stress hydrique ou sol nu sec. Comparer les parcelles "
        "entre elles à la même date, plutôt que lire une valeur absolue.",
        "Dépend du couvert : sans végétation, il reflète surtout l'humidité de surface du sol.",
        "Wilson et Sader (2002), https://doi.org/10.1016/S0034-4257(01)00318-2", -0.6, 0.7),
    "MNDWI": Indice(
        "MNDWI", "Indice d'eau modifié", "(Vert − SWIR1) / (Vert + SWIR1)", "(B03 − B11) / (B03 + B11)",
        "L'eau libre en surface : mares, stagnation, inondation.",
        "Positif : eau libre probable ; négatif : sol ou végétation. Quelques dates positives sur une parcelle signalent "
        "une stagnation d'eau ou une inondation.",
        "Résolution de 20 m pour le SWIR : les petites surfaces en eau peuvent échapper au calcul.",
        "Xu (2006), https://doi.org/10.1080/01431160600589179", -0.8, 0.6),
}


def calcul_indices(b: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """Indices à partir des réflectances (B, G, R, N, S1)."""
    with np.errstate(divide="ignore", invalid="ignore"):
        return {
            "NDVI": (b["N"] - b["R"]) / (b["N"] + b["R"]),
            "BSI": ((b["S1"] + b["R"]) - (b["N"] + b["B"])) / ((b["S1"] + b["R"]) + (b["N"] + b["B"])),
            "NDMI": (b["N"] - b["S1"]) / (b["N"] + b["S1"]),
            "MNDWI": (b["G"] - b["S1"]) / (b["G"] + b["S1"]),
        }


# ---------------------------------------------------------------------------
# Catalogue et lecture des images
# ---------------------------------------------------------------------------

@disk_cache("s2")
def rechercher(bbox4326: tuple[float, float, float, float], debut: str, fin: str, nuage_max: float = 60.0) -> list[dict]:
    """Images Sentinel-2 L2A couvrant entièrement la zone, une par date (la moins nuageuse)."""
    import pystac_client
    from shapely.geometry import box, shape

    try:
        cli = pystac_client.Client.open(STAC_URL)
        items = list(cli.search(collections=[COLLECTION], bbox=list(bbox4326), datetime=f"{debut}/{fin}",
                                query={"eo:cloud_cover": {"lt": nuage_max}}, max_items=None).items())
    except Exception as e:  # service indisponible ou réseau
        raise DataSourceError(f"Catalogue Sentinel-2 (Earth Search) indisponible : {e}") from e
    zone = box(*bbox4326)
    par_date: dict[str, dict] = {}
    for it in items:
        if not shape(it.geometry).contains(zone):
            continue
        d = it.datetime.date().isoformat()
        cc = float(it.properties.get("eo:cloud_cover", 100))
        if d not in par_date or cc < par_date[d]["nuages"]:
            par_date[d] = {"id": it.id, "date": d, "nuages": cc, "crs": it.properties.get("proj:code") or f"EPSG:{it.properties.get('proj:epsg')}",
                           "hrefs": {k: it.assets[v].href for k, v in {**ASSETS, "SCL": "scl"}.items()}}
    return [par_date[d] for d in sorted(par_date)]


def _grille(bbox4326, crs):
    from pyproj import Transformer

    tr = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    xs, ys = tr.transform([bbox4326[0], bbox4326[2], bbox4326[0], bbox4326[2]], [bbox4326[1], bbox4326[1], bbox4326[3], bbox4326[3]])
    minx, maxx = math.floor(min(xs) / RES) * RES, math.ceil(max(xs) / RES) * RES
    miny, maxy = math.floor(min(ys) / RES) * RES, math.ceil(max(ys) / RES) * RES
    return (minx, miny, maxx, maxy), (int((maxy - miny) / RES), int((maxx - minx) / RES))


def _lire(href: str, bounds, shape) -> np.ndarray:
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.windows import from_bounds

    with rasterio.Env(AWS_NO_SIGN_REQUEST="YES", GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_MAX_RETRY="3",
                      GDAL_HTTP_RETRY_DELAY="1", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif"):
        with rasterio.open(href) as src:
            w = from_bounds(*bounds, transform=src.transform)
            return src.read(1, window=w, out_shape=shape, resampling=Resampling.nearest, boundless=True, fill_value=0)


def _rasteriser(zones: gpd.GeoDataFrame, crs, bounds, shape) -> tuple[np.ndarray, list[str]]:
    from rasterio.features import rasterize
    from rasterio.transform import from_origin

    z = zones.to_crs(crs)
    ids = list(z["zone"])
    tr = from_origin(bounds[0], bounds[3], RES, RES)
    formes = [(g, i + 1) for i, g in enumerate(z.geometry) if g is not None and not g.is_empty]
    if not formes:
        return np.zeros(shape, dtype="int32"), ids
    lab = rasterize(formes, out_shape=shape, transform=tr, fill=0, dtype="int32")
    return lab, ids


@disk_cache("s2")
def _stats_image(image: dict, zones_json: str, emprise_json: str, bbox4326: tuple, bbox_anim: tuple) -> dict:
    """Moyennes des indices par zone pour une image, et NDVI de la fenêtre d'animation. Cache par image et zones."""
    zones = gpd.read_file(io.StringIO(zones_json))
    emprise = gpd.read_file(io.StringIO(emprise_json))
    bounds, shape = _grille(bbox4326, image["crs"])
    scl = _lire(image["hrefs"]["SCL"], bounds, shape)
    lab_e, _ = _rasteriser(emprise.assign(zone="emprise"), image["crs"], bounds, shape)
    in_e = lab_e > 0
    valide = np.isin(scl, SCL_VALIDES)
    part = float(valide[in_e].mean()) if in_e.any() else 0.0
    out = {"date": image["date"], "id": image["id"], "part_valide_emprise": part, "stats": [], "anim": None}
    if part < SEUIL_VALIDE:
        return out
    b = {k: _lire(image["hrefs"][k], bounds, shape).astype("float32") * ECHELLE for k in ASSETS}
    valide &= b["N"] > 0
    idx = calcul_indices(b)
    lab, ids = _rasteriser(zones, image["crs"], bounds, shape)
    n_tot = np.bincount(lab.ravel(), minlength=len(ids) + 1)
    lv = lab[valide]
    n_val = np.bincount(lv, minlength=len(ids) + 1)
    for code, arr in idx.items():
        a = arr[valide]
        ok = np.isfinite(a)
        s = np.bincount(lv[ok], weights=a[ok], minlength=len(ids) + 1)
        c = np.bincount(lv[ok], minlength=len(ids) + 1)
        for i, z in enumerate(ids, start=1):
            if n_tot[i] and c[i] and n_val[i] / n_tot[i] >= 0.5:
                out["stats"].append((z, code, float(s[i] / c[i]), float(n_val[i] / n_tot[i])))
        ae = arr[in_e & valide]
        if ae.size:
            out["stats"].append(("emprise", code, float(np.nanmean(ae)), part))
    # fenêtre d'animation (emprise + marge) : NDVI à 10 m
    ab, ash = _grille(bbox_anim, image["crs"])
    r0, c0 = int((bounds[3] - ab[3]) / RES), int((ab[0] - bounds[0]) / RES)
    nd = np.where(valide, idx["NDVI"], np.nan)[r0:r0 + ash[0], c0:c0 + ash[1]]
    out["anim"] = nd.astype("float16")
    return out


# ---------------------------------------------------------------------------
# Analyse de l'emprise
# ---------------------------------------------------------------------------

def zones_analyse(emprise: gpd.GeoDataFrame, parcelles_site: gpd.GeoDataFrame | None,
                  voisins: gpd.GeoDataFrame | None) -> gpd.GeoDataFrame:
    """Zones : parcelles RPG de l'emprise (« site:… »), partie de l'emprise hors RPG, parcelles voisines (« voisin:… »)."""
    from .territoire import L93

    e = emprise.to_crs(L93)
    zone_e = e.geometry.union_all()
    rows = []
    if parcelles_site is not None and not parcelles_site.empty:
        p = parcelles_site.to_crs(L93)
        for i, r in enumerate(p.itertuples(), start=1):
            rows.append({"zone": f"site:{i}", "type": "site", "culture": getattr(r, "culture", None), "geometry": r.geometry})
        reste = zone_e.difference(p.geometry.union_all())
    else:
        reste = zone_e
    if reste.area > 5000:  # plus de 0,5 ha non déclarés au RPG
        rows.append({"zone": "hors_rpg", "type": "hors RPG", "culture": None, "geometry": reste})
    if voisins is not None and not voisins.empty:
        v = voisins.to_crs(L93)
        v = v[~v.intersects(zone_e)]
        for i, r in enumerate(v.itertuples(), start=1):
            rows.append({"zone": f"voisin:{i}", "type": "voisin", "culture": getattr(r, "culture", None), "geometry": r.geometry})
    return gpd.GeoDataFrame(rows, geometry="geometry", crs=L93).to_crs(4326)


def analyser(emprise: gpd.GeoDataFrame, zones: gpd.GeoDataFrame, debut: str, fin: str, progress=None,
             fils: int = 8) -> dict:
    """Séries temporelles (date, zone, indice, valeur) et NDVI animé de l'emprise."""
    from .territoire import L93

    z = zones.to_crs(4326)
    eb = emprise.to_crs(L93).total_bounds
    m = max(100.0, 0.15 * max(eb[2] - eb[0], eb[3] - eb[1]))
    anim = gpd.GeoSeries.from_xy([eb[0] - m, eb[2] + m], [eb[1] - m, eb[3] + m], crs=L93).to_crs(4326).total_bounds
    bbox_anim = tuple(round(v, 5) for v in anim)
    # zone lue = zones analysées + fenêtre d'animation (sans voisinage, l'animation dépasse les zones)
    zb = z.total_bounds
    bbox = (min(zb[0], bbox_anim[0]), min(zb[1], bbox_anim[1]), max(zb[2], bbox_anim[2]), max(zb[3], bbox_anim[3]))
    bbox = tuple(round(v, 5) for v in bbox)
    images = rechercher(bbox, debut, fin)
    if not images:
        raise DataSourceError("Aucune image Sentinel-2 exploitable sur la période.")
    zj = z.to_json()
    ej = emprise.to_crs(4326)[["geometry"]].to_json()
    res, faits = [], 0

    def _un(img):
        try:
            return _stats_image(img, zj, ej, bbox, bbox_anim)
        except Exception as e:  # une image illisible n'interrompt pas l'analyse
            return {"date": img["date"], "id": img["id"], "erreur": str(e), "stats": [], "anim": None, "part_valide_emprise": 0}

    with ThreadPoolExecutor(max_workers=fils) as ex:
        for r in ex.map(_un, images):
            res.append(r)
            faits += 1
            if progress:
                progress(faits / len(images), f"Images Sentinel-2 : {faits}/{len(images)} ({r['date']})")
    lignes = [(r["date"], z_, ind, v, pv) for r in res for z_, ind, v, pv in r["stats"]]
    series = pd.DataFrame(lignes, columns=["date", "zone", "indice", "valeur", "part_valide"])
    series["date"] = pd.to_datetime(series["date"])
    # animation : images de la projection UTM la plus fréquente (une zone à cheval sur deux fuseaux en a deux)
    crs_img = {i["id"]: i["crs"] for i in images}
    avec = [r for r in res if r.get("anim") is not None]
    crs_anim = pd.Series([crs_img[r["id"]] for r in avec]).mode().iat[0] if avec else None
    anim_frames = [(r["date"], r["anim"]) for r in avec if crs_img[r["id"]] == crs_anim]
    return {"series": series, "images": len(images), "dates_valides": series["date"].nunique() if not series.empty else 0,
            "erreurs": sum(1 for r in res if r.get("erreur")), "anim": anim_frames, "bbox_anim": bbox_anim,
            "anim_crs": crs_anim, "anim_bornes": _grille(bbox_anim, crs_anim)[0] if crs_anim else None}


# ---------------------------------------------------------------------------
# Lecture des séries : bilan annuel par zone (règles indicatives, affichées)
# ---------------------------------------------------------------------------

REGLES = {
    "lissage": "NDVI lissé par médiane glissante sur 3 dates avant le calcul des cycles et de la saison (une valeur isolée, souvent un nuage non détecté, est écartée)",
    "saison": "début et fin de saison : passage à 50 % de l'amplitude du NDVI de l'année civile (méthode du seuil d'amplitude, TIMESAT) ; pour une culture d'hiver, le début correspond à la reprise de végétation de fin d'hiver",
    "hiver": "couverture hivernale : part des dates de novembre à février avec un NDVI ≥ 0,3",
    "sol_nu": "sol nu probable : NDVI < 0,25 et BSI > 0",
    "cycle": "cycle de végétation : un pic de NDVI ≥ 0,5, séparé du pic suivant par un passage sous 0,3",
    "eau": "eau libre probable : MNDWI > 0",
}


def cycles(ndvi: pd.Series, haut: float = 0.5, bas: float = 0.3) -> int:
    """Nombre de cycles de végétation dans une série datée (hystérésis : monter au-dessus de `haut`, redescendre sous `bas`)."""
    n, en_haut = 0, False
    s = ndvi.dropna()
    for v in s.rolling(3, center=True, min_periods=1).median():
        if not en_haut and v >= haut:
            n, en_haut = n + 1, True
        elif en_haut and v < bas:
            en_haut = False
    return n


# Repères généraux de lecture du NDVI : USGS, « NDVI, the Foundation for Remote Sensing Phenology »
# (https://www.usgs.gov/special-topics/remote-sensing-phenology/science/ndvi-foundation-remote-sensing-phenology)
REPERES_NDVI = [(-0.2, 0.1, "roche, sable, neige, sol nu", "rgba(138,122,92,.10)"),
                (0.2, 0.5, "végétation clairsemée, prairie, culture en fin de cycle", "rgba(220,229,188,.35)"),
                (0.6, 0.9, "végétation dense, culture à son pic", "rgba(86,101,62,.14)")]
SEUIL_PHENO = 0.5  # fraction de l'amplitude saisonnière (méthode du seuil d'amplitude, Jönsson et Eklundh 2004, TIMESAT)


def _franchissement(d0, v0, d1, v1, seuil):
    """Date d'interpolation linéaire où la courbe franchit `seuil` entre deux observations."""
    if v1 == v0:
        return d1
    k = (seuil - v0) / (v1 - v0)
    return d0 + (d1 - d0) * float(min(max(k, 0.0), 1.0))


def phenologie(ndvi: pd.Series) -> dict:
    """Début, pic et fin de la saison principale (seuil à 50 % de l'amplitude). ndvi : série indexée par date."""
    s = ndvi.dropna().sort_index()
    if len(s) < 5:
        return {}
    lisse = s.rolling(3, center=True, min_periods=1).median()
    ipic = lisse.idxmax()
    vmin, vmax = float(lisse.min()), float(lisse.max())
    amp = vmax - vmin
    if amp < 0.2:  # pas de saison marquée (prairie stable, sol nu permanent, couvert permanent)
        return {"pic": ipic, "ndvi_pic": vmax, "amplitude": amp}
    seuil = vmin + SEUIL_PHENO * amp
    avant, apres = lisse[:ipic], lisse[ipic:]
    sos = eos = None
    for (d0, v0), (d1, v1) in zip(list(avant.items())[::-1][1:], list(avant.items())[::-1][:-1]):
        if v0 < seuil <= v1:
            sos = _franchissement(d0, v0, d1, v1, seuil)
            break
    for (d0, v0), (d1, v1) in zip(list(apres.items())[:-1], list(apres.items())[1:]):
        if v0 >= seuil > v1:
            eos = _franchissement(d0, v0, d1, v1, seuil)
            break
    out = {"pic": ipic, "ndvi_pic": vmax, "amplitude": amp, "debut": sos, "fin": eos}
    if sos is not None and eos is not None:
        out["duree_j"] = int((eos - sos).days)
    return out


def fourchette(series: pd.DataFrame, zones: gpd.GeoDataFrame, culture: str, indice: str = "NDVI", n_min: int = 8,
               annee: int | None = None) -> pd.DataFrame:
    """Par date : 25e centile, médiane et 75e centile des parcelles voisines de la culture donnée (≥ n_min parcelles).

    `annee` : limiter aux dates de l'année du RPG dont viennent les cultures (elles changent d'une année à l'autre).
    """
    vz = zones[(zones["type"] == "voisin") & (zones["culture"] == culture)]["zone"]
    s = series[series["zone"].isin(vz) & (series["indice"] == indice)]
    if annee is not None:
        s = s[s["date"].dt.year == annee]
    if s.empty:
        return pd.DataFrame(columns=["date", "p25", "p50", "p75", "n"])
    g = s.groupby("date")["valeur"]
    f = pd.DataFrame({"p25": g.quantile(0.25), "p50": g.median(), "p75": g.quantile(0.75), "n": g.count()}).reset_index()
    return f[f["n"] >= n_min].sort_values("date").reset_index(drop=True)


def mois_txt(dates) -> str:
    """« juin et juillet 2025 » à partir d'une liste de dates."""
    ms = sorted({(pd.Timestamp(d).year, pd.Timestamp(d).month) for d in dates})
    if not ms:
        return ""
    noms = [f"{MOIS_LONG[m - 1]} {a}" for a, m in ms]
    return noms[0] if len(noms) == 1 else ", ".join(noms[:-1]) + " et " + noms[-1]


MOIS_LONG = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]


def position_fourchette(serie: pd.DataFrame, f: pd.DataFrame, fenetre=None) -> dict:
    """Part des dates d'une parcelle dans la fourchette des voisines (dans la saison si `fenetre`), et périodes sous / au-dessus."""
    m = serie.merge(f, on="date")
    if fenetre is not None:
        m = m[(m["date"] >= fenetre[0]) & (m["date"] <= fenetre[1])]
    if m.empty:
        return {}
    dedans = (m["valeur"] >= m["p25"]) & (m["valeur"] <= m["p75"])
    sous = m.loc[m["valeur"] < m["p25"], "date"]
    dessus = m.loc[m["valeur"] > m["p75"], "date"]
    return {"n": len(m), "dedans_pct": round(100 * float(dedans.mean())), "sous": list(sous), "dessus": list(dessus)}


MOIS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]


def bilan(series: pd.DataFrame, zones: gpd.GeoDataFrame) -> pd.DataFrame:
    """Une ligne par zone du site (parcelles, hors RPG, emprise) et par année."""
    if series.empty:
        return pd.DataFrame()
    w = series.pivot_table(index=["zone", "date"], columns="indice", values="valeur").reset_index()
    w["annee"] = w["date"].dt.year
    info = zones.set_index("zone")[["type", "culture"]].to_dict("index")
    rows = []
    for (zone, an), g in w[~w["zone"].str.startswith("voisin:")].groupby(["zone", "annee"]):
        g = g.sort_values("date")
        nu = (g["NDVI"] < 0.25) & (g["BSI"] > 0)
        ete = g[g["date"].dt.month.isin([6, 7, 8])]
        imax = g["NDVI"].idxmax()
        z = info.get(zone, {"type": "emprise", "culture": None})
        ph = phenologie(g.set_index("date")["NDVI"])
        hiver = g[g["date"].dt.month.isin([11, 12, 1, 2])]
        rows.append({
            "Zone": zone, "Type": z["type"] if zone != "emprise" else "emprise entière",
            "Culture RPG": z["culture"] if isinstance(z["culture"], str) else "",
            "Année": int(an), "Dates sans nuage": int(len(g)),
            "NDVI maximal": round(float(g["NDVI"].max()), 2), "Date du maximum": g.loc[imax, "date"].date().isoformat(),
            "Cycles de végétation": cycles(g["NDVI"]),
            "Sol nu probable (% des dates)": round(100 * float(nu.mean()), 0),
            "Mois de sol nu": ", ".join(MOIS[m - 1] for m in sorted(g.loc[nu, "date"].dt.month.unique())),
            "NDMI moyen juin-août": round(float(ete["NDMI"].mean()), 2) if not ete.empty else None,
            "Dates avec eau libre": int((g["MNDWI"] > 0).sum()),
            "Début de saison": ph["debut"].date().isoformat() if ph.get("debut") is not None else "",
            "Fin de saison": ph["fin"].date().isoformat() if ph.get("fin") is not None else "",
            "Durée de saison (j)": ph.get("duree_j"),
            "Couverture hivernale (% des dates)": round(100 * float((hiver["NDVI"] >= 0.3).mean())) if not hiver.empty else None,
        })
    return pd.DataFrame(rows)


def fenetre_saison(mediane: pd.Series, marge_j: int = 30):
    """Saison de la culture d'après la courbe médiane des voisines : (début − marge, fin + marge), ou None."""
    ph = phenologie(mediane)
    if ph.get("debut") is None or ph.get("fin") is None:
        return None
    return ph["debut"] - pd.Timedelta(days=marge_j), ph["fin"] + pd.Timedelta(days=marge_j)


def voisinage(series: pd.DataFrame, zones: gpd.GeoDataFrame, annee: int, n_min: int = 8) -> pd.DataFrame:
    """Rang du NDVI maximal de chaque parcelle du site parmi les parcelles voisines de même culture (même année RPG).

    Le maximum et le pic sont pris dans la saison de la culture (début et fin de saison médians des voisines, ± 30 jours),
    pour qu'un couvert d'interculture ou une repousse ne fausse pas la comparaison.
    """
    s = series[(series["indice"] == "NDVI") & (series["date"].dt.year == annee)]
    if s.empty:
        return pd.DataFrame()
    nd = s.pivot_table(index="date", columns="zone", values="valeur")
    z = zones.set_index("zone")
    rows = []
    for zone in [i for i in z.index if i.startswith("site:")]:
        cult = z.loc[zone, "culture"]
        if zone not in nd or not isinstance(cult, str) or not cult:
            continue
        vois = [v for v in z.index[(z["type"] == "voisin") & (z["culture"] == cult)] if v in nd]
        if len(vois) < n_min:
            rows.append({"Parcelle": zone, "Culture": cult, "Parcelles voisines comparées": len(vois),
                         "NDVI maximal": round(float(nd[zone].max()), 2), "Rang (percentile)": None,
                         "Lecture": f"moins de {n_min} parcelles voisines de même culture : comparaison non significative"})
            continue
        med = nd[vois].median(axis=1).dropna()
        fen = fenetre_saison(med)
        w = nd.loc[fen[0]:fen[1]] if fen else nd
        mx = w.max()
        mv = mx[vois].dropna()  # voisines sans image exploitable dans la saison : écartées
        if pd.isna(mx[zone]) or len(mv) < n_min:
            rows.append({"Parcelle": zone, "Culture": cult, "Parcelles voisines comparées": len(mv),
                         "NDVI maximal": round(float(mx[zone]), 2) if pd.notna(mx[zone]) else None, "Rang (percentile)": None,
                         "Lecture": "pas d'image exploitable sur la parcelle pendant la saison" if pd.isna(mx[zone]) else
                         f"moins de {n_min} parcelles voisines de même culture observées : comparaison non significative"})
            continue
        vois = list(mv.index)
        pct = 100 * float((mv < mx[zone]).mean())
        # décalage du pic : seulement pour une culture à saison marquée (prairie, luzerne : plusieurs pics équivalents)
        decal = int((w[zone].idxmax() - w[vois].median(axis=1).idxmax()).days) if fen else None
        lect = ("au-dessus de toutes les parcelles voisines de même culture" if pct >= 100 else
                "en dessous de toutes les parcelles voisines de même culture" if pct <= 0 else
                f"au-dessus de {round(pct)} % des parcelles voisines de même culture")
        rows.append({"Parcelle": zone, "Culture": cult, "Parcelles voisines comparées": len(vois),
                     "Saison comparée": f"{fen[0].strftime('%d/%m')} – {fen[1].strftime('%d/%m/%Y')}" if fen else f"année {annee}",
                     "NDVI maximal": round(float(mx[zone]), 2), "Médiane des voisines": round(float(mv.median()), 2),
                     "Rang (percentile)": round(pct), "Décalage du pic (jours)": decal, "Lecture": lect})
    return pd.DataFrame(rows)


def phrases(b: pd.DataFrame, v: pd.DataFrame, noms: dict[str, str], annee_rpg: int | None = None) -> list[str]:
    """Phrases factuelles par gabarit (aucune interprétation agronomique). `annee_rpg` : millésime des cultures citées."""
    out = []
    if b.empty:
        return out
    last = b["Année"].max()
    for _, r in b[b["Année"] == last].iterrows():
        nom = noms.get(r["Zone"], r["Zone"])
        c = r.get("Culture RPG", r.get("Culture RPG (dernière)"))  # ancien nom dans les projets enregistrés
        rpg = f"RPG {annee_rpg}" if annee_rpg else "RPG"
        cult = ("" if not (isinstance(c, str) and c) else
                f" (culture déclarée au {rpg})" if str(c).lower() in nom.lower() else  # culture déjà dans le nom
                f" ({str(c).lower()}, culture déclarée au {rpg})")
        txt = (f"{nom}{cult} : en {last}, le NDVI atteint {str(r['NDVI maximal']).replace('.', ',')} le "
               f"{pd.Timestamp(r['Date du maximum']).strftime('%d/%m/%Y')}, avec {r['Cycles de végétation']} cycle(s) de végétation "
               f"sur {r['Dates sans nuage']} dates sans nuage")
        if r["Sol nu probable (% des dates)"]:
            txt += f" ; sol nu probable sur {int(r['Sol nu probable (% des dates)'])} % des dates ({r['Mois de sol nu']})"
        out.append(txt + ".")
    if not v.empty:
        for _, r in v.dropna(subset=["Rang (percentile)"]).iterrows():
            dec = r.get("Décalage du pic (jours)")
            dtxt = (f" ; pic {abs(int(dec))} jours {'plus tard' if dec > 0 else 'plus tôt'} que la médiane des voisines"
                    if dec is not None and pd.notna(dec) and abs(dec) >= 7 else "")
            out.append(f"{noms.get(r['Parcelle'], r['Parcelle'])} : NDVI maximal {str(r['NDVI maximal']).replace('.', ',')}, "
                       f"{r['Lecture']} ({int(r['Parcelles voisines comparées'])} parcelles){dtxt}.")
    return out


def json_zones(z: gpd.GeoDataFrame) -> str:
    return json.dumps(json.loads(z.to_json()), sort_keys=True)
