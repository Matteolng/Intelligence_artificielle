import plotly.express as px
import streamlit as st

from epa.sources import enregistrer
from streamlit_folium import st_folium

from epa import cartes, filieres
from epa.analyse import fnum, texte_filieres
from epa.config import FILIERES
from epa.http import DataSourceError
from epa.ui import hero, kpis, progress_callback, require_territoire, resultat, source, stocker, texte_auto, zone_epcis

hero("Filières amont et aval", "Services et approvisionnement, première transformation, collecte et négoce, coopératives et CUMA "
     "présents sur le territoire (répertoire SIRENE).", "Étape 2 sur 4 : état initial, transformation et commercialisation")
require_territoire()
t = st.session_state["territoire"]

with st.expander("Catégories et codes NAF utilisés"):
    lib = filieres.naf_libelles()
    for cat, meta in FILIERES.items():
        st.markdown(f"**{cat}** – {meta['description']}")
        st.caption(" · ".join(f"{c} {lib.get(c, '')}" for c in meta["naf"]))
    st.markdown("**Autres coopératives agricoles et CUMA** – établissements à statut coopératif non classés ci-dessus ; catégories juridiques INSEE 6316 (CUMA), 6317 (société coopérative agricole), "
                "6318 (union de sociétés coopératives agricoles).")

df = resultat("filieres")
if df is None:
    if st.button("Rechercher les établissements du territoire", type="primary"):
        bar = st.progress(0.0, text="Interrogation de l'API Recherche d'entreprises…")
        try:
            df = filieres.filieres_territoire(zone_epcis(), t.codes_communes, progress=progress_callback(bar))
        except DataSourceError as e:
            st.error(str(e))
            st.stop()
        bar.empty()
        stocker("filieres", df)
        st.rerun()
    st.stop()

if df.empty:
    st.warning("Aucun établissement trouvé.")
    st.stop()

synth = filieres.synthese_filieres(df)
kpis([
    ("Établissements actifs", fnum(len(df)), "amont, transformation, commerce, coopératives"),
    ("Établissements employeurs", fnum(int((df["eff_max"] > 0).sum())), "tranche d'effectif ≥ 1 salarié"),
    ("Effectifs salariés", f"{fnum(df['eff_min'].sum())} – {fnum(df['eff_max'].sum())}", "fourchette d'après les tranches"),
    ("Statut coopératif / CUMA", fnum(int(df["forme"].isin(["CUMA", "Société coopérative agricole", "Union de sociétés coopératives agricoles"]).sum())), "établissements, toutes catégories"),
])
texte_auto(texte_filieres(synth, len(df)))

tab1, tab2, tab3 = st.tabs(["Synthèse", "Carte", "Liste des établissements"])
with tab1:
    c1, c2 = st.columns([1, 1])
    fig = px.bar(synth.sort_values("etablissements"), x="etablissements", y="categorie", orientation="h",
                 labels={"etablissements": "Établissements", "categorie": ""}, color_discrete_sequence=["#1F5F3F"])
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=30, b=10), title="Établissements par catégorie")
    c1.plotly_chart(fig)
    c2.dataframe(synth.rename(columns={"categorie": "Catégorie", "etablissements": "Établ.", "effectif_min": "Eff. min", "effectif_max": "Eff. max", "employeurs": "Employeurs"}),
                 hide_index=True, height=380)
    st.markdown("##### Activités (NAF) les plus représentées")
    naf = df.groupby(["naf", "libelle_naf"], as_index=False).agg(etablissements=("siret", "count"), effectif_max=("eff_max", "sum"))
    st.dataframe(naf.sort_values("etablissements", ascending=False), hide_index=True, height=320)

with tab2:
    cats = sorted(df["categorie"].unique())
    sel = st.multiselect("Catégories affichées", cats, default=cats, placeholder="Choisir")
    seuil = st.slider("Effectif minimal (borne haute de tranche)", 0, 500, 0, step=5)
    d = df[df["categorie"].isin(sel) & (df["eff_max"] >= seuil)]
    m = cartes.base_map(t.bounds)
    cartes.add_territoire(m, t.communes)
    cartes.add_emprise(m, st.session_state.get("emprise"))
    pal = ["#1F5F3F", "#C8A13A", "#8E3B46", "#4F86C6", "#F28C28", "#6E9E3A", "#7A5195", "#444444"]
    colors = {c: pal[i % len(pal)] for i, c in enumerate(cats)}
    for c in sel:
        cartes.add_points(m, d[d["categorie"] == c], c, colors[c], ["nom", "libelle_naf", "effectif", "adresse", "siret"], cluster=False)
    cartes.add_legend(m, {c: colors[c] for c in sel}, "Catégories")
    cartes.finalize(m)
    st_folium(m, height=600, use_container_width=True, returned_objects=[], key="map_filieres")
    st.caption(f"{len(d)} établissements affichés ({int(d['latitude'].isna().sum())} sans coordonnées).")

with tab3:
    cols = ["nom", "enseigne", "categorie", "naf", "libelle_naf", "forme", "effectif", "annee_effectif", "commune", "adresse", "siret", "date_creation", "est_siege"]
    st.dataframe(df[cols].sort_values(["categorie", "nom"]), hide_index=True, height=520)
    st.download_button("Télécharger la liste (CSV)", df[cols].to_csv(index=False, sep=";").encode("utf-8-sig"), "filieres_territoire.csv", "text/csv")

enregistrer("sirene")
source("INSEE – SIRENE / INPI – RNE, via l'API Recherche d'entreprises (DINUM) : établissements actifs localisés sur le territoire. "
       "Le code NAF et les tranches d'effectifs sont déclaratifs : liste à vérifier et à compléter par des entretiens.")
if st.button("Relancer la recherche"):
    st.session_state.pop("res::filieres", None)
    st.rerun()
st.page_link("app_pages/p06_qualite.py", label="Étape suivante : signes de qualité et agriculture biologique", icon=":material/arrow_forward:")
