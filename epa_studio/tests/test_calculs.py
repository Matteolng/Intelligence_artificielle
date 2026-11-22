"""Tests unitaires hors ligne (calculs, règles, formats)."""
import pandas as pd
import pytest

from epa import analyse, compensation as C, config
from epa.cartes import zoom_pour_emprise
from epa.filieres import naf_libelles
from epa.reglementation import test_assujettissement as assujettissement


def table():
    return pd.DataFrame({"groupe": ["Prairies permanentes", "Blé tendre"], "surface_ha": [8.0, 2.0], "pb_eur_ha": [1000.0, 2000.0]})


def test_compensation_artificialisation():
    p = C.Parametres(type_projet="Artificialisation", coefficient_aval=0.5, duree_reconstitution_ans=10, ratio_investissement=5.0)
    r = C.calcul(table(), p)
    assert r["perte_primaire_eur_an"] == pytest.approx(8 * 1000 + 2 * 2000)
    assert r["perte_aval_eur_an"] == pytest.approx(6000)
    assert r["impact_cumule_eur"] == pytest.approx(18000 * 10)
    assert r["montant_compensation_eur"] == pytest.approx(36000)


def test_compensation_agrivoltaique():
    # 1 ha soustrait sur 10 (10 %), 10 % de baisse sur le reste
    p = C.Parametres(type_projet="Agrivoltaïque", surface_infrastructures_ha=1.0, taux_perte_zone_agri_pct=10.0,
                     duree_reconstitution_ans=1, ratio_investissement=1.0)
    r = C.calcul(table(), p)
    attendu = (0.8 * 1000 + 7.2 * 1000 * 0.1) + (0.2 * 2000 + 1.8 * 2000 * 0.1)
    assert r["perte_primaire_eur_an"] == pytest.approx(attendu)
    assert r["surface_soustraite_ha"] == pytest.approx(1.0)


def test_compensation_changement_production():
    p = C.Parametres(type_projet="Agrivoltaïque", pb_apres_projet_eur_ha=500.0, duree_reconstitution_ans=1)
    r = C.calcul(table(), p)
    assert r["perte_primaire_eur_an"] == pytest.approx(8 * 500 + 2 * 1500)


def test_compensation_signale_pb_manquant():
    t = table()
    t.loc[1, "pb_eur_ha"] = 0
    r = C.calcul(t, C.Parametres())
    assert r["groupes_sans_pb"] == ["Blé tendre"]


def test_assujettissement():
    v, _ = assujettissement("Oui", "A ou N d'un PLU / zone naturelle ou agricole d'un document d'urbanisme", 1, 12, 5)
    assert v.startswith("Projet a priori soumis")
    v, _ = assujettissement("Oui", "AU d'un PLU (zone à urbaniser)", 4, 12, 5)  # délai de 3 ans dépassé
    assert "non soumis" in v
    v, _ = assujettissement("À déterminer", "A ou N d'un PLU / zone naturelle ou agricole d'un document d'urbanisme", None, 12, 5)
    assert "confirmer" in v
    v, _ = assujettissement("Oui", "A ou N d'un PLU / zone naturelle ou agricole d'un document d'urbanisme", 0, 3, 5)
    assert "non soumis" in v


def test_formats_francais():
    assert analyse.fnum(12345.678, 1) == "12 345,7"
    assert analyse.fpct(-3.25) == "-3,2 %" or analyse.fpct(-3.25) == "-3,3 %"
    assert analyse.fnum(float("nan")) == "n.d."


def test_codes_naf_existants():
    lib = naf_libelles()
    codes = set(config.NAF_PRODUCTION_AGRICOLE)
    for meta in config.FILIERES.values():
        codes |= set(meta["naf"])
    manquants = sorted(c for c in codes if c not in lib)
    assert not manquants, f"Codes NAF inconnus de la nomenclature INSEE : {manquants}"


def test_zoom():
    assert zoom_pour_emprise((2.39, 44.27, 2.66, 44.45)) in range(9, 13)
    assert zoom_pour_emprise((2.5085, 44.3365, 2.5165, 44.3415)) >= 15
