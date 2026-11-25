"""Périmètre proposé et justification (API simulée, aucun accès réseau)."""
import geopandas as gpd
import pandas as pd
from shapely.geometry import box

from epa import perimetre as P


def _communes():
    return gpd.GeoDataFrame({"code": ["63001", "63002", "63003"], "nom": ["A", "B", "C"], "codeDepartement": ["63"] * 3,
                             "surface_ha": [1000.0, 2000.0, 1500.0]},
                            geometry=[box(3.0, 45.0, 3.1, 45.1), box(3.1, 45.0, 3.2, 45.1), box(3.2, 45.0, 3.3, 45.1)], crs=4326)


def test_proposer(monkeypatch):
    c = _communes()
    monkeypatch.setattr(P, "commune_au_point", lambda lat, lon: {"code": "63001" if lon < 3.1 else "63002", "codeEpci": "200000001"})
    monkeypatch.setattr(P.T, "epci_info", lambda code: {"nom": "CC Test"})
    monkeypatch.setattr(P.T, "build_territoire", lambda epcis, hors=None, *a, **k: type("T", (), {"communes": c})())
    emprise = gpd.GeoDataFrame(geometry=[box(3.08, 45.04, 3.12, 45.06)], crs=4326)
    r = P.proposer(emprise)
    assert r["epcis"] == [{"code": "200000001", "nom": "CC Test"}]
    assert r["communes_emprise"] == ["63001", "63002"]


def test_justification_factuelle():
    otex = pd.DataFrame({"codgeo": ["63001", "63002", "63003"], "otex": ["Grandes cultures", "Grandes cultures", "Sans exploitation"]})
    txt = P.texte_justification(_communes(), [{"code": "1", "nom": "CC Test"}], ["63001"], ajoutees=["63003"], otex=otex)
    assert txt.startswith("Le périmètre d'étude élargi regroupe 3 communes pour 45 km².")
    assert "(A) et de leur intercommunalité (CC Test)" in txt and "1 commune y a été ajoutée : C." in txt
    assert "grandes cultures (2 communes)" in txt and "sans exploitation" not in txt
    assert txt.endswith("cohérence agricole du périmètre.]")
