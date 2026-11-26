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


def test_phenologie_seuil_amplitude():
    d = pd.date_range("2025-01-01", periods=12, freq="MS")
    v = pd.Series([0.2, 0.2, 0.3, 0.6, 0.8, 0.8, 0.5, 0.2, 0.2, 0.2, 0.2, 0.2], index=d)
    p = TD.phenologie(v)
    # amplitude 0,6 ; seuil 0,5 : franchi entre le 1er mars (0,3) et le 1er avril (0,6), puis entre le 1er juillet et le 1er août
    assert p["debut"] > pd.Timestamp("2025-03-01") and p["debut"] < pd.Timestamp("2025-04-01")
    assert pd.Timestamp("2025-07-01") <= p["fin"] < pd.Timestamp("2025-08-01")  # seuil atteint le 1er juillet (0,5)
    assert TD.phenologie(pd.Series([0.7, 0.72, 0.75, 0.7, 0.71, 0.73], index=d[:6])) .get("debut") is None  # prairie stable


def test_fourchette_et_position():
    dates = pd.to_datetime(["2025-04-01", "2025-05-01"])
    rows = [(d, f"voisin:{k}", "NDVI", 0.5 + 0.03 * k, 1) for d in dates for k in range(10)]
    rows += [(dates[0], "site:1", "NDVI", 0.62, 1), (dates[1], "site:1", "NDVI", 0.40, 1)]
    s = pd.DataFrame(rows, columns=["date", "zone", "indice", "valeur", "part_valide"])
    z = gpd.GeoDataFrame({"zone": ["site:1"] + [f"voisin:{k}" for k in range(10)], "type": ["site"] + ["voisin"] * 10,
                          "culture": ["Blé"] * 11}, geometry=[box(0, 0, 1, 1)] * 11, crs=4326)
    f = TD.fourchette(s, z, "Blé")
    assert len(f) == 2 and f.loc[0, "n"] == 10
    pos = TD.position_fourchette(s[s["zone"] == "site:1"][["date", "valeur"]], f)
    assert pos["dedans_pct"] == 50 and pos["sous"] == [dates[1]]


def test_fourchette_limitee_a_l_annee_du_rpg():
    rows = [(pd.Timestamp(f"{an}-05-01"), f"voisin:{k}", "NDVI", 0.8, 1) for an in (2025, 2026) for k in range(10)]
    s = pd.DataFrame(rows, columns=["date", "zone", "indice", "valeur", "part_valide"])
    z = gpd.GeoDataFrame({"zone": [f"voisin:{k}" for k in range(10)], "type": ["voisin"] * 10, "culture": ["Blé"] * 10},
                         geometry=[box(0, 0, 1, 1)] * 10, crs=4326)
    assert list(TD.fourchette(s, z, "Blé", annee=2025)["date"].dt.year) == [2025]
    assert TD.mois_txt([pd.Timestamp("2025-06-03"), pd.Timestamp("2025-07-09"), pd.Timestamp("2025-06-20")]) == "juin 2025 et juillet 2025"


def test_voisinage_dans_la_saison_de_la_culture():
    # voisins : blé, pic fin avril ; parcelle du site : même blé, plus un couvert d'hiver très vert en janvier
    d = pd.to_datetime(["2025-01-10", "2025-02-10", "2025-03-10", "2025-04-10", "2025-04-30", "2025-05-30", "2025-06-30",
                        "2025-07-30", "2025-08-30", "2025-09-30"])
    prof = [0.3, 0.3, 0.45, 0.75, 0.85, 0.7, 0.35, 0.2, 0.2, 0.2]
    rows = [(dd, f"voisin:{k}", "NDVI", v + 0.005 * k, 1) for k in range(10) for dd, v in zip(d, prof)]
    rows += [(dd, "site:1", "NDVI", v, 1) for dd, v in zip(d, [0.95] + prof[1:])]
    s = pd.DataFrame(rows, columns=["date", "zone", "indice", "valeur", "part_valide"])
    z = gpd.GeoDataFrame({"zone": ["site:1"] + [f"voisin:{k}" for k in range(10)], "type": ["site"] + ["voisin"] * 10,
                          "culture": ["Blé"] * 11}, geometry=[box(0, 0, 1, 1)] * 11, crs=4326)
    r = TD.voisinage(s, z, 2025).iloc[0]
    assert r["NDVI maximal"] == 0.85 and abs(r["Décalage du pic (jours)"]) < 7  # le couvert de janvier est hors saison


