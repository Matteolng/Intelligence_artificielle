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
with st.expander("Sauvegarder, partager ou charger un projet", expanded=st.session_state.get("territoire") is None):
    from epa import bibliotheque as BIB

    up = st.file_uploader("Charger un fichier projet (.json)", type=["json"])
    if up is not None and st.button("Restaurer ce projet"):
        with st.spinner("Reconstruction du territoire…"):
            BIB.restaurer(json.loads(up.getvalue().decode("utf-8")), st.session_state)
        st.success("Projet restauré. Relancez les modules de calcul (les données sont en cache).")
    if st.session_state.get("territoire") is not None:
        c1, c2 = st.columns(2)
        if c1.button("Enregistrer dans la bibliothèque et obtenir un lien", type="primary", icon=":material/link:"):
            pid = BIB.enregistrer(st.session_state)
            st.session_state["lien_projet"] = pid
        if st.session_state.get("lien_projet"):
            base = str(st.context.url or "").split("?")[0]
            st.code(f"{base}?projet={st.session_state['lien_projet']}", language=None)
            st.caption("Ce lien ouvre le projet pour toute personne qui utilise cette même instance d'EPA Studio.")
        c2.download_button("Télécharger le fichier projet (.json)",
                           json.dumps(BIB.serialiser(st.session_state), ensure_ascii=False, indent=1, default=str),
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
            from epa.branding import branding_courant
            _g = branding_courant().gabarit_docx
            docx = rapport.build_docx(ctx, gabarit=_g.read_bytes() if _g else None)
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

st.markdown("#### Diapositives")
if st.button("Préparer les diapositives (PowerPoint)", icon=":material/slideshow:"):
    from pathlib import Path as _P

    from epa import diapos, theme
    from epa.branding import branding_courant
    from epa.sources import bibliographie
    from epa.ui import fmt_val

    b = branding_courant()
    cc = resultat("chiffres_cles")
    ech, phr = [], []
    if cc:
        from epa.gabarits import phrase_evolution
        noms = [t.nom, "Département", "Région", "France"]
        rows = [cc["comp"].iloc[i].to_dict() for i in range(len(cc["comp"]))]
        labels = ["Périmètre", "Département", "Région", "France"][:len(rows)] if len(rows) == 4 else ["Périmètre", "Département", "France"]
        for lab, row in zip(labels, rows):
            _codes = {"Département": (T.list_departements().set_index("code")["nom"], cc.get("dep")),
                      "Région": (T.list_regions().set_index("code")["nom"], cc.get("reg"))}
            _nom = t.nom if lab == "Périmètre" else ("Somme des départements" if lab == "France" else
                                                     _codes[lab][0].get(_codes[lab][1], row["Territoire"]))
            ech.append({"label": lab, "nom": _nom,
                        "exp": fmt_val(row.get("Exploitations 2020"), "", 0),
                        "evol_exp": fmt_val(row.get("Évolution exploitations 2010-2020 (%)"), "%", 1, signe=True),
                        "sau": fmt_val(row.get("SAU 2020 (ha)"), "ha", 0),
                        "evol_sau": fmt_val(row.get("Évolution SAU 2010-2020 (%)"), "%", 1, signe=True)})
        if len(rows) == 4:
            for col, suj in (("Évolution exploitations 2010-2020 (%)", "Le nombre d'exploitations"), ("Évolution SAU 2010-2020 (%)", "La surface agricole utilisée")):
                phr.append(phrase_evolution(suj, False, rows[0].get(col), rows[1].get(col), rows[3].get(col), v_reg=rows[2].get(col), avec_region=True))
    figs = []
    noms_fig = {"localisation": "Localisation du projet", "otex": "Orientation technico-économique des communes", "clc": "Occupation du sol",
                "sols": "Sols dominants"}
    for k, v in st.session_state.items():
        if str(k).startswith("res::fig::") and v and v.get("val"):
            cle = str(k)[len("res::fig::"):]
            figs.append((noms_fig.get(cle, "Cultures déclarées sur le site" if cle.startswith("rpg") else cle), v["val"],
                         "voir la figure (titre et source intégrés)"))
    url = theme.photo_territoire(t.communes)
    photo = theme.STATIC / url[len(theme.URL) + 1:] if url else None
    pptx = diapos.build_pptx({"titre": (pj.nom if pj else "Projet"), "territoire": t.nom, "photo": photo, "echelles": ech,
                              "phrases": phr, "figures": figs,
                              "bibliographie": bibliographie(st.session_state.get("sources_utilisees", {}))},
                             b.nom, b.couleur, police_titres=b.police_titres, police_texte=b.police_texte,
                             gabarit=b.gabarit_pptx.read_bytes() if b.gabarit_pptx else None)
    stocker("pptx", pptx)
if resultat("pptx"):
    st.download_button("Télécharger les diapositives (.pptx)", resultat("pptx"), f"EPA_diapositives_{date.today().isoformat()}.pptx",
                       "application/vnd.openxmlformats-officedocument.presentationml.presentation")
    st.caption("Diapositives générées à partir des chiffres clés et des figures déjà produites (pages Chiffres clés et Figures).")

st.info("Le rapport est une **base de rédaction** : les passages en rouge « [À compléter par le chargé d'études] » signalent les "
        "analyses qualitatives, enquêtes et justifications à apporter.", icon=":material/edit_note:")
