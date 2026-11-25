"""Précharge les tables nationales utilisées par toute démonstration (aucun territoire particulier).

Usage : python scripts/precharger_demo.py
Écrit dans demo_cache/ (livré avec l'application) : listes des régions et départements, indicateurs du recensement
agricole 2020 aux niveaux commune, département et région, OTEX communale. Les données proviennent des services publics
interrogés par l'application ; rien n'est saisi à la main.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ["EPA_CACHE_DIR"] = str(ROOT / "demo_cache")
sys.path.insert(0, str(ROOT))

from epa import agreste, territoire as T  # noqa: E402


def etape(msg, fn):
    print(f"- {msg}…", flush=True)
    try:
        fn()
    except Exception as e:  # la démonstration signalera la donnée manquante
        print(f"  ÉCHEC : {e}")


etape("Régions et départements", lambda: (T.list_regions(), T.list_departements()))
for niv in ("commune", "departement", "region"):
    etape(f"RA 2020 – {niv}", lambda niv=niv: agreste.ra2020(niv))
try:
    from epa import otex
    etape("OTEX communale", otex.otex_communes)
except ImportError:
    pass
print("Taille :", round(sum(p.stat().st_size for p in (ROOT / "demo_cache").rglob("*.pkl")) / 1e6, 1), "Mo")
