"""Rédaction automatique de synthèses factuelles à partir des données calculées.

Les phrases ne contiennent que des valeurs issues des tableaux de l'application,
avec la source et le millésime. Elles constituent une base de rédaction que le
chargé d'études complète par son expertise et ses enquêtes de terrain.
"""
from __future__ import annotations

import math

import pandas as pd


def fnum(x, dec: int = 0, suffix: str = "") -> str:
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "n.d."
    s = f"{x:,.{dec}f}".replace(",", " ").replace(".", ",")
    return s + suffix


def _minus(txt: str) -> str:
    """Met en minuscule la première lettre seulement (préserve les sigles : CUMA, AOP…)."""
    return txt[:1].lower() + txt[1:] if txt else txt


def fpct(x, dec: int = 1) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "n.d."
    sign = "+" if x > 0 else ""
    return f"{sign}{fnum(x, dec)} %"


def texte_territoire(resume: dict) -> str:
    return (
        f"Le territoire d'étude « {resume['Nom']} » regroupe {resume['Nombre de communes']} communes "
        f"({resume['EPCI']}), sur {fnum(resume['Surface (ha)'])} ha, et compte {fnum(resume['Population (INSEE, via API Découpage administratif)'])} "
        f"habitants (population municipale diffusée par l'API Découpage administratif). Département(s) : {resume['Départements']}."
    )


def texte_rpg(ind: dict, asso: pd.DataFrame, annee: str, surface_territoire_ha: float | None = None) -> str:
    if not ind:
        return "Aucune parcelle du RPG n'a été trouvée sur le territoire."
    top = asso.head(3)
    parts = [f"{_minus(r['groupe'])} ({fnum(r['part_pct'], 1)} %)" for _, r in top.iterrows()]
    s = ind["Surface déclarée (ha)"]
    moy = ind.get("Surface moyenne d'une parcelle (ha)")
    nb = ind.get("Nombre de parcelles")
    phr = (
        f"D'après le Registre parcellaire graphique {annee}, {fnum(s)} ha sont déclarés à la PAC sur le territoire "
        f"({fnum(nb)} parcelles, {fnum(moy, 2)} ha en moyenne)"
    )
    if surface_territoire_ha:
        phr += f", soit {fnum(100 * s / surface_territoire_ha, 1)} % de la superficie du territoire"
    phr += f". Les principaux groupes de cultures sont : {', '.join(parts)}."
    pp = ind.get("Part prairies permanentes, estives et landes (%)")
    bio = ind.get("Part de la surface déclarée en bio (%)")
    if pp is not None:
        phr += f" Les prairies permanentes, estives et landes représentent {fnum(pp, 1)} % des surfaces déclarées"
    if bio is not None:
        phr += f" et les parcelles déclarées en agriculture biologique {fnum(bio, 1)} %."
    phr += " Le RPG ne recense que les surfaces déclarées à la PAC : il peut sous-estimer la SAU réelle."
    return phr


def texte_ra2020(synth: list[dict]) -> str:
    if not synth:
        return ""
    t = synth[0]
    phr = (
        f"Selon le recensement agricole 2020 (Agreste, diffusé par l'Observatoire des territoires), le territoire compte "
        f"{fnum(t['Exploitations 2020'])} exploitations ayant leur siège sur le territoire, pour une SAU de {fnum(t['SAU 2020 (ha)'])} ha, "
        f"soit {fnum(t['SAU moyenne par exploitation (ha)'], 1)} ha par exploitation en moyenne. Entre 2010 et 2020, le nombre "
        f"d'exploitations a évolué de {fpct(t['Évolution exploitations 2010-2020 (%)'])} et la SAU de {fpct(t['Évolution SAU 2010-2020 (%)'])}."
    )
    for ref in synth[1:]:
        if ref.get("Évolution exploitations 2010-2020 (%)") is not None:
            phr += (f" À titre de comparaison, {ref['Territoire']} : {fpct(ref['Évolution exploitations 2010-2020 (%)'])} "
                    f"d'exploitations et SAU moyenne de {fnum(ref['SAU moyenne par exploitation (ha)'], 1)} ha.")
    if t.get("Communes sans donnée (secret ou absence)"):
        phr += f" {t['Communes sans donnée (secret ou absence)']} commune(s) sans donnée (secret statistique ou absence d'exploitation)."
    phr += " Les données sont rattachées à la commune du siège de l'exploitation."
    return phr


