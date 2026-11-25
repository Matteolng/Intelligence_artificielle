"""Figures : 300 dpi, None si donnée absente. Le WMS est simulé (aucun accès réseau)."""
import io

import geopandas as gpd
import pandas as pd
import pytest
from PIL import Image
from shapely.geometry import box

from epa import cartes, figures as F


@pytest.fixture(autouse=True)
def wms_simule(monkeypatch):
    def fake(layer, bbox, w, h, url=None):
        b = io.BytesIO()
        Image.new("RGB", (40, 40), (200, 210, 190)).save(b, "PNG")
        return b.getvalue()
    monkeypatch.setattr(cartes, "_wms_image", fake)
    monkeypatch.setattr(F, "legende_wms", lambda couche: None)


def _g(**cols):
    return gpd.GeoDataFrame(cols, geometry=[box(0.30 + i * 0.01, 43.90, 0.31 + i * 0.01, 43.91) for i in range(len(next(iter(cols.values()))))], crs=4326)


def _dpi(png):
    return round(Image.open(io.BytesIO(png)).info["dpi"][0])


def test_png_300_dpi():
    e = _g(x=[1])
    rpg = {2021: _g(culture=["Blé tendre d'hiver"], surface_ha=[1.0]), 2022: _g(culture=["Tournesol"], surface_ha=[1.0])}
    assert _dpi(F.vignettes_rpg(e, rpg)) == 300
    com = _g(code=["32001", "32002"], codeDepartement=["32", "32"])
    assert _dpi(F.localisation_3_echelles(com, com, com.iloc[[0]], None, ("Gers", "Périmètre", "Site"))) == 300
    assert _dpi(F.carte_wms_perimetre(com, "LANDCOVER.CLC18_FR", "CLC", "test")) == 300


def test_vignettes_sans_emprise():
    assert F.vignettes_rpg(None, {2021: _g(culture=["Blé"], surface_ha=[1.0])}) is None


def test_otex_sans_fichier():
    com = _g(code=["32001"])
    assert F.carte_otex(com, None) is None
    png = F.carte_otex(com, pd.DataFrame({"codgeo": ["32001"], "otex": ["Viticulture"]}))
    assert _dpi(png) == 300


def test_otex_codes_numeriques():
    com = _g(code=["32001", "32002"])
    png = F.carte_otex(com, pd.DataFrame({"codgeo": ["32001"], "otex": [1500.0]}))
    assert _dpi(png) == 300


def test_lire_otex_codes_sur_5_caracteres():
    from epa.otex import lire_otex
    csv = "index;code_geographique;libelle_geographique;otex_12_postes\n0;1001;A;Grandes cultures\n1;2A004;B;Viticulture\n".encode()
    d = lire_otex(csv)
    assert d["codgeo"].tolist() == ["01001", "2A004"] and d["otex"].tolist() == ["Grandes cultures", "Viticulture"]
