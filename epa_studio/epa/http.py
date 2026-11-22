"""Accès HTTP robuste (reprises, limitation de débit) et cache disque."""
from __future__ import annotations

import hashlib
import io
import pickle
import threading
import time
from functools import wraps
from typing import Any, Callable

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import CACHE_DIR, CACHE_TTL_DAYS, USER_AGENT

_session_lock = threading.Lock()
_session: requests.Session | None = None


class DataSourceError(RuntimeError):
    """Erreur lors de l'interrogation d'une source de données externe."""


def session() -> requests.Session:
    """Session HTTP partagée, avec reprises automatiques sur erreurs transitoires."""
    global _session
    with _session_lock:
        if _session is None:
            s = requests.Session()
            retry = Retry(
                total=5,
                connect=3,
                read=3,
                backoff_factor=1.0,
                status_forcelist=(429, 500, 502, 503, 504),
                allowed_methods=frozenset({"GET", "POST"}),
                respect_retry_after_header=True,
            )
            adapter = HTTPAdapter(max_retries=retry, pool_connections=16, pool_maxsize=16)
            s.mount("https://", adapter)
            s.mount("http://", adapter)
            s.headers.update({"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate"})
            _session = s
        return _session


class RateLimiter:
    """Limiteur simple (n requêtes par seconde) partagé entre threads."""

    def __init__(self, per_second: float):
        self.min_interval = 1.0 / per_second
        self._lock = threading.Lock()
        self._last = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            delay = self._last + self.min_interval - now
            if delay > 0:
                time.sleep(delay)
            self._last = time.monotonic()


# L'API Recherche d'entreprises limite le nombre d'appels par seconde : on reste prudent.
LIMITERS = {
    "recherche-entreprises": RateLimiter(4),
    "geo": RateLimiter(20),
    "cerema": RateLimiter(5),
    "agencebio": RateLimiter(3),
}


def get(url: str, params: dict | None = None, timeout: int = 90, limiter: str | None = None,
        retries_on_html: int = 3) -> requests.Response:
    """GET avec gestion des erreurs ; lève DataSourceError avec un message lisible."""
    last_exc: Exception | None = None
    for attempt in range(retries_on_html + 1):
        if limiter:
            LIMITERS[limiter].wait()
        try:
            r = session().get(url, params=params, timeout=timeout)
        except requests.RequestException as exc:  # réseau, TLS, timeout…
            last_exc = exc
            time.sleep(1.5 * (attempt + 1))
            continue
        if r.status_code == 429:
            time.sleep(2.0 * (attempt + 1))
            last_exc = DataSourceError(f"Limite de débit atteinte ({url})")
            continue
        if r.status_code >= 400:
            raise DataSourceError(f"{url} a répondu {r.status_code} : {r.text[:200]}")
        return r
    raise DataSourceError(f"Échec de l'appel à {url} : {last_exc}")


def get_json(url: str, params: dict | None = None, timeout: int = 90, limiter: str | None = None) -> Any:
    last_err: Exception | None = None
    for attempt in range(3):
        r = get(url, params=params, timeout=timeout, limiter=limiter)
        try:
            return r.json()
        except ValueError as exc:  # page HTML d'erreur renvoyée avec un code 200
            last_err = exc
            time.sleep(2.0 * (attempt + 1))
    raise DataSourceError(f"Réponse non JSON de {url} : {last_err}")


def get_bytes(url: str, params: dict | None = None, timeout: int = 180) -> bytes:
    return get(url, params=params, timeout=timeout).content


# ---------------------------------------------------------------------------
# Cache disque (pickle) – survit aux redémarrages de l'application
# ---------------------------------------------------------------------------

def _cache_path(namespace: str, key: str):
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]
    d = CACHE_DIR / namespace
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{h}.pkl"


def disk_cache(namespace: str) -> Callable:
    """Décorateur : met en cache le résultat (picklable) d'une fonction sur disque."""
    ttl = CACHE_TTL_DAYS.get(namespace, 30) * 86400

    def deco(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            key = f"{fn.__module__}.{fn.__qualname__}|{args!r}|{sorted(kwargs.items())!r}"
            path = _cache_path(namespace, key)
            if path.exists() and (time.time() - path.stat().st_mtime) < ttl:
                try:
                    with open(path, "rb") as f:
                        return pickle.load(f)
                except Exception:  # cache corrompu : on recalcule
                    path.unlink(missing_ok=True)
            result = fn(*args, **kwargs)
            tmp = path.with_suffix(".tmp")
            with open(tmp, "wb") as f:
                pickle.dump(result, f, protocol=pickle.HIGHEST_PROTOCOL)
            tmp.replace(path)
            return result

        wrapper.cache_namespace = namespace  # type: ignore[attr-defined]
        return wrapper

    return deco


def clear_cache(namespace: str | None = None) -> int:
    """Supprime le cache disque (tout ou un espace de noms). Retourne le nombre de fichiers supprimés."""
    n = 0
    base = CACHE_DIR / namespace if namespace else CACHE_DIR
    if base.exists():
        for p in base.rglob("*.pkl"):
            p.unlink(missing_ok=True)
            n += 1
    return n


def cache_size_mb() -> float:
    total = sum(p.stat().st_size for p in CACHE_DIR.rglob("*.pkl")) if CACHE_DIR.exists() else 0
    return total / 1e6


def bytes_io(b: bytes) -> io.BytesIO:
    return io.BytesIO(b)
