"""Registre parcellaire graphique (RPG) – Géoplateforme IGN (WFS).

Le RPG recense les parcelles déclarées à la PAC. Il ne couvre donc pas les
surfaces agricoles non déclarées : il sous-estime la SAU réelle, en particulier
pour le maraîchage, la viticulture hors aides et les petites exploitations.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Callable

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import MultiPolygon, shape

from .config import DATA_DIR, GPF_WFS, RPG_FAMILLES, RPG_GROUPES, RPG_PAGE_SIZE
from .http import DataSourceError, disk_cache, get_json, memo
from .territoire import L93, WGS84

_FAMILLE_DE_GROUPE = {g: fam for fam, groupes in RPG_FAMILLES.items() for g in groupes}
FAMILLE_PAR_LIBELLE = {RPG_GROUPES[g]: fam for g, fam in _FAMILLE_DE_GROUPE.items() if g in RPG_GROUPES}


@disk_cache("catalogue")
def _codes_cultures_wfs(couche: str) -> pd.DataFrame:
    d = get_json(GPF_WFS, params={"SERVICE": "WFS", "VERSION": "2.0.0", "REQUEST": "GetFeature", "TYPENAMES": couche,
                                  "COUNT": 2000, "OUTPUTFORMAT": "application/json"}, timeout=120)
    return pd.DataFrame([f["properties"] for f in d.get("features", [])]).astype(str)


@memo(3600)
def codes_cultures() -> pd.DataFrame:
    """Nomenclature des cultures du RPG : table « codes_cultures » du dernier millésime publié (Géoplateforme),
    complétée par la copie locale (2025) pour les codes absents ou si le service ne répond pas."""
    local = pd.read_csv(DATA_DIR / "rpg_codes_cultures_2025.csv", dtype=str)
    try:
        from .catalogue import couche_codes_cultures

        web = _codes_cultures_wfs(couche_codes_cultures())
        if {"code_culture", "libelle_culture"} <= set(web.columns):
            return pd.concat([web[["code_culture", "libelle_culture"]], local[["code_culture", "libelle_culture"]]]).drop_duplicates("code_culture")
    except Exception:  # nomenclature locale en secours
        pass
    return local


def _wfs_params(layer: str, bbox: tuple[float, float, float, float], start: int, count: int) -> dict:
    minx, miny, maxx, maxy = bbox
    return {
        "SERVICE": "WFS",
        "VERSION": "2.0.0",
        "REQUEST": "GetFeature",
        "TYPENAMES": layer,
        "OUTPUTFORMAT": "application/json",
        "SRSNAME": "EPSG:4326",
        "BBOX": f"{minx},{miny},{maxx},{maxy},EPSG:4326",
        "COUNT": count,
        "STARTINDEX": start,
    }


def _features_to_rows(features: list[dict]) -> list[dict]:
    rows = []
    for f in features:
        p = dict(f.get("properties") or {})
        p["fid"] = f.get("id")
        geom = f.get("geometry")
        p["geometry"] = shape(geom) if geom else None
        rows.append(p)
    return rows


def fetch_rpg_bbox(layer: str, bbox: tuple[float, float, float, float]) -> gpd.GeoDataFrame:
    """Télécharge toutes les parcelles RPG d'une emprise (pagination WFS).

    Le cache est indexé par l'année réelle de la couche : quand « RPG.LATEST » passe à un nouveau millésime,
    les anciennes données ne sont plus resservies.
    """
    from .catalogue import annee_de_couche

    return _fetch_rpg_bbox(layer, bbox, annee_de_couche(layer))


@disk_cache("rpg")
def _fetch_rpg_bbox(layer: str, bbox: tuple[float, float, float, float], millesime: str) -> gpd.GeoDataFrame:
    first = get_json(GPF_WFS, params=_wfs_params(layer, bbox, 0, RPG_PAGE_SIZE), timeout=180)
    total = int(first.get("numberMatched") or first.get("totalFeatures") or 0)
    rows = _features_to_rows(first.get("features", []))
    starts = list(range(RPG_PAGE_SIZE, total, RPG_PAGE_SIZE))

    def _page(start: int) -> list[dict]:
        d = get_json(GPF_WFS, params=_wfs_params(layer, bbox, start, RPG_PAGE_SIZE), timeout=180)
        return _features_to_rows(d.get("features", []))

    if starts:
        with ThreadPoolExecutor(max_workers=3) as ex:
            for part in ex.map(_page, starts):
                rows.extend(part)
    if not rows:
        return gpd.GeoDataFrame(geometry=[], crs=WGS84)
    gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs=WGS84)
    gdf = gdf.drop_duplicates(subset="fid")
    return gdf


def _split_bbox(bounds, n: int):
    minx, miny, maxx, maxy = bounds
    xs = np.linspace(minx, maxx, n + 1)
    ys = np.linspace(miny, maxy, n + 1)
    for i in range(n):
        for j in range(n):
            yield (round(xs[i], 6), round(ys[j], 6), round(xs[i + 1], 6), round(ys[j + 1], 6))


def normalise(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Harmonise les attributs (les noms varient légèrement selon les millésimes)."""
    if gdf.empty:
        return gdf
    g = gdf.copy()
    rename = {}
    for col in g.columns:
        low = col.lower()
        if low in ("code_cultu", "code_cultur"):
            rename[col] = "code_cultu"
        elif low in ("code_group", "code_groupe"):
            rename[col] = "code_group"
    g = g.rename(columns=rename)
    if "code_group" in g:
        g["code_group"] = pd.to_numeric(g["code_group"], errors="coerce").astype("Int64")
    else:
        g["code_group"] = pd.NA
    g["groupe"] = g["code_group"].map(lambda c: RPG_GROUPES.get(int(c), f"Groupe {c}") if pd.notna(c) else "Non renseigné")
    g["famille"] = g["code_group"].map(lambda c: _FAMILLE_DE_GROUPE.get(int(c), "Gel et divers") if pd.notna(c) else "Gel et divers")
    cc = codes_cultures().set_index("code_culture")["libelle_culture"].to_dict()
    if "code_cultu" in g:
        g["culture"] = g["code_cultu"].map(cc).fillna(g["code_cultu"])
    else:
        g["culture"] = "Non renseigné"
    for flag in ("bio", "pp", "gcp", "iae"):
        if flag in g:
            g[flag] = g[flag].fillna(False).astype(bool)
    g["surface_ha"] = g.to_crs(L93).area / 1e4
    return g


