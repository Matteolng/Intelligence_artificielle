"""Tests hors réseau : marque blanche, gabarits de phrases, sources, chiffres clés, composants."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from epa import branding as B
from epa.gabarits import phrase_evolution


def test_branding_defaut(tmp_path):
    b = B.charger_branding(tmp_path / "absent.toml")
    assert b.nom == "Votre bureau d'études" and b.couleur == "#2F6B3A"


def test_branding_fichier(tmp_path):
    p = tmp_path / "b.toml"
    p.write_text('[bureau]\nnom = "Bureau Test"\ncouleur = "#1a4d8f"\n', encoding="utf-8")
    b = B.charger_branding(p)
    assert b.nom == "Bureau Test" and b.couleur == "#1A4D8F"


def test_branding_couleur_invalide(tmp_path):
    p = tmp_path / "b.toml"
    p.write_text('[bureau]\ncouleur = "vert"\n', encoding="utf-8")
    assert B.charger_branding(p).couleur == "#2F6B3A"


def test_branding_session_prioritaire():
    b = B.branding_courant({"branding": {"nom": "Session", "couleur": "#000000"}})
    assert (b.nom, b.couleur) == ("Session", "#000000")


def test_phrase_baisse():
    assert phrase_evolution("Le nombre d'exploitations", False, -13.1, -14.5, -21.0) == (
        "Le nombre d'exploitations recule de 13,1 % entre 2010 et 2020, "
        "contre 14,5 % dans le département et 21,0 % en France.")


def test_phrase_sens_oppose_et_stable():
    assert phrase_evolution("La SAU", True, 2.6, 0.3, -0.8) == (
        "La SAU progresse de 2,6 % entre 2010 et 2020, contre 0,3 % dans le département et −0,8 % en France.")
    assert phrase_evolution("La SAU", True, 0.01, 1.0, None).startswith("La SAU est stable entre 2010 et 2020, contre +1,0 %")


def test_phrase_valeurs_manquantes():
    assert phrase_evolution("Le nombre d'exploitations", False, -5.0, None, -21.0) == (
        "Le nombre d'exploitations recule de 5,0 % entre 2010 et 2020, contre 21,0 % en France ; "
        "la valeur départementale n'est pas disponible.")
    assert "non disponible pour le périmètre" in phrase_evolution("X", False, np.nan, 1, 1)


# --- sources ---------------------------------------------------------------
from epa import sources as S  # noqa: E402


def test_citer_format():
    assert S.citer("clc2018") == "Union européenne – Copernicus / SDES, CORINE Land Cover – France métropolitaine (2018)"
    assert "(2023)" in S.citer("rpg:2023")


def test_bibliographie_dedoublonne_et_trie():
    state = {}
    for c in ("ra2020", "clc2018", "ra2020"):
        S.enregistrer(c, state)
    refs = S.bibliographie(state["sources_utilisees"])
    assert len(refs) == 2 and refs[0].startswith("Agreste") and "Consulté le" in refs[0]


def test_cle_inconnue_leve_keyerror():
    with pytest.raises(KeyError):
        S.enregistrer("inconnue", {})


# --- chiffres clés ---------------------------------------------------------
import geopandas as gpd  # noqa: E402
from shapely.geometry import box  # noqa: E402

from epa import chiffres_cles as C  # noqa: E402


def _df(rows):
    return pd.DataFrame(rows, columns=["codgeo", "libgeo", "exp2020", "sau2020", "evol_exp", "evol_sau"])


def test_comparaison_trois_lignes():
    com = _df([["1", "a", 10, 100, -10.0, 0.0], ["2", "b", 20, 200, -20.0, 10.0], ["3", "c", 5, 50, 0.0, 0.0]])
    dep = _df([["32", "Gers", 100, 1000, -14.5, 0.3], ["31", "HG", 300, 3000, -20.0, -1.0]])
    t = C.comparaison(com, dep, ["1", "2"], "32")
    assert list(t["Territoire"]) == ["Périmètre d'étude", "Département (32)", C.LIGNE_FRANCE]
    assert t.loc[0, "Exploitations 2020"] == 30 and t.loc[1, "Évolution exploitations 2010-2020 (%)"] == -14.5
    assert t.loc[2, "Exploitations 2020"] == 400


def test_comparaison_ignore_nan():
    com = _df([["1", "a", 10, 100, -10.0, 0.0], ["2", "b", np.nan, np.nan, np.nan, np.nan]])
    dep = _df([["32", "Gers", 100, 1000, -14.5, 0.3]])
    t = C.comparaison(com, dep, ["1", "2"], "32")
    assert t.loc[0, "Exploitations 2020"] == 10 and t.loc[0, "Communes sans donnée (secret ou absence)"] == 1
    assert round(t.loc[0, "Évolution exploitations 2010-2020 (%)"], 6) == -10.0


def test_departement_reference():
    g = gpd.GeoDataFrame({"code": ["1", "2"], "codeDepartement": ["32", "47"], "surface_ha": [10.0, 50.0]},
                         geometry=[box(0, 0, 1, 1), box(1, 0, 2, 1)], crs=4326)
    assert C.departement_reference(g, "1") == "32"
    assert C.departement_reference(g, None) == "47"


# --- composants ------------------------------------------------------------
from epa import ui  # noqa: E402


def test_tuile_valeur_manquante():
    h = ui.tuile_comparee("Exploitations", {"Périmètre": None, "Gers": -14.5}, "%")
    assert "Non disponible" in h and "−14,5 %" in h


def test_tuile_format_francais():
    assert ui.fmt_val(-13.1, "%", 1, signe=True) == "−13,1 %"
    assert ui.fmt_val(2.6, "%", 1, signe=True) == "+2,6 %"
    assert ui.fmt_val(448499, "ha") == "448 499 ha"


def test_contraste_couleur():
    assert round(B.contraste_blanc("#2F6B3A"), 2) == 6.39
    assert B.contraste_blanc("#FFD700") < 4.5
