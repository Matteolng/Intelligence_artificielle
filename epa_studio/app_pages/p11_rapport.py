import json
from datetime import date

import pandas as pd
import streamlit as st

from epa import exports
from epa.ui import entete, require_territoire, resultat, stocker

entete("Étape 4 sur 4 : livrables", "Exports", "Toutes les données calculées en classeur Excel, toutes les figures en PNG 300 dpi, "
       "la bibliographie des sources consultées, et la sauvegarde du projet.", italique="et données")

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

modules = [
    ("Territoire d'étude", True, "p01_territoire.py"),
    ("Projet et emprise", pj is not None and emprise is not None, "p02_projet.py"),
    ("Chiffres clés", resultat("chiffres_cles") is not None, "p04b_chiffres_cles.py"),
    ("Occupation agricole (RPG)", resultat("rpg") is not None, "p03_occupation.py"),
    ("Le site vu par satellite", resultat("teledec") is not None, "p03b_teledetection.py"),
    ("Exploitations (RA 2020)", resultat("ra2020") is not None, "p04_exploitations.py"),
    ("Filières amont / aval", resultat("filieres") is not None, "p05_filieres.py"),
    ("SIQO et bio", resultat("siqo") is not None or resultat("bio") is not None, "p06_qualite.py"),
    ("Foncier (DVF)", resultat("dvf") is not None, "p07_foncier.py"),
    ("Effets (emprise × RPG)", resultat("rpg_emprise") is not None, "p09_effets.py"),
    ("Compensation collective", resultat("compensation") is not None, "p10_compensation.py"),
]
st.markdown("### Ce qui est déjà calculé")
cols = st.columns(4)
for i, (lbl, ok, page) in enumerate(modules):
    with cols[i % 4]:
        if ok:
            st.markdown(f":material/check_circle: {lbl}")
        else:
            st.page_link(f"app_pages/{page}", label=f"{lbl} (à calculer)", icon=":material/arrow_forward:")

st.markdown("### Classeur Excel")
c1, c2 = st.columns(2)
with c1:
    if st.button("Préparer le classeur Excel", type="primary", width="stretch"):
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
        tv = resultat("teledec")
        if tv:
            tables["Satellite séries"] = tv["series"]
            tables["Satellite bilan annuel"] = tv["bilan"]
            if tv.get("voisinage") is not None:
                tables["Satellite voisinage"] = tv["voisinage"]
        stocker("xlsx", exports.build_xlsx(tables))
    x = resultat("xlsx")
    if x:
        st.download_button("Télécharger le classeur (.xlsx)", x, f"EPA_donnees_{date.today().isoformat()}.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch")

st.markdown("### Figures")
figs = {}
for k, v in st.session_state.items():
    if str(k).startswith("res::fig::") and isinstance(v, dict) and v.get("val"):
        figs[str(k)[len("res::fig::"):]] = v["val"]
tv = resultat("teledec")
if tv:
    figs.update({k: v for k, v in tv.get("figures", {}).items() if v})
from epa.sources import bibliographie  # noqa: E402

biblio = bibliographie(st.session_state.get("sources_utilisees", {}))
if figs:
    st.caption(f"{len(figs)} figure(s) produite(s) : " + ", ".join(figs))
    st.download_button("Télécharger toutes les figures (.zip)", exports.zip_figures(figs, biblio),
                       f"EPA_figures_{date.today().isoformat()}.zip", "application/zip", icon=":material/download:")
else:
    st.page_link("app_pages/p13_figures.py", label="Produire les figures", icon=":material/arrow_forward:")

st.markdown("### Bibliographie")
if biblio:
    st.markdown("\n".join(f"- {r}" for r in biblio))
    st.download_button("Télécharger la bibliographie (.txt)", "\n".join(biblio).encode("utf-8"), "bibliographie.txt", "text/plain")
else:
    st.caption("La bibliographie se construit au fil des pages consultées.")
