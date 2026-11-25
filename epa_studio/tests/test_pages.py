"""Tests de fumée des pages Streamlit (AppTest) sur un territoire réel.

Nécessite un accès Internet aux API publiques. Lancement : pytest -q tests/test_pages.py
"""
import os
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)

from epa import projet as P, territoire as T  # noqa: E402

EPCI = {"code": "241200187", "nom": "CA Rodez Agglomération"}
EMPRISE = (
    '{"type":"FeatureCollection","features":[{"type":"Feature","properties":{},"geometry":{"type":"Polygon","coordinates":'
    '[[[2.505,44.335],[2.520,44.335],[2.520,44.345],[2.505,44.345],[2.505,44.335]]]}}]}'
)


@pytest.fixture(scope="module")
def state():
    t = T.build_territoire([EPCI])
    return {
        "territoire": t,
        "territoire_cfg": {"region": "76", "departements": ["12"], "epcis": [EPCI["code"]], "communes_ajoutees": [], "communes_retirees": []},
        "projet": P.Projet(nom="Projet test", type_projet="Agrivoltaïque", puissance_mwc=12, taux_couverture_pct=35,
                           services=[P.SERVICES_AGRIVOLTAIQUES[1]], surface_infrastructures_ha=1.0),
        "emprise": P.emprise_from_geojson(EMPRISE),
    }


def goto(at: AppTest, page: str, clicks: list[str] | None = None) -> AppTest:
    at.switch_page(page).run()
    for label in clicks or []:
        btn = [b for b in at.button if b.label.startswith(label)]
        assert btn, f"bouton « {label} » introuvable sur {page}"
        btn[0].click().run()
    assert not at.exception, f"{page} : {[e.message for e in at.exception]}"
    return at


def res(at: AppTest, key: str):
    return at.session_state[f"res::{key}"]["val"]


def test_parcours_complet(state):
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=900)
    for k, v in state.items():
        at.session_state[k] = v
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    goto(at, "app_pages/p01_territoire.py")
    goto(at, "app_pages/p02_projet.py")
    goto(at, "app_pages/p03_occupation.py", ["Charger"])
    assert res(at, "rpg")["ind"]["Nombre de parcelles"] > 1000
    goto(at, "app_pages/p04_exploitations.py", ["Charger les données du RA 2020"])
    assert res(at, "ra2020")["synth"][0]["Exploitations 2020"] > 0
    goto(at, "app_pages/p04_exploitations.py", ["Compter"])
    goto(at, "app_pages/p05_filieres.py", ["Rechercher"])
    goto(at, "app_pages/p06_qualite.py", ["Charger les aires SIQO"])
    goto(at, "app_pages/p06_qualite.py", ["Charger les opérateurs bio"])
    goto(at, "app_pages/p07_foncier.py", ["Charger les transactions"])
    goto(at, "app_pages/p08_atlas.py")
    goto(at, "app_pages/p09_effets.py")
    assert not res(at, "rpg_emprise")["gdf"].empty
    goto(at, "app_pages/p10_compensation.py")
    assert "montant_compensation_eur" in res(at, "compensation")
    goto(at, "app_pages/p11_rapport.py", ["Préparer le classeur"])
    assert res(at, "xlsx")[:2] == b"PK"
    goto(at, "app_pages/p12_referentiel.py")
    goto(at, "app_pages/p04b_chiffres_cles.py")
    assert res(at, "chiffres_cles")["comp"].shape[0] == 4
    goto(at, "app_pages/p13_figures.py")
    goto(at, "app_pages/p14_reglages.py")
    goto(at, "app_pages/p15_bibliotheque.py")
    goto(at, "app_pages/p03b_teledetection.py")
    goto(at, "app_pages/p00_accueil.py")
