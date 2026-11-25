import streamlit as st

from epa import bibliotheque as BIB
from epa.ui import entete

entete(None, "Bibliothèque", italique="partagée",
       intro="Les projets enregistrés et les analyses déjà calculées sur cette instance. Une analyse d'intercommunalité "
       "faite pour un projet est réutilisée par tous les projets suivants du même secteur.")

st.markdown("### Projets")
pr = BIB.projets()
if pr.empty:
    st.caption("Aucun projet enregistré. Depuis la page Rapport et exports, enregistrez un projet pour obtenir un lien.")
else:
    base = str(st.context.url or "").split("?")[0]
    for _, r in pr.iterrows():
        c1, c2, c3 = st.columns([3, 2, 1.2])
        c1.markdown(f"**{r['Projet']}**  \n{r['Territoire']}")
        c2.caption(f"Enregistré le {r['Enregistré le']}  \n`{base}?projet={r['id']}`")
        if c3.button("Ouvrir", key=f"open_{r['id']}"):
            for k in [k for k in st.session_state if str(k).startswith("res::")]:
                del st.session_state[k]
            if BIB.charger(r["id"], st.session_state):
                st.switch_page("app_pages/p04b_chiffres_cles.py")
            st.error("Projet illisible.")

st.markdown("### Analyses déjà calculées")
inv = BIB.inventaire()
if inv.empty:
    st.caption("Aucune analyse pour l'instant : elles s'ajoutent au fil des projets (RPG par intercommunalité, etc.).")
else:
    st.dataframe(inv, hide_index=True, width="stretch")
    st.caption(f"{len(inv)} analyses, {inv['Taille (Mo)'].sum():.1f} Mo. Dossier : {BIB.LIB}".replace(".", ",", 1))
