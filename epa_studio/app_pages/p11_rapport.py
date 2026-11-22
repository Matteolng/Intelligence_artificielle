import json
from dataclasses import asdict
from datetime import date

import pandas as pd
import streamlit as st

from epa import cartes, projet as P, rapport, territoire as T
from epa.compensation import Parametres
from epa.config import APP_VERSION, FAMILLE_COLORS
from epa.ui import hero, require_territoire, resultat, stocker

hero("Rapport et exports", "Générez le rapport Word pré-rédigé (plan de l'article D. 112-1-19), l'export Excel de toutes les "
     "données, et sauvegardez votre projet pour le reprendre plus tard.", "Étape 4 sur 4 : livrables")

# ---------------------------------------------------------------------------
# Sauvegarde / chargement
# ---------------------------------------------------------------------------
with st.expander("Sauvegarder ou charger un projet", expanded=st.session_state.get("territoire") is None):
    up = st.file_uploader("Charger un fichier projet (.json)", type=["json"])
    if up is not None and st.button("Restaurer ce projet"):
        data = json.loads(up.getvalue().decode("utf-8"))
        cfg = data.get("territoire_cfg", {})
        terr = data.get("territoire", {})
        with st.spinner("Reconstruction du territoire…"):
            st.session_state["territoire"] = T.build_territoire(terr.get("epcis", []), cfg.get("communes_ajoutees", []),
                                                                cfg.get("communes_retirees", []), terr.get("nom"))
        st.session_state["territoire_cfg"] = cfg
        if data.get("projet"):
            st.session_state["projet"] = P.Projet(**data["projet"])
        st.session_state["emprise"] = P.emprise_from_geojson(data.get("emprise"))
        for k in ("assuj_cfg", "mesures_choix", "mesures_autres", "couches_atlas", "source_pb"):
            if k in data:
                st.session_state[k] = data[k]
        if data.get("comp_params"):
            st.session_state["comp_params"] = Parametres(**data["comp_params"])
        if data.get("pb_table"):
            st.session_state["pb_table"] = pd.DataFrame(data["pb_table"])
        if data.get("effets"):
            st.session_state["effets"] = pd.DataFrame(data["effets"])
        st.success("Projet restauré. Relancez les modules de calcul (les données sont en cache).")
    if st.session_state.get("territoire") is not None:
        t0 = st.session_state["territoire"]
        save = {
            "version": APP_VERSION,
            "date": date.today().isoformat(),
            "territoire": T.territoire_to_dict(t0),
            "territoire_cfg": st.session_state.get("territoire_cfg", {}),
            "projet": st.session_state["projet"].to_dict() if st.session_state.get("projet") else None,
            "emprise": P.emprise_to_geojson(st.session_state.get("emprise")),
            "assuj_cfg": st.session_state.get("assuj_cfg"),
            "mesures_choix": st.session_state.get("mesures_choix", []),
            "mesures_autres": st.session_state.get("mesures_autres", ""),
            "couches_atlas": st.session_state.get("couches_atlas", []),
            "source_pb": st.session_state.get("source_pb", ""),
            "comp_params": asdict(st.session_state["comp_params"]) if st.session_state.get("comp_params") else None,
            "pb_table": st.session_state["pb_table"].to_dict(orient="records") if st.session_state.get("pb_table") is not None else None,
            "effets": st.session_state["effets"].to_dict(orient="records") if st.session_state.get("effets") is not None else None,
        }
        st.download_button("Télécharger le fichier projet (.json)", json.dumps(save, ensure_ascii=False, indent=1, default=str),
                           f"projet_epa_{date.today().isoformat()}.json", "application/json")

require_territoire()
t = st.session_state["territoire"]
emprise = st.session_state.get("emprise")
pj = st.session_state.get("projet")