def rpg_territoire(layer: str, communes: gpd.GeoDataFrame, progress: Callable[[float, str], None] | None = None) -> gpd.GeoDataFrame:
    """Parcelles RPG du territoire, rattachées à leur commune (point intérieur)."""
    bounds = communes.total_bounds
    width_km = (bounds[2] - bounds[0]) * 80
    height_km = (bounds[3] - bounds[1]) * 111
    # découpage en tuiles pour limiter la taille des réponses et profiter du cache par tuile
    n = int(min(6, max(1, np.ceil(max(width_km, height_km) / 25))))
    tiles = list(_split_bbox(bounds, n))
    parts = []
    for i, bb in enumerate(tiles, start=1):
        if progress:
            progress((i - 1) / len(tiles), f"Téléchargement RPG – tuile {i}/{len(tiles)}")
        part = fetch_rpg_bbox(layer, bb)
        if not part.empty:
            parts.append(part)
    if progress:
        progress(1.0, "Rattachement des parcelles aux communes")
    if not parts:
        return gpd.GeoDataFrame(geometry=[], crs=WGS84)
    gdf = gpd.GeoDataFrame(pd.concat(parts, ignore_index=True), geometry="geometry", crs=WGS84)
    gdf = gdf.drop_duplicates(subset="fid")
    pts = gdf.copy()
    pts["geometry"] = gdf.geometry.representative_point()
    joined = gpd.sjoin(pts, communes[["code", "nom", "geometry"]], how="inner", predicate="within")
    gdf = gdf.loc[joined.index].copy()
    gdf["code_commune"] = joined["code"].values
    gdf["nom_commune"] = joined["nom"].values
    return normalise(gdf)


def _polygonal(geom):
    """Ne garde que la partie surfacique d'une géométrie (les intersections produisent parfois des GeometryCollection)."""
    if geom is None or geom.is_empty:
        return None
    if geom.geom_type in ("Polygon", "MultiPolygon"):
        return geom
    parts = [g for g in getattr(geom, "geoms", []) if g.geom_type in ("Polygon", "MultiPolygon")]
    if not parts:
        return None
    polys = []
    for p in parts:
        polys.extend(p.geoms if p.geom_type == "MultiPolygon" else [p])
    return MultiPolygon(polys)


