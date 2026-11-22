import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_folium import st_folium

from epa import cartes, rpg
from epa.analyse import fnum, texte_emprise
from epa.config import FAMILLE_COLORS, RPG_LAYERS
from epa.http import DataSourceError
from epa.projet import communes_concernees, surface_ha
from epa.ui import hero, kpis, require_territoire, resultat, source, stocker, texte_auto

hero("Effets du projet sur l'économie agricole", "Cultures et surfaces déclarées concernées par l'emprise, part dans le territoire, "
     "grille des effets et mesures d'évitement / réduction.", "Étape 3 · Impacts")
require_territoire()
t = st.session_state["territoire"]
emprise = st.session_state.get("emprise")
if emprise is None or emprise.empty:
    st.info("Renseignez d'abord l'**emprise du projet** (import ou dessin).", icon="📐")
    st.page_link("app_pages/p02_projet.py", label="Définir l'emprise", icon="📐")
    st.stop()

rt = resultat("rpg")
annee = rt["annee"] if rt else list(RPG_LAYERS)[0]
re_ = resultat("rpg_emprise")
if re_ is None or re_.get("annee") != annee:
    with st.spinner("Croisement de l'emprise avec le RPG…"):
        try:
            ge = rpg.rpg_emprise(RPG_LAYERS[annee], emprise)
        except DataSourceError as e:
            st.error(str(e))
            st.stop()
    comp = rpg.comparaison_emprise(ge, rt["gdf"]) if (rt is not None and not ge.empty) else (
        ge.groupby("groupe", as_index=False)["surface_ha"].sum().rename(columns={"surface_ha": "emprise_ha"}) if not ge.empty else pd.DataFrame())
    re_ = {"annee": annee, "gdf": ge, "comparaison": comp}
    stocker("rpg_emprise", re_)

ge, comp = re_["gdf"], re_["comparaison"]
s_emp = surface_ha(emprise)
s_rpg = float(ge["surface_ha"].sum()) if not ge.empty else 0.0
communes = communes_concernees(emprise, t.communes)
kpis([
    ("Emprise du projet", fnum(s_emp, 2) + " ha", ", ".join(communes)[:60]),
    ("Surfaces déclarées PAC", fnum(s_rpg, 2) + " ha", f"{fnum(100 * s_rpg / s_emp, 1) if s_emp else 'n.d.'} % de l'emprise"),
    ("Parcelles / îlots RPG", f"{len(ge)} / {ge['num_ilot'].nunique() if 'num_ilot' in ge else 'n.d.'}", f"RPG {annee.split(' ')[0]}"),
    ("Part de la SAU déclarée du territoire", (fnum(100 * s_rpg / rt["ind"]["Surface déclarée (ha)"], 2) + " %") if rt else "charger le RPG", ""),
])
texte_auto(texte_emprise(comp, s_emp, s_rpg, communes))
if rt is None:
    st.caption("Chargez le RPG du territoire (page Occupation agricole) pour comparer l'emprise au territoire.")

c1, c2 = st.columns([3, 2])
with c1:
    m = cartes.base_map(tuple(emprise.total_bounds), basemap="Photographies aériennes IGN")
    if not ge.empty:
        gp = ge[["culture", "groupe", "famille", "surface_ha", "geometry"]].copy()
        gp["surface_ha"] = gp["surface_ha"].round(2)
        cartes.categorical(m, gp, "famille", FAMILLE_COLORS, "Parcelles RPG dans l'emprise", ["culture", "groupe", "surface_ha"], ["Culture", "Groupe", "Surface dans l'emprise (ha)"])
        cartes.add_legend(m, {k: v for k, v in FAMILLE_COLORS.items() if k in set(gp["famille"])}, "Familles de cultures")
    cartes.add_wms(m, ["Parcellaire cadastral (PCI)"], show=False)
    cartes.add_emprise(m, emprise)
    cartes.finalize(m)
    st_folium(m, height=520, use_container_width=True, returned_objects=[], key="map_effets")