# ---------------------------------------------------------------------------
# État d'avancement
# ---------------------------------------------------------------------------
modules = [
    ("Territoire d'étude", True, "p01_territoire.py"),
    ("Projet et emprise", pj is not None and emprise is not None, "p02_projet.py"),
    ("Occupation agricole (RPG)", resultat("rpg") is not None, "p03_occupation.py"),
    ("Exploitations (RA 2020)", resultat("ra2020") is not None, "p04_exploitations.py"),
    ("Orientations SIRENE", resultat("naf_prod") is not None, "p04_exploitations.py"),
    ("Filières amont / aval", resultat("filieres") is not None, "p05_filieres.py"),
    ("SIQO", resultat("siqo") is not None, "p06_qualite.py"),
    ("Agriculture biologique", resultat("bio") is not None, "p06_qualite.py"),
    ("Foncier (DVF)", resultat("dvf") is not None, "p07_foncier.py"),
    ("Effets (emprise × RPG)", resultat("rpg_emprise") is not None, "p09_effets.py"),
    ("Compensation collective", resultat("compensation") is not None, "p10_compensation.py"),
]
st.markdown("##### Contenu disponible pour le rapport")
cols = st.columns(4)
for i, (lbl, ok, page) in enumerate(modules):
    with cols[i % 4]:
        if ok:
            st.markdown(f"{lbl}")
        else:
            st.page_link(f"app_pages/{page}", label=f"{lbl} (à calculer)", icon=":material/arrow_forward:")

opt_cartes = st.toggle("Inclure les cartes statiques (fond IGN) dans le rapport", value=True,
                       help="Génère des cartes PNG ; nécessite l'accès au service WMS de la Géoplateforme.")


def build_ctx() -> dict:
    ctx: dict = {"territoire_resume": t.resume()}
    ctx["communes_table"] = t.communes[["code", "nom", "codeEpci", "population", "surface_ha"]].rename(
        columns={"code": "Code INSEE", "nom": "Commune", "codeEpci": "EPCI", "population": "Population", "surface_ha": "Surface (ha)"})
    if pj is not None:
        ctx["projet"] = pj.to_dict()
    if emprise is not None and not emprise.empty:
        ctx["surface_emprise_ha"] = P.surface_ha(emprise)
        ctx["communes_emprise"] = P.communes_concernees(emprise, t.communes)
    ctx["assujettissement"] = st.session_state.get("assujettissement")
    ctx["controle_agrivoltaique"] = st.session_state.get("controle_agrivoltaique")
    ctx["mesures_erc"] = st.session_state.get("mesures_erc")
    ctx["couches_consultees"] = st.session_state.get("couches_atlas")
    from epa.sources import bibliographie
    ctx["bibliographie"] = bibliographie(st.session_state.get("sources_utilisees", {}))
    if opt_cartes:
        ctx["carte_localisation"] = cartes.carte_localisation(t.communes, emprise, f"Territoire d'étude – {t.nom}")
    ra = resultat("ra2020")
    if ra:
        ctx["ra2020_synthese"] = ra["synth"]
        if opt_cartes:
            gc = t.communes.merge(ra["communes"], left_on="code", right_on="codgeo", how="left")
            ctx["carte_ra2020"] = cartes.carte_choroplethe(gc, "evol_exp", "Évolution du nombre d'exploitations 2010-2020",
                                                           "Évolution (%)", "RdYlGn", "Agreste – RA 2020 via l'Observatoire des territoires ; fond IGN")
    imp = resultat("ra_import")
    if imp:
        ctx["ra2020_import"] = imp["df"]
        ctx["ra2020_import_source"] = imp["source"]
    ctx["naf_production"] = resultat("naf_prod")
    r = resultat("rpg")
    if r:
        annee = r["annee"].split(" ")[0]
        ctx.update({"rpg_indicateurs": r["ind"], "rpg_assolement": r["asso"], "rpg_cultures": r["cultures"].head(25), "rpg_annee": annee})
        fam = r["asso"].copy()
        ctx["graph_assolement"] = rapport.graph_barres(fam, "groupe", "surface_ha", f"Surfaces déclarées par groupe de cultures (RPG {annee})", "Surface (ha)")
        if opt_cartes:
            gc = t.communes.merge(r["communes"], left_on="code", right_on="code_commune", how="left")
            gc["Famille dominante"] = gc["Famille dominante"].fillna("Gel et divers")
            ctx["carte_rpg"] = cartes.carte_categories(gc, "Famille dominante", FAMILLE_COLORS, "Famille de cultures dominante par commune",
                                                       f"RPG {annee} (IGN/ASP) ; fond IGN", contour=t.communes, emprise=emprise)
    s = resultat("siqo")
    if s is not None:
        ctx["siqo"] = s
    b = resultat("bio")
    if b is not None:
        from epa.bio_siqo import synthese_bio

        ctx["bio"] = b
        ctx["bio_synthese"] = synthese_bio(b)
    f = resultat("filieres")
    if f is not None and not f.empty:
        from epa.filieres import synthese_filieres

        ctx["filieres_synthese"] = synthese_filieres(f)
        top = f[f["eff_max"] >= 10].sort_values("eff_max", ascending=False)
        ctx["filieres_principales"] = top[["nom", "categorie", "libelle_naf", "effectif", "commune"]].rename(columns={
            "nom": "Établissement", "categorie": "Catégorie", "libelle_naf": "Activité", "effectif": "Effectif", "commune": "Commune"})
        if opt_cartes:
            ctx["carte_filieres"] = cartes.carte_points(t.communes, f, "categorie", "Établissements des filières amont et aval",
                                                        "INSEE – SIRENE (API Recherche d'entreprises) ; fond IGN")
    d = resultat("dvf")
    if d is not None:
        ctx["dvf_stats"] = d["stats"]
        ctx["dvf_filtres"] = d["filtres"]
        ctx["dvf_annee_min"] = d["annee_min"]
        if not d["annee"].empty:
            ctx["graph_dvf"] = rapport.graph_ligne(d["annee"], "annee", "prix_median_eur_ha", "Prix médian des terres agricoles (€/ha)", "€/ha")
    e = resultat("rpg_emprise")
    if e is not None and not e["comparaison"].empty:
        ctx["emprise_comparaison"] = e["comparaison"]
        ctx["surface_rpg_emprise_ha"] = float(e["gdf"]["surface_ha"].sum())
        if opt_cartes:
            ctx["carte_emprise"] = cartes.carte_categories(e["gdf"], "famille", FAMILLE_COLORS, "Cultures déclarées dans l'emprise du projet",
                                                           f"RPG {e['annee'].split(' ')[0]} (IGN/ASP) ; fond IGN", contour=emprise, emprise=emprise)
    c = resultat("compensation")
    if c is not None:
        ctx["compensation"] = c
        ctx["compensation_sensibilite"] = resultat("compensation_sens")
    return ctx


