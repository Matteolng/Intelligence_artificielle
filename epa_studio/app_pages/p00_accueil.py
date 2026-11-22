import streamlit as st

from epa.branding import branding_courant
from epa.config import APP_NAME, APP_VERSION
from epa.demo import DEMO_NOM, charger_demo
from epa.http import DataSourceError

b = branding_courant()
st.markdown(
    f"""<div class="epa-home">
  <div class="etape">{APP_NAME} pour {b.nom}</div>
  <h1>L'état initial agricole d'un territoire, prêt en quelques minutes.</h1>
  <p>Cartes, chiffres clés comparés au département et à la France, figures prêtes pour le rapport :
  tout ce qui se répète d'une étude préalable agricole à l'autre est calculé depuis les données publiques,
  avec ses sources. L'analyse reste celle du chargé d'études.</p>
</div>""",
    unsafe_allow_html=True,
)

c1, c2, _ = st.columns([1.35, 1, 1.6])
if c1.button("Ouvrir la démonstration", type="primary", icon=":material/play_arrow:", width="stretch",
             help="Données publiques réelles, préchargées pour une démonstration fluide"):
    with st.spinner("Chargement du périmètre de démonstration…"):
        try:
            charger_demo(st.session_state)
        except DataSourceError as e:
            st.error(f"Le périmètre de démonstration n'a pas pu être chargé : {e}")
            st.stop()
    st.switch_page("app_pages/p04b_chiffres_cles.py")
c2.page_link("app_pages/p01_territoire.py", label="Nouveau projet", icon=":material/add:")
st.caption(f"Démonstration : {DEMO_NOM}, EPCI d'exemple et EPCI d'exemple. Vous ajoutez ensuite l'emprise de votre projet.")

st.write("")
st.markdown("#### Ce que l'outil prépare pour vous")
a, b_, c = st.columns(3, gap="large")
a.markdown("**Chiffres clés comparés**  \nExploitations, SAU et évolutions 2010-2020 du périmètre, face au département "
           "et à la France, avec la phrase de synthèse correspondante.")
b_.markdown("**Figures pour le rapport**  \nLocalisation à trois échelles, cultures RPG par année sur photo aérienne, "
            "Corine Land Cover, sols, OTEX. Export PNG 300 dpi, titre et source inclus.")
c.markdown("**Rapport, tableaux, bibliographie**  \nRapport Word structuré selon l'article D. 112-1-19 du code rural, "
           "export Excel de toutes les données, bibliographie des sources réellement interrogées.")

st.write("")
st.markdown("#### Le parcours")
etapes = [
    ("1", "Cadrage", "Territoire d'étude et emprise du projet."),
    ("2", "État initial", "Occupation agricole, exploitations, filières, qualité, foncier, atlas."),
    ("3", "Impacts", "Effets du projet, mesures ERC, compensation collective."),
    ("4", "Livrables", "Figures, rapport Word, export Excel, sources."),
]
cols = st.columns(4, gap="large")
for col, (n, t, d) in zip(cols, etapes):
    col.markdown(f'<div class="epa-step"><span>{n}</span><b>{t}</b><p>{d}</p></div>', unsafe_allow_html=True)

st.write("")
with st.expander("Données publiques mobilisées"):
    st.markdown(
        """
| Thème | Source |
|---|---|
| Limites administratives, population | DINUM, API Découpage administratif |
| Occupation agricole, cultures, bio, prairies | IGN / ASP, Registre parcellaire graphique 2015-2025 |
| Exploitations, SAU, évolutions 2010-2020 | Agreste, recensements agricoles, via l'Observatoire des territoires |
| Amont, transformation, commercialisation | INSEE, SIRENE, via l'API Recherche d'entreprises |
| Agriculture biologique | Agence Bio, annuaire des opérateurs |
| AOC/AOP, IGP/IG | INAO, data.gouv.fr |
| Prix des terres agricoles | DGFiP / Cerema, DVF |
| Occupation du sol, sols, zonages | Copernicus CLC 2018, INRAE carte des sols, Géoplateforme IGN |
"""
    )
st.caption(f"{APP_NAME} {APP_VERSION}. Les résultats n'engagent pas les services instructeurs ; les synthèses générées sont à relire.")
