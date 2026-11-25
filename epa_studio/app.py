"""EPA Studio – application Streamlit d'aide à la réalisation des études préalables agricoles.

Lancement :  streamlit run app.py
"""
import streamlit as st

from epa.config import APP_NAME
from epa.ui import setup_page, sidebar_status

st.set_page_config(page_title=APP_NAME, page_icon=":material/agriculture:", layout="wide", initial_sidebar_state="expanded")
setup_page()

# Ouverture d'un projet partagé par lien (?projet=<identifiant>)
_pid = st.query_params.get("projet")
if _pid and st.session_state.get("projet_id") != _pid and st.session_state.get("_projet_echec") != _pid:
    from epa import bibliotheque

    try:
        ok = bibliotheque.charger(_pid, st.session_state)
    except Exception:  # données du projet illisibles ou service indisponible
        ok = False
    if not ok:
        st.session_state["_projet_echec"] = _pid
        st.toast("Projet introuvable dans la bibliothèque de cette instance.", icon=":material/error:")

P = "app_pages/"
pages = {
    "": [
        st.Page(P + "p00_accueil.py", title="Accueil", icon=":material/home:", default=True),
    ],
    "1. Cadrage": [
        st.Page(P + "p01_territoire.py", title="Territoire d'étude", icon=":material/map:"),
        st.Page(P + "p02_projet.py", title="Projet et emprise", icon=":material/crop_free:"),
    ],
    "2. État initial": [
        st.Page(P + "p04b_chiffres_cles.py", title="Chiffres clés", icon=":material/monitoring:"),
        st.Page(P + "p03_occupation.py", title="Occupation agricole (RPG)", icon=":material/grass:"),
        st.Page(P + "p04_exploitations.py", title="Exploitations (RA 2020)", icon=":material/agriculture:"),
        st.Page(P + "p05_filieres.py", title="Filières amont et aval", icon=":material/factory:"),
        st.Page(P + "p06_qualite.py", title="Qualité et bio (SIQO)", icon=":material/verified:"),
        st.Page(P + "p07_foncier.py", title="Foncier agricole (DVF)", icon=":material/euro:"),
        st.Page(P + "p08_atlas.py", title="Atlas cartographique", icon=":material/layers:"),
    ],
    "3. Impacts": [
        st.Page(P + "p09_effets.py", title="Effets du projet et ERC", icon=":material/balance:"),
        st.Page(P + "p10_compensation.py", title="Compensation collective", icon=":material/calculate:"),
    ],
    "4. Livrables": [
        st.Page(P + "p13_figures.py", title="Figures", icon=":material/photo_library:"),
        st.Page(P + "p11_rapport.py", title="Rapport et exports", icon=":material/description:"),
        st.Page(P + "p12_referentiel.py", title="Sources et réglementation", icon=":material/menu_book:"),
    ],
    "Bibliothèque": [
        st.Page(P + "p15_bibliotheque.py", title="Projets et analyses", icon=":material/folder_shared:"),
    ],
    "Paramètres": [
        st.Page(P + "p14_reglages.py", title="Réglages", icon=":material/tune:"),
    ],
}

nav = st.navigation(pages, position="sidebar", expanded=True)
try:
    nav.run()
finally:
    # affiché après la page pour refléter les modifications faites pendant son exécution (même après st.stop())
    sidebar_status()
