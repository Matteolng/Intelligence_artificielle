"""EPA Studio – application Streamlit d'aide à la réalisation des études préalables agricoles.

Lancement :  streamlit run app.py
"""
import streamlit as st

from epa.config import APP_NAME
from epa.ui import setup_page, sidebar_status

st.set_page_config(page_title=APP_NAME, page_icon="🌾", layout="wide", initial_sidebar_state="expanded")
setup_page()

P = "app_pages/"
pages = {
    "Démarrer": [
        st.Page(P + "p00_accueil.py", title="Accueil", icon="🏠", default=True),
    ],
    "1 · Cadrage": [
        st.Page(P + "p01_territoire.py", title="Territoire d'étude", icon="🗺️"),
        st.Page(P + "p02_projet.py", title="Projet et emprise", icon="📐"),
    ],
    "2 · État initial": [
        st.Page(P + "p03_occupation.py", title="Occupation agricole (RPG)", icon="🌾"),
        st.Page(P + "p04_exploitations.py", title="Exploitations (RA 2020)", icon="🚜"),
        st.Page(P + "p05_filieres.py", title="Filières amont / aval", icon="🏭"),
        st.Page(P + "p06_qualite.py", title="Qualité et bio (SIQO)", icon="🏅"),
        st.Page(P + "p07_foncier.py", title="Foncier agricole (DVF)", icon="💶"),
        st.Page(P + "p08_atlas.py", title="Atlas cartographique", icon="🧭"),
    ],
    "3 · Impacts": [
        st.Page(P + "p09_effets.py", title="Effets du projet et ERC", icon="⚖️"),
        st.Page(P + "p10_compensation.py", title="Compensation collective", icon="🧮"),
    ],
    "4 · Livrables": [
        st.Page(P + "p11_rapport.py", title="Rapport et exports", icon="📄"),
        st.Page(P + "p12_referentiel.py", title="Cadre réglementaire et sources", icon="📚"),
    ],
}

nav = st.navigation(pages, position="sidebar", expanded=True)
try:
    nav.run()
finally:
    # affiché après la page pour refléter les modifications faites pendant son exécution (même après st.stop())
    sidebar_status()
