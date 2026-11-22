"""Phrases de synthèse générées par gabarit à partir des chiffres calculés (aucune IA générative)."""
from __future__ import annotations

import math


def _ok(v) -> bool:
    return v is not None and not (isinstance(v, float) and math.isnan(v))


def _pct(v: float) -> str:
    return f"{abs(v):.1f}".replace(".", ",") + " %"


def _verbe(v: float, feminin: bool) -> str:
    if abs(v) < 0.05:
        return "est stable"
    return f"{'progresse' if v > 0 else 'recule'} de {_pct(v)}"


def phrase_evolution(sujet: str, feminin: bool, v_perim, v_dep, v_fr, periode: str = "entre 2010 et 2020") -> str:
    """Ex. « Le nombre d'exploitations recule de 13,1 % entre 2010 et 2020, contre 14,5 % dans le département et 21,0 % en France. »

    Les valeurs absentes sont signalées explicitement, jamais remplacées.
    """
    if not _ok(v_perim):
        return f"{sujet} : évolution {periode} non disponible pour le périmètre."
    base = f"{sujet} {_verbe(v_perim, feminin)} {periode}"
    refs, manquants = [], []
    for v, lieu, nom in ((v_dep, "dans le département", "départementale"), (v_fr, "en France", "nationale")):
        if _ok(v):
            meme_sens = (v > 0) == (v_perim > 0) and abs(v_perim) >= 0.05 and abs(v) >= 0.05
            refs.append(f"{_pct(v) if meme_sens else _signe(v)} {lieu}")
        else:
            manquants.append(nom)
    txt = base + (", contre " + " et ".join(refs) if refs else "")
    if manquants:
        txt += " ; la valeur " + " et la valeur ".join(manquants) + (" n'est" if len(manquants) == 1 else " ne sont") + " pas disponible" + ("" if len(manquants) == 1 else "s")
    return txt + "."


def _signe(v: float) -> str:
    if abs(v) < 0.05:
        return "une stabilité"
    return ("+" if v > 0 else "−") + _pct(v)