c1, c2 = st.columns(2)
with c1:
    if st.button("Générer le rapport Word", type="primary", width="stretch"):
        with st.spinner("Génération des cartes et du document…"):
            ctx = build_ctx()
            docx = rapport.build_docx(ctx)
        stocker("docx", docx)
    docx = resultat("docx")
    if docx:
        st.download_button("Télécharger le rapport (.docx)", docx, f"EPA_etat_initial_{date.today().isoformat()}.docx",
                           "application/vnd.openxmlformats-officedocument.wordprocessingml.document", width="stretch")
with c2:
    if st.button("Préparer l'export Excel", width="stretch"):
        tables = {"Communes": t.communes.drop(columns="geometry")}
        r = resultat("rpg")
        if r:
            tables.update({"RPG assolement": r["asso"], "RPG cultures": r["cultures"], "RPG par commune": r["communes"]})
        ev = resultat("rpg_evolution")
        if ev is not None:
            tables["RPG évolution"] = ev
        ra = resultat("ra2020")
        if ra:
            tables.update({"RA2020 communes": ra["communes"], "RA2020 comparaison": pd.DataFrame(ra["synth"])})
        imp = resultat("ra_import")
        if imp:
            tables["RA2020 import"] = imp["df"]
        for k, n in (("naf_prod", "SIRENE production"), ("filieres", "Filières établissements"), ("siqo", "SIQO"), ("bio", "Bio opérateurs")):
            v = resultat(k)
            if v is not None:
                tables[n] = v
        d = resultat("dvf")
        if d:
            tables.update({"DVF par type": d["stats"], "DVF par année": d["annee"], "DVF mutations": d["data"]})
        e = resultat("rpg_emprise")
        if e:
            tables["Emprise cultures"] = e["comparaison"]
            tables["Emprise parcelles"] = pd.DataFrame(e["gdf"].drop(columns="geometry"))
        c = resultat("compensation")
        if c:
            tables["Compensation détail"] = c["detail"]
            tables["Compensation résultats"] = pd.DataFrame([{k: v for k, v in c.items() if isinstance(v, (int, float))}])
        if st.session_state.get("effets") is not None:
            tables["Grille des effets"] = st.session_state["effets"]
        stocker("xlsx", rapport.build_xlsx(tables))
    x = resultat("xlsx")
    if x:
        st.download_button("Télécharger l'export (.xlsx)", x, f"EPA_donnees_{date.today().isoformat()}.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch")

st.info("Le rapport est une **base de rédaction** : les passages en rouge « [À compléter par le chargé d'études] » signalent les "
        "analyses qualitatives, enquêtes et justifications à apporter.", icon=":material/edit_note:")
