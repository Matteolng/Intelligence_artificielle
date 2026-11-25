"""Barème indicatif de la valeur vénale moyenne des terres agricoles (décision annuelle publiée au Journal officiel).

- Petites régions agricoles (PRA) du territoire : référentiel du ministère de l'Agriculture (2017), diffusé par l'OFB
  (service WFS « ref_met_petite_region_agricole_masa_pol_3857 »).
- Barème : Légifrance n'autorise pas l'accès automatisé ; l'utilisateur dépose la décision (page enregistrée en HTML,
  ou texte copié) et l'outil en lit les tableaux. Dernière décision connue : décision du 10 août 2026 portant fixation
  du barème indicatif de la valeur vénale moyenne des terres agricoles en 2025 (JORFTEXT000054708553).
La correspondance PRA → ligne du barème se fait par le nom ; elle est présentée comme une proposition à vérifier.
"""
from __future__ import annotations

import io
import re
import unicodedata

import geopandas as gpd
import pandas as pd

from .http import DataSourceError, disk_cache, get_json

OFB_WFS = "https://wxs.ofb.fr/geoserver/referentiel/ows"
PRA_LAYER = "referentiel:ref_met_petite_region_agricole_masa_pol_3857"
DECISION_2025 = "https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000054708553"


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().upper()
    return re.sub(r"[^A-Z0-9]+", " ", s).strip()


@disk_cache("geo")
def _pra_bbox(bbox3857: tuple[float, float, float, float]) -> dict:
    return get_json(OFB_WFS, params={"service": "WFS", "version": "2.0.0", "request": "GetFeature", "typename": PRA_LAYER,
                                     "outputFormat": "application/json", "srsName": "EPSG:3857",
                                     "bbox": ",".join(f"{v:.0f}" for v in bbox3857) + ",EPSG:3857"})


def pra_du_territoire(communes: gpd.GeoDataFrame) -> pd.DataFrame:
    """PRA intersectant le territoire, avec la part de la surface du territoire dans chacune."""
    c = communes.to_crs(3857)
    fc = _pra_bbox(tuple(round(v) for v in c.total_bounds))
    if not fc.get("features"):
        return pd.DataFrame(columns=["code_pra", "nom", "departement", "part_pct"])
    p = gpd.GeoDataFrame.from_features(fc["features"], crs=3857)
    zone = c.geometry.union_all()
    p["surf"] = p.geometry.intersection(zone).area
    p = p[p["surf"] > 0].copy()
    tot = p["surf"].sum()
    p["departement"] = p["code_pra"].astype(str).str[:-3]
    p["nom"] = p["libelle_pr"].astype(str).str.replace(r"\s*-\s*\w+$", "", regex=True)
    p["part_pct"] = 100 * p["surf"] / tot if tot else 0
    return p[["code_pra", "nom", "departement", "part_pct"]].sort_values("part_pct", ascending=False).reset_index(drop=True)


_NUM = re.compile(r"^\s*(ND|\d[\d\s  ]*)\s*$")


def _val(s: str):
    s = str(s).strip()
    if s.upper() == "ND" or not s:
        return None
    return float(re.sub(r"[\s  ]", "", s))


def lire_bareme(contenu: bytes | str) -> pd.DataFrame:
    """Lit les tableaux de la décision (HTML enregistré depuis Légifrance, ou texte en tableaux « | … | »).

    Renvoie : tableau (titre du tableau), departement (code), region_agricole, dominante, minimum, maximum (€/ha).
    """
    txt = contenu.decode("utf-8", errors="ignore") if isinstance(contenu, bytes) else contenu
    lignes: list[list[str]] = []
    if "<table" in txt.lower():
        for tb in pd.read_html(io.StringIO(txt), flavor="lxml"):
            lignes.append(["__TABLE__"])
            for row in tb.astype(str).values.tolist():
                lignes.append([x for x in row if x and x != "nan"])
    else:
        for l in txt.splitlines():
            if l.strip().startswith("|"):
                lignes.append([c.strip() for c in l.strip().strip("|").split("|") if c.strip()])
    titre, dep, out = "", None, []
    for cells in lignes:
        if not cells:
            continue
        if cells == ["__TABLE__"]:
            dep = None
            continue
        head = " ".join(cells).upper()
        if "TERRES" in head or "VIGNES" in head or "PRAIRIES" in head:
            if len(cells) == 1 or not any(_NUM.match(c) for c in cells[1:]):
                titre = " ".join(cells)
                continue
        m = re.match(r"^(\d{2,3}|2A|2B)\s*-\s*(.+)$", cells[0])
        nums = [c for c in cells[1:] if _NUM.match(c)]
        if m and len(nums) < 3:
            dep = m.group(1)
            continue
        if m and len(nums) >= 3:  # département sans détail par région agricole
            out.append({"tableau": titre, "departement": m.group(1), "region_agricole": m.group(2).strip(),
                        "dominante": _val(nums[0]), "minimum": _val(nums[1]), "maximum": _val(nums[2])})
            continue
        if dep and len(cells) >= 4 and all(_NUM.match(c) for c in cells[-3:]):
            out.append({"tableau": titre, "departement": dep, "region_agricole": cells[-4],
                        "dominante": _val(cells[-3]), "minimum": _val(cells[-2]), "maximum": _val(cells[-1])})
    if not out:
        raise DataSourceError("Aucun tableau de barème reconnu dans ce fichier.")
    return pd.DataFrame(out)


_VIDES = {"DE", "DES", "DU", "LA", "LE", "LES", "ET", "D", "L", "EN", "SUR"}


def _mots(s: str) -> set[str]:
    return set(_norm(s).split()) - _VIDES


def correspondances(pra: pd.DataFrame, bareme: pd.DataFrame) -> pd.DataFrame:
    """Lignes du barème dont le libellé contient le nom de la PRA (même département). Proposition à vérifier."""
    rows = []
    for _, p in pra.iterrows():
        n = _mots(p["nom"])
        b = bareme[bareme["departement"].astype(str) == str(p["departement"])]
        hit = b[[bool(n) and n <= _mots(x) for x in b["region_agricole"]]]
        if hit.empty and len(b["region_agricole"].unique()) == 1:
            hit = b  # département sans découpage par région agricole
        for _, h in hit.iterrows():
            rows.append({"PRA": p["nom"], "Part du territoire (%)": round(p["part_pct"], 1), "Tableau": h["tableau"],
                         "Ligne du barème": h["region_agricole"], "Dominante (€/ha)": h["dominante"],
                         "Minimum (€/ha)": h["minimum"], "Maximum (€/ha)": h["maximum"]})
    return pd.DataFrame(rows)
