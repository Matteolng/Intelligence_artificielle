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
