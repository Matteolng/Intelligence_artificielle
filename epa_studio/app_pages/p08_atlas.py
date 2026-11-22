import streamlit as st
from streamlit_folium import st_folium

from epa import cartes
from epa.config import BASEMAPS, WMS_LAYERS
from epa.ui import hero, require_territoire, source

hero("Atlas cartographique", "Superposez les couches de référence (agriculture, occupation du sol, urbanisme, environnement, énergie) "
     "au territoire et à l'emprise du projet.", "Étape 2 · État initial – contexte")
require_territoire()
t = st.session_state["territoire"]
emprise = st.session_state.get("emprise")

themes = sorted({v["theme"] for v in WMS_LAYERS.values()}, key=["Agriculture", "Occupation du sol", "Urbanisme", "Environnement", "Énergie"].index)
c1, c2 = st.columns([1, 3])
with c1:
    fond = st.radio("Fond de carte", list(BASEMAPS), index=0)
    zoom_emprise = st.checkbox("Centrer sur l'emprise du projet", value=emprise is not None)
    choix = []
    defaults = set(st.session_state.get("couches_atlas", ["RPG 2025 – parcelles PAC"]))
    for th in themes:
        with st.expander(th, expanded=th == "Agriculture"):
            for name, cfg in WMS_LAYERS.items():
                if cfg["theme"] == th and st.checkbox(name, value=name in defaults, key=f"wms_{name}"):
                    choix.append(name)
    st.session_state["couches_atlas"] = choix
with c2:
    b = tuple(emprise.total_bounds) if (zoom_emprise and emprise is not None and not emprise.empty) else t.bounds
    m = cartes.base_map(b, basemap=fond)
    cartes.add_wms(m, choix)
    cartes.add_territoire(m, t.communes)
    cartes.add_emprise(m, emprise)
    cartes.finalize(m)
    st_folium(m, height=720, use_container_width=True, returned_objects=[], key="map_atlas")
    source("Géoplateforme IGN (services WMS) : RPG (IGN/ASP), INAO, INRAE, Corine Land Cover, OCS GE, Géoportail de l'urbanisme, "
           "PatriNat (OFB/MNHN/CNRS), Cerema, gestionnaires de réseaux. Consulter les métadonnées de chaque couche pour sa date de mise à jour.")

st.caption("Astuce : l'outil de mesure (icône règle) permet de mesurer distances et surfaces ; le mode plein écran facilite les captures.")
st.page_link("app_pages/p09_effets.py", label="Étape suivante : effets du projet", icon="➡️")