def test_cycles_ignore_valeur_isolee():
    d = pd.date_range("2025-03-01", periods=7, freq="10D")
    assert TD.cycles(pd.Series([0.2, 0.7, 0.8, 0.1, 0.8, 0.7, 0.2], index=d)) == 1  # nuage résiduel isolé


def _zones_voisinage(n):
    rows = [{"zone": "site:1", "type": "site", "culture": "Blé", "geometry": box(0, 0, 1, 1)}]
    rows += [{"zone": f"voisin:{i}", "type": "voisin", "culture": "Blé", "geometry": box(0, 0, 1, 1)} for i in range(n)]
    return gpd.GeoDataFrame(rows, geometry="geometry", crs=4326)


def test_voisinage_ignore_voisines_sans_donnee():
    dates = pd.date_range("2025-03-01", periods=12, freq="15D")
    prof = [0.2, 0.3, 0.5, 0.7, 0.85, 0.9, 0.8, 0.5, 0.3, 0.2, 0.2, 0.2]
    rows = [(d, "site:1", "NDVI", v + 0.05) for d, v in zip(dates, prof)]
    for i in range(10):
        rows += [(d, f"voisin:{i}", "NDVI", v - 0.01 * i) for d, v in zip(dates, prof)]
    for i in range(10, 14):  # voisines observées seulement hors saison
        rows += [(dates[-1], f"voisin:{i}", "NDVI", 0.2)]
    s = pd.DataFrame(rows, columns=["date", "zone", "indice", "valeur"])
    v = TD.voisinage(s, _zones_voisinage(14), 2025)
    assert v.loc[0, "Parcelles voisines comparées"] == 10 and v.loc[0, "Rang (percentile)"] == 100


def test_voisinage_parcelle_sans_image_en_saison():
    dates = pd.date_range("2025-03-01", periods=12, freq="15D")
    prof = [0.2, 0.3, 0.5, 0.7, 0.85, 0.9, 0.8, 0.5, 0.3, 0.2, 0.2, 0.2]
    rows = [(dates[-1], "site:1", "NDVI", 0.2)]
    for i in range(10):
        rows += [(d, f"voisin:{i}", "NDVI", v) for d, v in zip(dates, prof)]
    s = pd.DataFrame(rows, columns=["date", "zone", "indice", "valeur"])
    v = TD.voisinage(s, _zones_voisinage(10), 2025)
    assert pd.isna(v.loc[0, "Rang (percentile)"]) and "pas d'image" in v.loc[0, "Lecture"]


def test_phrase_date_le_rpg():
    b = pd.DataFrame([{"Zone": "site:1", "Culture RPG": "Blé tendre d'hiver", "Année": 2026, "NDVI maximal": 0.9,
                       "Date du maximum": "2026-04-20", "Cycles de végétation": 1, "Dates sans nuage": 20,
                       "Sol nu probable (% des dates)": 0, "Mois de sol nu": ""}])
    assert "culture déclarée au RPG 2025" in TD.phrases(b, pd.DataFrame(), {"site:1": "Parcelle 1"}, 2025)[0]


def test_pas_de_decalage_de_pic_sans_saison_marquee():
    dates = pd.date_range("2025-01-10", periods=24, freq="15D")
    rng = np.random.default_rng(0)
    rows = [(d, "site:1", "NDVI", 0.8 + 0.05 * rng.random()) for d in dates]
    for i in range(10):
        rows += [(d, f"voisin:{i}", "NDVI", 0.78 + 0.08 * rng.random()) for d in dates]
    s = pd.DataFrame(rows, columns=["date", "zone", "indice", "valeur"])
    v = TD.voisinage(s, _zones_voisinage(10), 2025)
    assert v.loc[0, "Saison comparée"] == "année 2025" and pd.isna(v.loc[0, "Décalage du pic (jours)"])
