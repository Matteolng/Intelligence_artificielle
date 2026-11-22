"""Évaluation financière de l'impact et montant de compensation collective agricole.

Méthode générique paramétrable, reprenant la structure commune aux doctrines
départementales (voir epa.reglementation, thème « Compensation collective ») :

    Perte annuelle primaire  = Σ_cultures  surface_affectée_effective × produit_brut/ha
    Perte annuelle aval      = Perte annuelle primaire × coefficient filières aval
    Impact annuel total      = primaire + aval
    Impact cumulé            = Impact annuel total × durée de reconstitution (années)
    Montant de compensation  = Impact cumulé / ratio d'investissement

Pour un projet agrivoltaïque, la surface « effective » distingue :
- les surfaces soustraites définitivement à la production (pistes, postes, locaux, bases de vie, clôtures…) : perte 100 % ;
- les surfaces sous et entre les structures : perte = taux de baisse de production attendu ;
- un éventuel changement de production (ex. grandes cultures → pâturage ovin) : perte = PB avant − PB après.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd


@dataclass
class Parametres:
    type_projet: str = "Agrivoltaïque"
    surface_infrastructures_ha: float = 0.0
    taux_perte_zone_agri_pct: float = 10.0
    pb_apres_projet_eur_ha: float | None = None  # si changement de production sur la zone agrivoltaïque
    coefficient_aval: float = 0.0
    duree_reconstitution_ans: float = 7.0
    ratio_investissement: float = 1.0
    etp_pour_100ha: float | None = None
    parametres_valides: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def calcul(table_cultures: pd.DataFrame, p: Parametres) -> dict:
    """table_cultures : colonnes `groupe`, `surface_ha`, `pb_eur_ha` (surface de l'emprise par groupe de culture)."""
    t = table_cultures.copy()
    t["pb_eur_ha"] = pd.to_numeric(t["pb_eur_ha"], errors="coerce").fillna(0.0)
    s_tot = float(t["surface_ha"].sum())
    if s_tot <= 0:
        return {"erreur": "Aucune surface agricole déclarée dans l'emprise."}
    s_infra = min(max(p.surface_infrastructures_ha, 0.0), s_tot)
    part_infra = s_infra / s_tot

    if p.type_projet == "Agrivoltaïque":
        t["surface_soustraite_ha"] = t["surface_ha"] * part_infra
        t["surface_zone_agri_ha"] = t["surface_ha"] - t["surface_soustraite_ha"]
        if p.pb_apres_projet_eur_ha is not None:
            t["perte_zone_agri_eur_ha"] = (t["pb_eur_ha"] - p.pb_apres_projet_eur_ha).clip(lower=0)
        else:
            t["perte_zone_agri_eur_ha"] = t["pb_eur_ha"] * p.taux_perte_zone_agri_pct / 100
        t["perte_primaire_eur_an"] = t["surface_soustraite_ha"] * t["pb_eur_ha"] + t["surface_zone_agri_ha"] * t["perte_zone_agri_eur_ha"]
        t["surface_equivalente_perdue_ha"] = t["perte_primaire_eur_an"] / t["pb_eur_ha"].where(t["pb_eur_ha"] > 0)
    else:  # artificialisation / perte totale de la production
        t["surface_soustraite_ha"] = t["surface_ha"]
        t["surface_zone_agri_ha"] = 0.0
        t["perte_primaire_eur_an"] = t["surface_ha"] * t["pb_eur_ha"]
        t["surface_equivalente_perdue_ha"] = t["surface_ha"]

    primaire = float(t["perte_primaire_eur_an"].sum())
    aval = primaire * p.coefficient_aval
    annuel = primaire + aval
    cumule = annuel * p.duree_reconstitution_ans
    montant = cumule / p.ratio_investissement if p.ratio_investissement > 0 else float("nan")
    s_eq = float(t["surface_equivalente_perdue_ha"].fillna(0).sum())
    etp = s_eq * p.etp_pour_100ha / 100 if p.etp_pour_100ha else None
    manquants = t.loc[(t["pb_eur_ha"] <= 0) & (t["surface_ha"] > 0), "groupe"].tolist()
    return {
        "detail": t,
        "surface_emprise_agricole_ha": s_tot,
        "surface_soustraite_ha": float(t["surface_soustraite_ha"].sum()),
        "surface_equivalente_perdue_ha": s_eq,
        "perte_primaire_eur_an": primaire,
        "perte_aval_eur_an": aval,
        "impact_annuel_eur": annuel,
        "impact_cumule_eur": cumule,
        "montant_compensation_eur": montant,
        "etp_concernes": etp,
        "groupes_sans_pb": manquants,
        "parametres": p.to_dict(),
    }


def sensibilite(table_cultures: pd.DataFrame, p: Parametres, durees=(5, 7, 10), ratios=None) -> pd.DataFrame:
    ratios = ratios or sorted({1.0, p.ratio_investissement, 5.6, 6.69})
    rows = []
    for d in durees:
        for r in ratios:
            q = Parametres(**{**p.to_dict(), "duree_reconstitution_ans": d, "ratio_investissement": r})
            res = calcul(table_cultures, q)
            rows.append({"Durée de reconstitution (ans)": d, "Ratio d'investissement": r,
                         "Montant (€)": res.get("montant_compensation_eur")})
    return pd.DataFrame(rows).pivot(index="Durée de reconstitution (ans)", columns="Ratio d'investissement", values="Montant (€)")
