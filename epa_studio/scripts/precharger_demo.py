"""Télécharge les données réelles du périmètre de démonstration dans demo_cache/ (livré avec l'application).

Usage : python scripts/precharger_demo.py [--lourd]
  --lourd : ajoute le RPG du périmètre (dernier millésime), SIRENE, Agence Bio et DVF (plus volumineux).
Aucune donnée n'est saisie à la main : tout provient des API publiques interrogées par l'application.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ["EPA_CACHE_DIR"] = str(ROOT / "demo_cache")
sys.path.insert(0, str(ROOT))

from epa import agreste, bio_siqo, demo, figures, rpg, territoire as T  # noqa: E402
from epa.config import RPG_LAYERS  # noqa: E402
from epa.chiffres_cles import departement_reference  # noqa: E402


def etape(msg, fn):
    print(f"- {msg}…", flush=True)
    try:
        return fn()
    except Exception as e:  # on continue : la démo signalera la donnée manquante
        print(f"  ÉCHEC : {e}")


state = {}
etape("Territoire", lambda: demo.charger_demo(state))
t = state["territoire"]
T.list_regions(); T.list_departements()
for d in t.codes_departements:
    etape(f"EPCI du département {d}", lambda d=d: T.list_epcis_departement(d))
dep = departement_reference(t.communes, demo.DEMO_COMMUNE_SITE)
etape("Communes du département (géométries)", lambda: T.communes_departement_geo(dep))
for niv in ("commune", "departement", "region"):
    etape(f"RA 2020 – {niv}", lambda niv=niv: agreste.ra2020(niv))
etape("Figure : localisation", lambda: figures.localisation_3_echelles(
    T.communes_departement_geo(dep), t.communes, t.communes[t.communes["code"] == demo.DEMO_COMMUNE_SITE], None, ("a", "b", "c")))
etape("Figure : CLC 2018", lambda: figures.carte_wms_perimetre(t.communes, "LANDCOVER.CLC18_FR", "x", "x"))
etape("Figure : sols", lambda: figures.carte_wms_perimetre(t.communes, "INRAE_CARTE-SOLS", "x", "x"))
# INAO : fichier national (~95 Mo) non embarqué ; téléchargé à la demande.
if "--lourd" in sys.argv:
    etape("RPG dernier millésime", lambda: rpg.rpg_territoire(next(iter(RPG_LAYERS.values())), t.communes))
    for d in t.codes_departements:
        etape(f"Agence Bio {d}", lambda d=d: bio_siqo.operateurs_departement(d))
print("Taille :", round(sum(p.stat().st_size for p in (ROOT / "demo_cache").rglob("*.pkl")) / 1e6, 1), "Mo")
