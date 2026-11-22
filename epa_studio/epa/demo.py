"""Mode démonstration : périmètre élargi autour de Commune-exemple (Gers), données réelles mises en cache.

Le périmètre reprend deux intercommunalités publiques (API Découpage administratif) : EPCI d'exemple
(000000000, dont fait partie Commune-exemple, code INSEE 00000) et EPCI d'exemple (000000000).
Aucune emprise de projet n'est fournie : l'utilisateur la renseigne lui-même (page Projet et emprise).
"""
from __future__ import annotations

from typing import MutableMapping

from . import territoire as T

DEMO_EPCIS = [
    {"code": "000000000", "nom": "EPCI d'exemple"},
    {"code": "000000000", "nom": "EPCI d'exemple"},
]
DEMO_COMMUNE_SITE = "00000"  # Commune-exemple
DEMO_NOM = "Périmètre élargi de Commune-exemple (Gers)"


def charger_demo(state: MutableMapping) -> None:
    """Charge le territoire de démonstration dans l'état de session (sans emprise de projet)."""
    t = T.build_territoire(DEMO_EPCIS, nom=DEMO_NOM)
    state["territoire"] = t
    state["territoire_cfg"] = {"region": t.code_region, "tous_deps": False, "departements": t.codes_departements,
                               "epcis": [e["code"] for e in DEMO_EPCIS], "communes_ajoutees": [], "communes_retirees": [],
                               "nom": DEMO_NOM}
    state["site_commune"] = DEMO_COMMUNE_SITE
    state["mode_demo"] = True
