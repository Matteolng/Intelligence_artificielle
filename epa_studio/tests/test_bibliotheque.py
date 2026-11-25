"""Bibliothèque partagée et projets par lien (stockage dans un dossier temporaire, sans réseau)."""
import pytest

from epa import bibliotheque as B


@pytest.fixture(autouse=True)
def lib(tmp_path, monkeypatch):
    monkeypatch.setattr(B, "LIB", tmp_path)


def test_analyse_calculee_une_fois():
    appels = []
    f = lambda: appels.append(1) or {"x": 1}  # noqa: E731
    assert B.analyse("rpg-epci", "200000001", "2025", "CC Test", "IGN / ASP", f) == {"x": 1}
    assert B.analyse("rpg-epci", "200000001", "2025", "CC Test", "IGN / ASP", f) == {"x": 1}
    assert appels == [1]
    inv = B.inventaire()
    assert inv.loc[0, "Territoire"] == "CC Test" and inv.loc[0, "Millésime"] == "2025"


def test_erreur_non_stockee():
    def boom():
        raise RuntimeError("réseau")
    with pytest.raises(RuntimeError):
        B.analyse("rpg-epci", "1", "2025", "x", "y", boom)
    assert B.inventaire().empty


def test_projet_inconnu():
    assert B.charger("000000000000", {}) is False
    assert B.charger("../../etc/passwd", {}) is False


def test_projet_aller_retour(monkeypatch):
    saved = {"territoire_cfg": {"epcis": ["1"]}, "site_commune": "63001"}
    monkeypatch.setattr(B, "serialiser", lambda state: dict(saved))
    pid = B.enregistrer({})
    restored = {}
    monkeypatch.setattr(B, "restaurer", lambda data, state: state.update(data))
    assert B.charger(pid, restored) and restored["site_commune"] == "63001" and restored["projet_id"] == pid
    assert B.projets().loc[0, "id"] == pid
