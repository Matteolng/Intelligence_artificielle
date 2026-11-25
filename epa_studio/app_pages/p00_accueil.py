import folium
import streamlit as st
from streamlit_folium import st_folium

from epa import demo
from epa.branding import branding_courant
from epa.config import APP_NAME, APP_VERSION, BASEMAPS
from epa.http import DataSourceError
from epa.theme import URL, frise, ornement
from epa.ui import entete_nuit

b = branding_courant()
entete_nuit(
    f"{b.nom}, avec {APP_NAME}", "L'état initial agricole", "en quelques minutes.",
    "Cartes, chiffres clés à quatre échelles, figures et sources : ce qui se répète d'une étude préalable agricole à "
    "l'autre est préparé depuis les données publiques. L'analyse reste celle du chargé d'études.",
    photo=f"{URL}/accueil_ortho.jpg", credit="Photographie aérienne : IGN, Géoplateforme (zone agricole, illustration)", grand=True,
)

st.markdown('<h2 style="margin-top:.4rem">Une démonstration, <em style="color:var(--accent)">où vous voulez</em></h2>',
            unsafe_allow_html=True)
st.caption("Cliquez n'importe où sur la carte : la commune et son intercommunalité deviennent le périmètre d'étude. "
           "Aucune donnée de projet client n'est utilisée.")

c1, c2 = st.columns([1.6, 1], gap="large")
with c1:
    m = folium.Map(location=[46.6, 2.4], zoom_start=6, tiles=None, control_scale=True, min_zoom=5)
    for name in ("Photographies aériennes IGN", "Plan IGN"):
        bm = BASEMAPS[name]
        folium.TileLayer(tiles=bm["tiles"], attr=bm["attr"], name=name, overlay=False, control=True,
                         show=name == "Photographies aériennes IGN", max_zoom=19).add_to(m)
    pt = st.session_state.get("demo_choix")
    if pt:
        folium.CircleMarker(pt, radius=9, color="#DCE5BC", weight=3, fill=True, fill_color="#F4ECDF", fill_opacity=1).add_to(m)
    folium.LayerControl(collapsed=True).add_to(m)
    out = st_folium(m, height=460, use_container_width=True, returned_objects=["last_clicked"], key="carte_demo")
    clic = (out or {}).get("last_clicked")
    if clic and (round(clic["lat"], 5), round(clic["lng"], 5)) != (tuple(round(v, 5) for v in pt) if pt else None):
        st.session_state["demo_choix"] = (clic["lat"], clic["lng"])
        st.rerun()

with c2:
    pt = st.session_state.get("demo_choix")
    if not pt:
        st.markdown("**Choisissez un point sur la carte.**")
        st.caption("Zoomez si besoin : la photo aérienne aide à viser une zone agricole.")
    else:
        try:
            with st.spinner("Recherche de la commune…"):
                p = demo.perimetre_depuis_point(*pt)
        except DataSourceError as e:
            st.warning(str(e))
        else:
            c = p["commune"]
            st.markdown(f"**{c['nom']}** ({c['code']})")
            st.caption(f"Intercommunalité : {p['epci']['nom']}" if p["epci"] else "Commune sans intercommunalité : le périmètre sera la commune seule.")
            avec = st.toggle("Ajouter une emprise fictive de 20 ha", value=True,
                             help="Carré centré sur le point cliqué, signalé partout comme fictif. Remplacez-le par votre emprise.")
            if st.button("Lancer la démonstration ici", type="primary", icon=":material/play_arrow:", width="stretch"):
                with st.spinner("Construction du périmètre…"):
                    try:
                        for k in [k for k in st.session_state if str(k).startswith("res::")]:
                            del st.session_state[k]
                        demo.charger_demo(st.session_state, *pt, avec_emprise=avec)
                    except DataSourceError as e:
                        st.error(str(e))
                        st.stop()
                st.switch_page("app_pages/p04b_chiffres_cles.py")
    st.write("")
    st.page_link("app_pages/p01_territoire.py", label="Ou démarrer un vrai projet", icon=":material/add:")

st.markdown(ornement(), unsafe_allow_html=True)
st.markdown('<h2>Ce qui se répète d\'une étude à l\'autre, <em style="color:var(--accent)">préparé pour vous</em></h2>',
            unsafe_allow_html=True)
a, b_, c = st.columns(3, gap="large")
a.markdown("#### Chiffres clés à quatre échelles\nPérimètre, département, région et France, évolution 2010-2020, et la "
           "phrase de synthèse qui va avec.")
b_.markdown("#### Figures prêtes à poser\nLocalisation, cultures RPG année par année, occupation du sol, sols, OTEX. "
            "PNG 300 dpi avec titre, source et année.")
c.markdown("#### Livrables à vos couleurs\nRapport Word, diapositives PowerPoint et export Excel, avec la bibliographie "
           "des sources consultées.")

st.markdown(
    '<div class="epa-nuit"><h2 style="margin:0">Le parcours, <em>étape par étape</em></h2>'
    + frise([
        ("un", "Cadrage", "Périmètre proposé à partir de l'emprise, ajustable, recalculé en direct."),
        ("deux", "État initial", "Occupation, exploitations, filières, qualité, foncier et atlas, aux quatre échelles."),
        ("trois", "Impacts", "Cultures touchées, mesures ERC, compensation collective."),
        ("quatre", "Livrables", "Figures, rapport Word, diapositives, export Excel et bibliographie."),
    ]) + "</div>",
    unsafe_allow_html=True,
)
st.caption(f"{APP_NAME} {APP_VERSION}. Aucune donnée inventée : ce qui manque est signalé comme manquant. "
           "Les résultats n'engagent pas les services instructeurs.")
