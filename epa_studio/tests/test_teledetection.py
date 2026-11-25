"""Télédétection : formules (catalogue Awesome Spectral Indices), règles de lecture, statistiques par zone (sans réseau)."""
import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import box

from epa import teledetection as TD

B = {"B": np.array([0.04]), "G": np.array([0.07]), "R": np.array([0.05]), "N": np.array([0.40]), "S1": np.array([0.20])}


def test_formules_conformes_au_catalogue():
    spyndex = pytest.importorskip("spyndex")
    i = TD.calcul_indices(B)
    p = {"B": 0.04, "G": 0.07, "R": 0.05, "N": 0.40, "S1": 0.20}
    assert i["NDVI"][0] == pytest.approx(spyndex.computeIndex("NDVI", p))
    assert i["NDMI"][0] == pytest.approx(spyndex.computeIndex("NDMI", p))
    assert i["MNDWI"][0] == pytest.approx(spyndex.computeIndex("MNDWI", p))
    assert i["BSI"][0] == pytest.approx(spyndex.computeIndex("BI", p))  # BSI = « BI » dans le catalogue


def test_cycles():
    s = pd.Series([0.2, 0.6, 0.8, 0.25, 0.2, 0.55, 0.7, 0.2])  # deux cycles
    assert TD.cycles(s) == 2
    assert TD.cycles(pd.Series([0.7, 0.75, 0.8, 0.72])) == 1  # prairie : un seul passage au-dessus de 0,5


def test_bilan_et_voisinage():
    dates = pd.to_datetime(["2025-03-01", "2025-05-01", "2025-07-15", "2025-09-01"])
    rows = []
    for d, nd, bs in zip(dates, [0.3, 0.85, 0.15, 0.2], [-0.1, -0.3, 0.1, 0.05]):
        rows += [(d, "site:1", "NDVI", nd, 1), (d, "site:1", "BSI", bs, 1), (d, "site:1", "NDMI", 0.1, 1), (d, "site:1", "MNDWI", -0.4, 1)]
    for k in range(10):
        rows += [(dates[1], f"voisin:{k}", "NDVI", 0.5 + k * 0.04, 1)]
    s = pd.DataFrame(rows, columns=["date", "zone", "indice", "valeur", "part_valide"])
    z = gpd.GeoDataFrame({"zone": ["site:1"] + [f"voisin:{k}" for k in range(10)], "type": ["site"] + ["voisin"] * 10,
                          "culture": ["Blé tendre d'hiver"] * 11}, geometry=[box(0, 0, 1, 1)] * 11, crs=4326)
    b = TD.bilan(s, z)
    r = b.iloc[0]
    assert (r["NDVI maximal"], r["Date du maximum"], r["Cycles de végétation"]) == (0.85, "2025-05-01", 1)
    assert r["Sol nu probable (% des dates)"] == 50 and r["Mois de sol nu"] == "juil., sept." and r["NDMI moyen juin-août"] == 0.1
    v = TD.voisinage(s, z, 2025)
    assert v.iloc[0]["Rang (percentile)"] == 90  # 0,85 dépasse 9 voisines sur 10
    assert len(TD.phrases(b, v, {"site:1": "Parcelle 1"})) == 2


def test_voisinage_non_significatif():
    s = pd.DataFrame([(pd.Timestamp("2025-05-01"), "site:1", "NDVI", 0.8, 1), (pd.Timestamp("2025-05-01"), "voisin:1", "NDVI", 0.6, 1)],
                     columns=["date", "zone", "indice", "valeur", "part_valide"])
    z = gpd.GeoDataFrame({"zone": ["site:1", "voisin:1"], "type": ["site", "voisin"], "culture": ["Maïs", "Maïs"]},
                         geometry=[box(0, 0, 1, 1)] * 2, crs=4326)
    assert pd.isna(TD.voisinage(s, z, 2025).iloc[0]["Rang (percentile)"])


def test_zones_hors_rpg():
    emp = gpd.GeoDataFrame(geometry=[box(3.0, 45.0, 3.01, 45.01)], crs=4326)  # ~ 87 ha
    site = gpd.GeoDataFrame({"culture": ["Maïs"]}, geometry=[box(3.0, 45.0, 3.005, 45.01)], crs=4326)
    z = TD.zones_analyse(emp, site, None)
    assert list(z["zone"]) == ["site:1", "hors_rpg"]