def rpg_emprise(layer: str, emprise: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Parcelles RPG intersectant l'emprise du projet, découpées à l'emprise."""
    e = emprise.to_crs(WGS84)
    minx, miny, maxx, maxy = e.total_bounds
    pad = 0.002
    gdf = fetch_rpg_bbox(layer, (round(minx - pad, 6), round(miny - pad, 6), round(maxx + pad, 6), round(maxy + pad, 6)))
    if gdf.empty:
        return gdf
    g = normalise(gdf).to_crs(L93)
    zone = e.to_crs(L93).geometry.union_all()
    g = g[g.intersects(zone)].copy()
    g["surface_parcelle_ha"] = g.area / 1e4
    g["geometry"] = g.geometry.intersection(zone).map(_polygonal)
    g = g[g.geometry.notna()]
    g["surface_ha"] = g.area / 1e4
    g = g[g["surface_ha"] > 0.0001]
    return g.to_crs(WGS84)


# ---------------------------------------------------------------------------
# Statistiques
# ---------------------------------------------------------------------------

def indicateurs(g: gpd.GeoDataFrame) -> dict:
    if g.empty:
        return {}
    s = float(g["surface_ha"].sum())
    out = {
        "Surface déclarée (ha)": s,
        "Nombre de parcelles": int(len(g)),
        "Nombre d'îlots": int(g["num_ilot"].nunique()) if "num_ilot" in g else None,
        "Surface moyenne d'une parcelle (ha)": s / len(g) if len(g) else None,
    }
    if "bio" in g:
        out["Part de la surface déclarée en bio (%)"] = 100 * g.loc[g["bio"], "surface_ha"].sum() / s if s else None
    pp = g["code_group"].isin([17, 18])
    out["Part prairies permanentes, estives et landes (%)"] = 100 * g.loc[pp, "surface_ha"].sum() / s if s else None
    return out


def assolement(g: gpd.GeoDataFrame, by: str = "groupe") -> pd.DataFrame:
    if g.empty:
        return pd.DataFrame(columns=[by, "surface_ha", "part_pct", "nb_parcelles"])
    t = g.groupby(by, as_index=False).agg(surface_ha=("surface_ha", "sum"), nb_parcelles=("surface_ha", "size"))
    t["part_pct"] = 100 * t["surface_ha"] / t["surface_ha"].sum()
    return t.sort_values("surface_ha", ascending=False).reset_index(drop=True)


def cultures_detail(g: gpd.GeoDataFrame, top: int | None = None) -> pd.DataFrame:
    t = assolement(g, by="culture")
    if top:
        t = t.head(top)
    return t


def par_commune(g: gpd.GeoDataFrame) -> pd.DataFrame:
    """Surface par commune et par famille, famille dominante."""
    if g.empty:
        return pd.DataFrame()
    pv = g.pivot_table(index=["code_commune", "nom_commune"], columns="famille", values="surface_ha", aggfunc="sum", fill_value=0)
    pv["Total RPG (ha)"] = pv.sum(axis=1)
    fam_cols = [c for c in pv.columns if c != "Total RPG (ha)"]
    pv["Famille dominante"] = pv[fam_cols].idxmax(axis=1)
    pv["Part famille dominante (%)"] = 100 * pv[fam_cols].max(axis=1) / pv["Total RPG (ha)"].replace(0, np.nan)
    return pv.reset_index()


def comparaison_emprise(emprise_rpg: gpd.GeoDataFrame, territoire_rpg: gpd.GeoDataFrame) -> pd.DataFrame:
    """Part de chaque groupe de culture de l'emprise dans le total du territoire."""
    if emprise_rpg.empty:
        return pd.DataFrame()
    a = emprise_rpg.groupby("groupe", as_index=False)["surface_ha"].sum().rename(columns={"surface_ha": "emprise_ha"})
    b = territoire_rpg.groupby("groupe", as_index=False)["surface_ha"].sum().rename(columns={"surface_ha": "territoire_ha"})
    m = a.merge(b, on="groupe", how="left")
    m["part_du_territoire_pct"] = 100 * m["emprise_ha"] / m["territoire_ha"]
    return m.sort_values("emprise_ha", ascending=False).reset_index(drop=True)


def check_layer_available(layer: str) -> bool:
    try:
        d = get_json(GPF_WFS, params=_wfs_params(layer, (2.0, 45.0, 2.01, 45.01), 0, 1), timeout=60)
        return "features" in d
    except DataSourceError:
        return False