def texte_filieres(synth: pd.DataFrame, n_total: int) -> str:
    if synth.empty:
        return "Aucun établissement des filières amont/aval n'a été identifié dans SIRENE sur le territoire."
    parts = [f"{_minus(r['categorie'])} : {r['etablissements']}" for _, r in synth.iterrows()]
    emin, emax = int(synth["effectif_min"].sum()), int(synth["effectif_max"].sum())
    return (
        f"{n_total} établissements actifs des filières amont et aval ont été identifiés dans le répertoire SIRENE "
        f"(API Recherche d'entreprises) : {'; '.join(parts)}. D'après les tranches d'effectifs déclarées, ils emploient "
        f"entre {fnum(emin)} et {fnum(emax)} salariés (fourchette indicative). Cette liste, fondée sur le code NAF, doit être "
        f"vérifiée et complétée par des entretiens (coopératives, négoces, abattoirs, laiteries…)."
    )


def texte_bio(df_bio: pd.DataFrame, exp2020: float | None) -> str:
    if df_bio is None or df_bio.empty:
        return "Aucun opérateur bio n'a été recensé par l'Agence Bio sur le territoire."
    eng = df_bio[df_bio["etat_certification"].eq("ENGAGEE")]
    prod = eng[eng["activites"].str.contains("Production", na=False)]
    phr = (f"L'annuaire de l'Agence Bio recense {len(eng)} opérateurs engagés en agriculture biologique sur le territoire, "
           f"dont {len(prod)} ayant une activité de production")
    if exp2020:
        phr += f" (à rapprocher des {fnum(exp2020)} exploitations du RA 2020, millésimes différents)"
    return phr + "."


def texte_siqo(siqo: pd.DataFrame) -> str:
    if siqo is None or siqo.empty:
        return "Aucune aire géographique AOC/AOP ou IGP ne concerne les communes du territoire."
    ao = siqo[siqo["famille"] == "AOC / AOP"]
    ig = siqo[siqo["famille"] == "IGP / IG"]
    phr = f"Le territoire est concerné par {len(ao)} aire(s) d'AOC/AOP et {len(ig)} aire(s) d'IGP/IG (INAO)."
    full = siqo[siqo["part_communes_pct"] >= 99.9]["aire"].tolist()
    if full:
        phr += f" Couvrent l'ensemble des communes : {', '.join(full[:12])}{'…' if len(full) > 12 else ''}."
    return phr


def texte_foncier(stats: pd.DataFrame, annee_min: int, filtres: str) -> str:
    if stats is None or stats.empty:
        return "Aucune mutation de terrain agricole exploitable n'a été trouvée dans DVF sur la période."
    parts = []
    for _, r in stats.iterrows():
        parts.append(f"{_minus(r['type_bien'])} : {int(r['mutations'])} ventes, prix médian {fnum(r['prix_median_eur_ha'])} €/ha "
                     f"(Q1–Q3 : {fnum(r['prix_q1_eur_ha'])}–{fnum(r['prix_q3_eur_ha'])} €/ha)")
    return (f"Sur les transactions DVF depuis {annee_min} ({filtres}) : " + " ; ".join(parts) +
            ". Ces valeurs issues des actes de vente sont indicatives et doivent être comparées au barème indicatif de la valeur "
            "vénale des terres agricoles et aux références SAFER.")


def texte_emprise(comp: pd.DataFrame, surface_emprise: float, surface_rpg_emprise: float, communes: list[str]) -> str:
    if comp is None or comp.empty:
        return (f"L'emprise du projet ({fnum(surface_emprise, 2)} ha) ne recoupe aucune parcelle déclarée au RPG. "
                "Vérifier sur le terrain l'usage agricole des 5 dernières années.")
    parts = [f"{_minus(r['groupe'])} ({fnum(r['emprise_ha'], 2)} ha)" for _, r in comp.iterrows()]
    return (f"L'emprise du projet couvre {fnum(surface_emprise, 2)} ha sur la(les) commune(s) de {', '.join(communes)}, dont "
            f"{fnum(surface_rpg_emprise, 2)} ha déclarés au RPG : {', '.join(parts)}.")


def texte_compensation(res: dict) -> str:
    if not res or "erreur" in res:
        return res.get("erreur", "") if res else ""
    p = res["parametres"]
    phr = (
        f"La perte de production agricole primaire est estimée à {fnum(res['perte_primaire_eur_an'])} € par an "
        f"(surface équivalente perdue : {fnum(res['surface_equivalente_perdue_ha'], 2)} ha), et à {fnum(res['perte_aval_eur_an'])} € par an "
        f"pour les filières aval (coefficient {fnum(p['coefficient_aval'], 2)}). Sur une durée de reconstitution de "
        f"{fnum(p['duree_reconstitution_ans'])} ans et avec un ratio d'investissement de {fnum(p['ratio_investissement'], 2)}, "
        f"le montant de compensation collective s'élève à {fnum(res['montant_compensation_eur'])} €."
    )
    if res.get("regime"):
        phr += f" Assiette retenue : {res['regime']}."
    if not p.get("parametres_valides"):
        phr += " ATTENTION : les paramètres n'ont pas été validés au regard de la doctrine départementale."
    return phr
