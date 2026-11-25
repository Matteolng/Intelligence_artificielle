"""Démonstration sur n'importe quel point de France : la commune cliquée et son intercommunalité forment le périmètre.

Aucun territoire n'est codé en dur (pas de site client). La commune est trouvée par l'API Découpage administratif
(recherche par coordonnées). Une emprise de démonstration peut être ajoutée : elle est toujours signalée comme fictive.
"""
from __future__ import annotations

from typing import MutableMapping

import geopandas as gpd
from shapely.geometry import Point

from . import territoire as T
from .config import GEO_API
from .http import DataSourceError, disk_cache, get_json

EMPRISE_FICTIVE = "Emprise fictive de démonstration"


@disk_cache("geo")
def commune_au_point(lat: float, lon: float) -> dict | None:
    """Commune contenant le point (None hors du territoire français couvert par l'API)."""
    res = get_json(f"{GEO_API}/communes", params={"lat": round(lat, 5), "lon": round(lon, 5),
                                                  "fields": "nom,code,codeEpci,codeDepartement,codeRegion"})
    return res[0] if res else None


def perimetre_depuis_point(lat: float, lon: float) -> dict:
    """{commune, epci (ou None), nom} pour un point ; lève DataSourceError si le point n'est dans aucune commune."""
    c = commune_au_point(lat, lon)
    if not c:
        raise DataSourceError("Ce point n'est situé dans aucune commune française : cliquez sur le territoire national.")
    epci = None
    if c.get("codeEpci"):
        info = T.epci_info(c["codeEpci"])
        epci = {"code": c["codeEpci"], "nom": info.get("nom", c["codeEpci"])}
    nom = epci["nom"] if epci else c["nom"]
    return {"commune": c, "epci": epci, "nom": nom}


def emprise_fictive(lat: float, lon: float, surface_ha: float = 20.0) -> gpd.GeoDataFrame:
    """Carré de `surface_ha` centré sur le point, étiqueté comme fictif (démonstration uniquement)."""
    p = gpd.GeoSeries([Point(lon, lat)], crs=T.WGS84).to_crs(T.L93).iloc[0]
    demi = (surface_ha * 1e4) ** 0.5 / 2
    g = gpd.GeoDataFrame({"nom": [EMPRISE_FICTIVE]}, geometry=[p.buffer(demi, cap_style=3)], crs=T.L93)
    return g.to_crs(T.WGS84)


def charger_demo(state: MutableMapping, lat: float, lon: float, avec_emprise: bool = True) -> dict:
    """Construit le territoire de démonstration autour du point et le place dans l'état de session."""
    p = perimetre_depuis_point(lat, lon)
    c = p["commune"]
    # nouveau territoire : on oublie le projet précédent (emprise, identifiant de projet partagé, lien)
    for k in ("emprise", "emprise_fictive", "communes_emprise", "projet_id", "lien_projet", "projet"):
        state.pop(k, None)
    if p["epci"]:
        t = T.build_territoire([p["epci"]], nom=p["nom"])
    else:
        t = T.build_territoire([], communes_ajoutees=[c["code"]], nom=c["nom"])
    state["territoire"] = t
    state["territoire_cfg"] = {"region": t.code_region, "tous_deps": False, "departements": t.codes_departements,
                               "epcis": [p["epci"]["code"]] if p["epci"] else [], "communes_ajoutees": [] if p["epci"] else [c["code"]],
                               "communes_retirees": [], "nom": p["nom"]}
    state["site_commune"] = c["code"]
    state["mode_demo"] = True
    state["demo_point"] = (lat, lon)
    if avec_emprise:
        state["emprise"] = emprise_fictive(lat, lon)
        state["emprise_fictive"] = True
    return p
