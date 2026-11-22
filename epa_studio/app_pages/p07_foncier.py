import plotly.express as px
import streamlit as st

from epa import foncier
from epa.analyse import fnum, texte_foncier
from epa.config import DVF_DEPARTEMENTS_NON_COUVERTS, DVF_TYPES_AGRICOLES
from epa.http import DataSourceError
from epa.ui import hero, kpis, progress_callback, require_territoire, resultat, source, stocker, texte_auto

hero("Foncier agricole", "Transactions de terrains agricoles (terres et prés, vignes, vergers) issues des Demandes de valeurs "
     "foncières, et prix à l'hectare observés sur le territoire.", "Étape 2 · État initial – foncier")
require_territoire()
t = st.session_state["territoire"]

if set(t.codes_departements) & DVF_DEPARTEMENTS_NON_COUVERTS:
    st.warning("DVF ne couvre pas l'Alsace (67, 68), la Moselle (57) ni Mayotte : les communes de ces départements sont exclues.")

c1, c2, c3 = st.columns(3)
annee_min = c1.number_input("Mutations depuis l'année", min_value=2014, max_value=2026, value=2014, step=1)
types = c2.multiselect("Types de biens", list(DVF_TYPES_AGRICOLES), default=list(DVF_TYPES_AGRICOLES), format_func=lambda c: DVF_TYPES_AGRICOLES[c])
c3.write("")
c3.write("")
go = c3.button("📥 Charger les transactions", type="primary", width="stretch")

raw = resultat("dvf_raw")
if go:
    bar = st.progress(0.0, text="Interrogation de l'API Données foncières (Cerema)…")
    try:
        raw = foncier.mutations_territoire(t.codes_communes, int(annee_min), tuple(types), progress=progress_callback(bar))
    except DataSourceError as e:
        st.error(str(e))
        st.stop()
    bar.empty()
    stocker("dvf_raw", raw)
    st.session_state["dvf_annee_min"] = int(annee_min)

if raw is None:
    st.info("Le chargement interroge l'API commune par commune (environ 10 à 30 s par commune au premier appel, puis cache).")
    st.stop()
if raw.empty:
    st.warning("Aucune mutation trouvée.")
    st.stop()

with st.expander("Filtres d'exploitabilité (affichés dans le rapport)", expanded=True):
    c1, c2, c3, c4 = st.columns(4)
    smin = c1.number_input("Surface minimale (ha)", 0.0, 50.0, 0.5, 0.1)
    pmin = c2.number_input("Prix minimal (€/ha)", 0, 50_000, 100, 100)
    pmax = c3.number_input("Prix maximal (€/ha)", 1_000, 1_000_000, 100_000, 1_000)
    ventes = c4.checkbox("Ventes uniquement", True)
d = foncier.filtrer(raw, smin, pmin, pmax, ventes)
filtres = f"ventes ≥ {smin:g} ha, prix entre {fnum(pmin)} et {fnum(pmax)} €/ha, mutations mono-communales"
st_type = foncier.stats_prix(d, ["type_bien"])
st_annee = foncier.stats_prix(d, ["annee"])
stocker("dvf", {"stats": st_type, "annee": st_annee, "filtres": filtres, "data": d, "annee_min": st.session_state.get("dvf_annee_min", 2014)})

tp = st_type[st_type["type_bien"] == "Terres et prés"] if not st_type.empty else st_type
kpis([
    ("Mutations exploitables", fnum(len(d)), f"sur {fnum(len(raw))} mutations agricoles"),
    ("Surface échangée", fnum(d["surface_ha"].sum(), 0) + " ha", f"depuis {st.session_state.get('dvf_annee_min', 2014)}"),
    ("Prix médian terres et prés", (fnum(tp["prix_median_eur_ha"].iloc[0]) + " €/ha") if not tp.empty else "n.d.", "toutes années"),
    ("Prix médian toutes catégories", fnum(d["prix_eur_ha"].median()) + " €/ha" if len(d) else "n.d.", ""),
])
texte_auto(texte_foncier(st_type, st.session_state.get("dvf_annee_min", 2014), filtres))

c1, c2 = st.columns(2)
with c1:
    if not st_annee.empty:
        fig = px.line(st_annee, x="annee", y="prix_median_eur_ha", markers=True, labels={"annee": "Année", "prix_median_eur_ha": "Prix médian (€/ha)"})
        fig.update_traces(line_color="#1F5F3F")
        fig.update_layout(height=360, margin=dict(l=10, r=10, t=40, b=10), title="Prix médian annuel (toutes catégories retenues)")
        st.plotly_chart(fig)
with c2:
    if len(d):
        fig = px.box(d, x="type_bien", y="prix_eur_ha", points="outliers", labels={"type_bien": "", "prix_eur_ha": "Prix (€/ha)"},
                     color_discrete_sequence=["#C8A13A"])
        fig.update_layout(height=360, margin=dict(l=10, r=10, t=40, b=10), title="Distribution des prix par type de bien")
        st.plotly_chart(fig)

st.markdown("##### Statistiques par type de bien")
st.dataframe(st_type, hide_index=True, column_config={c: st.column_config.NumberColumn(format="%.0f") for c in st_type.columns if c != "type_bien"})
st.markdown("##### Statistiques par année")
st.dataframe(st_annee, hide_index=True, column_config={c: st.column_config.NumberColumn(format="%.0f") for c in st_annee.columns})
with st.expander("Mutations retenues"):
    st.dataframe(d, hide_index=True, height=360)
source("DGFiP – Demandes de valeurs foncières (DVF), via l'API Données foncières du Cerema (typologie DV3F). "
       "Prix = valeur foncière / surface de terrain de la mutation. Indicateur à rapprocher du barème indicatif de la valeur vénale "
       "des terres agricoles (arrêté annuel) et des références SAFER.")
st.page_link("app_pages/p08_atlas.py", label="Étape suivante : atlas cartographique", icon="➡️")
