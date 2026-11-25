import importlib
import pickle

from epa import http


def test_cache_repli_demo(tmp_path, monkeypatch):
    monkeypatch.setattr(http, "CACHE_DIR", tmp_path / "user")
    monkeypatch.setattr(http, "DEMO_CACHE_DIR", tmp_path / "demo")
    calls = []

    @http.disk_cache("geo")
    def f(x):
        calls.append(x)
        return "réseau"

    key = f"{f.__module__}.{f.__qualname__}|{(1,)!r}|{[]!r}"
    d = tmp_path / "demo" / "geo"
    d.mkdir(parents=True)
    import hashlib
    (d / (hashlib.sha256(key.encode()).hexdigest()[:32] + ".pkl")).write_bytes(pickle.dumps("démo"))
    assert f(1) == "démo" and calls == []
    assert f(2) == "réseau" and calls == [2]


# --- démonstration par clic (API simulée) ---------------------------------
import pytest  # noqa: E402

from epa import demo as D  # noqa: E402
from epa.http import DataSourceError  # noqa: E402


def test_point_hors_france(monkeypatch):
    monkeypatch.setattr(D, "commune_au_point", lambda lat, lon: None)
    with pytest.raises(DataSourceError):
        D.perimetre_depuis_point(47.0, -12.0)


def test_point_sans_epci(monkeypatch):
    monkeypatch.setattr(D, "commune_au_point", lambda lat, lon: {"nom": "Île-test", "code": "29999", "codeEpci": None,
                                                                   "codeDepartement": "29", "codeRegion": "53"})
    p = D.perimetre_depuis_point(48.4, -5.1)
    assert p["epci"] is None and p["nom"] == "Île-test"


def test_point_avec_epci(monkeypatch):
    monkeypatch.setattr(D, "commune_au_point", lambda lat, lon: {"nom": "A", "code": "63001", "codeEpci": "200000001",
                                                                   "codeDepartement": "63", "codeRegion": "84"})
    monkeypatch.setattr(D.T, "epci_info", lambda code: {"nom": "CC Test"})
    assert D.perimetre_depuis_point(45.9, 3.27)["epci"] == {"code": "200000001", "nom": "CC Test"}


def test_emprise_fictive_surface():
    from epa.projet import surface_ha
    e = D.emprise_fictive(45.9, 3.27, 20)
    assert abs(surface_ha(e) - 20) < 0.01 and e["nom"].iloc[0] == D.EMPRISE_FICTIVE
