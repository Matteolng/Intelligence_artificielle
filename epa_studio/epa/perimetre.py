"""Périmètre d'étude proposé à partir de l'emprise du projet, et paragraphe de justification généré par gabarit.

Proposition : communes intersectant l'emprise et leurs intercommunalités (API Découpage administratif).
Les communes des sièges des exploitations concernées ne sont pas publiques : le chargé d'études les ajoute.
"""
from __future__ import annotations

import geopandas as gpd
import pandas as pd

from . import territoire as T
from .analyse import fnum
from .demo import commune_au_point
from .http import DataSourceError


def _points_echantillon(emprise: gpd.GeoDataFrame, n_max: int = 40) -> list[tuple[float, float]]:
    """Points représentatifs (intérieur de chaque polygone + sommets) en WGS84, pour interroger l'API par coordonnées."""
    e = emprise.to_crs(T.WGS84)
    pts = [g.representative_point() for g in e.geometry]
    for g in e.geometry:
        for poly in getattr(g, "geoms", [g]):
            coords = list(poly.exterior.coords)
            pas = max(1, len(coords) // 8)
            pts.extend(gpd.points_from_xy([c[0] for c in coords[::pas]], [c[1] for c in coords[::pas]]))
    return [(p.y, p.x) for p in pts[:n_max]]


def proposer(emprise: gpd.GeoDataFrame) -> dict:
    """{'epcis': [{code, nom}], 'communes_hors_epci': [code], 'communes_emprise': [code]} pour l'emprise donnée."""
    if emprise is None or emprise.empty:
        raise DataSourceError("Aucune emprise : importez ou dessinez l'emprise du projet.")
    communes: dict[str, dict] = {}
    for lat, lon in _points_echantillon(emprise):
        c = commune_au_point(lat, lon)
        if c:
            communes[c["code"]] = c
    if not communes:
        raise DataSourceError("L'emprise n'est située dans aucune commune française.")
    epcis = {}
    for c in communes.values():
        if c.get("codeEpci") and c["codeEpci"] not in epcis:
            epcis[c["codeEpci"]] = {"code": c["codeEpci"], "nom": T.epci_info(c["codeEpci"]).get("nom", c["codeEpci"])}
    hors = [k for k, c in communes.items() if not c.get("codeEpci")]
    t = T.build_territoire(list(epcis.values()), hors)
    zone = emprise.to_crs(T.L93).geometry.union_all()
    touchees = t.communes.to_crs(T.L93)
    touchees = touchees.loc[touchees.intersects(zone), "code"].astype(str).tolist()
    return {"epcis": list(epcis.values()), "communes_hors_epci": hors, "communes_emprise": sorted(set(touchees) | set(communes))}


def texte_justification(communes: gpd.GeoDataFrame, epcis: list[dict], codes_emprise: list[str],
                        ajoutees: list[str] | None = None, retirees: list[str] | None = None,
                        otex: pd.DataFrame | None = None) -> str:
    """Paragraphe factuel (aucune interprétation) ; les éléments à apporter par le chargé d'études sont signalés."""
    noms = dict(zip(communes["code"].astype(str), communes["nom"]))
    n = len(communes)
    surf = float(communes["surface_ha"].sum()) if "surface_ha" in communes else None
    emp = [noms.get(c, c) for c in codes_emprise]
    phr = [f"Le périmètre d'étude élargi regroupe {n} commune{'s' if n > 1 else ''}"
           + (f" pour {fnum(surf / 100)} km²" if surf else "") + "."]
    if emp:
        phr.append(f"Il est construit à partir de la ou des communes concernées par l'emprise du projet ({', '.join(emp)})"
                   + (f" et de leur intercommunalité ({', '.join(e['nom'] for e in epcis)})." if epcis else "."))
    if ajoutees:
        phr.append(f"{len(ajoutees)} commune{'s' if len(ajoutees) > 1 else ''} y {'ont' if len(ajoutees) > 1 else 'a'} été "
                   f"ajoutée{'s' if len(ajoutees) > 1 else ''} : {', '.join(noms.get(c, c) for c in ajoutees)}.")
    if retirees:
        phr.append(f"{len(retirees)} commune{'s' if len(retirees) > 1 else ''} en "
                   f"{'ont' if len(retirees) > 1 else 'a'} été retirée{'s' if len(retirees) > 1 else ''}.")
    if otex is not None and not otex.empty:
        o = otex[otex["codgeo"].isin(communes["code"].astype(str))]
        o = o[~o["otex"].isin(["Sans exploitation", "Exploitations non classées"])]
        if not o.empty:
            vc = o["otex"].value_counts()
            top = ", ".join(f"{k.lower()} ({v} commune{'s' if v > 1 else ''})" for k, v in vc.head(3).items())
            phr.append(f"Les orientations technico-économiques dominantes des communes sont : {top} "
                       "(Agreste, recensement agricole 2020).")
    phr.append("[À compléter par le chargé d'études : communes des sièges des exploitations concernées, partenaires amont et "
               "aval, cohérence agricole du périmètre.]")
    return " ".join(phr)