with c2:
    if not comp.empty:
        fig = px.bar(comp.sort_values("emprise_ha"), x="emprise_ha", y="groupe", orientation="h",
                     labels={"emprise_ha": "Surface dans l'emprise (ha)", "groupe": ""}, color_discrete_sequence=["#C0392B"])
        fig.update_layout(height=300, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig)
        st.dataframe(comp.rename(columns={"groupe": "Groupe", "emprise_ha": "Emprise (ha)", "territoire_ha": "Territoire (ha)", "part_du_territoire_pct": "Part du territoire (%)"}),
                     hide_index=True, column_config={"Part du territoire (%)": st.column_config.NumberColumn(format="%.2f")})
if not ge.empty:
    with st.expander("Parcelles concernées"):
        cols = [c for c in ["num_ilot", "num_parcel", "culture", "groupe", "surface_ha", "surface_parcelle_ha", "bio", "pp"] if c in ge.columns]
        st.dataframe(ge[cols].rename(columns={"surface_ha": "Surface dans l'emprise (ha)", "surface_parcelle_ha": "Surface de la parcelle (ha)"}), hide_index=True)
source(f"RPG {annee.split(' ')[0]} (IGN / ASP) croisé avec l'emprise ; surfaces calculées en Lambert-93. Les îlots du RPG sont anonymisés : "
       "l'identification des exploitations concernées relève des enquêtes.")

st.divider()
st.markdown("##### Grille des effets sur l'économie agricole")
st.caption("Grille de travail à compléter par le chargé d'études (reprise dans le rapport).")
defaut = pd.DataFrame([
    {"Effet": "Perte ou réduction de surface productive", "Sens": "Négatif", "Intensité": "À évaluer", "Commentaire": ""},
    {"Effet": "Variation de rendement sous les structures", "Sens": "À évaluer", "Intensité": "À évaluer", "Commentaire": ""},
    {"Effet": "Contraintes d'exploitation (accès, mécanisation, clôtures)", "Sens": "Négatif", "Intensité": "À évaluer", "Commentaire": ""},
    {"Effet": "Effets sur les filières aval (volumes collectés, transformés)", "Sens": "À évaluer", "Intensité": "À évaluer", "Commentaire": ""},
    {"Effet": "Emploi agricole et para-agricole", "Sens": "À évaluer", "Intensité": "À évaluer", "Commentaire": ""},
    {"Effet": "Revenu complémentaire de l'exploitant (loyer, rémunération)", "Sens": "Positif", "Intensité": "À évaluer", "Commentaire": ""},
    {"Effet": "Services agronomiques (ombrage, protection contre les aléas…)", "Sens": "Positif", "Intensité": "À évaluer", "Commentaire": ""},
    {"Effet": "Marché foncier local (prix, accès au foncier)", "Sens": "À évaluer", "Intensité": "À évaluer", "Commentaire": ""},
    {"Effet": "Effets cumulés avec d'autres projets connus", "Sens": "À évaluer", "Intensité": "À évaluer", "Commentaire": ""},
])
effets = st.data_editor(st.session_state.get("effets", defaut), num_rows="dynamic", hide_index=True, key="ed_effets",
                        column_config={"Sens": st.column_config.SelectboxColumn(options=["Positif", "Négatif", "Neutre", "À évaluer"]),
                                       "Intensité": st.column_config.SelectboxColumn(options=["Faible", "Modérée", "Forte", "À évaluer"])})
st.session_state["effets"] = effets

st.markdown("##### Mesures d'évitement et de réduction")
suggestions = [
    "Évitement des parcelles à fort potentiel (irriguées, en AOP, à haute valeur agronomique)",
    "Réduction de l'emprise des pistes, postes et locaux techniques",
    "Hauteur et espacement des structures compatibles avec le matériel agricole",
    "Maintien d'une production agricole principale et d'un exploitant identifié (bail, convention)",
    "Protocole de suivi agronomique avec zone témoin",
    "Phasage des travaux hors périodes sensibles pour l'exploitation",
    "Garantie de démantèlement et de remise en état des sols",
]
choix = st.multiselect("Mesures à intégrer (suggestions)", suggestions, default=st.session_state.get("mesures_choix", []))
autres = st.text_area("Autres mesures (une par ligne)", st.session_state.get("mesures_autres", ""))
st.session_state["mesures_choix"] = choix
st.session_state["mesures_autres"] = autres
st.session_state["mesures_erc"] = choix + [l.strip() for l in autres.splitlines() if l.strip()]
st.page_link("app_pages/p10_compensation.py", label="Étape suivante : compensation collective", icon="➡️")
