import plotly.express as px
import streamlit as st
from streamlit_folium import st_folium

from epa import bio_siqo, cartes
from epa.analyse import fnum, texte_bio, texte_siqo
from epa.http import DataSourceError
from epa.ui import hero, kpis, require_territoire, resultat, source, stocker, texte_auto

hero("Signes de qualité et agriculture biologique", "Aires AOC/AOP et IGP/IG couvrant les communes du territoire (INAO) et "
     "opérateurs engagés en agriculture biologique (Agence Bio).", "Étape 2 · État initial – qualité et valorisation")
require_territoire()
t = st.session_state["territoire"]
codes = t.codes_communes

tab1, tab2 = st.tabs(["🏅 SIQO (INAO)", "🌱 Agriculture biologique"])

with tab1:
    siqo = resultat("siqo")
    if siqo is None:
        st.caption("Premier chargement : téléchargement des fichiers INAO (≈ 45 Mo), mis ensuite en cache.")
        if st.button("📥 Charger les aires SIQO", type="primary"):
            with st.spinner("Téléchargement des fichiers INAO…"):
                try:
                    siqo = bio_siqo.siqo_territoire(codes)
                    par_c = bio_siqo.siqo_par_commune(codes)
                except DataSourceError as e:
                    st.error(str(e))
                    st.stop()
            stocker("siqo", siqo)
            stocker("siqo_communes", par_c)
            st.rerun()
    else:
        if siqo.empty:
            st.info("Aucune aire SIQO sur le territoire.")
        else:
            ao = siqo[siqo["famille"] == "AOC / AOP"]
            ig = siqo[siqo["famille"] == "IGP / IG"]
            kpis([("Aires AOC / AOP", str(len(ao)), "concernant au moins une commune"),
                  ("Aires IGP / IG", str(len(ig)), "concernant au moins une commune"),
                  ("Produits rattachés", fnum(siqo["nb_produits"].fillna(0).sum()), "toutes aires confondues")])
            texte_auto(texte_siqo(siqo))
            st.dataframe(siqo.rename(columns={"aire": "Aire géographique", "famille": "Famille", "signes": "Signe(s)",
                                              "communes_concernees": "Communes", "part_communes_pct": "Part des communes (%)",
                                              "produits": "Produits", "nb_produits": "Nb produits", "IDA": "Identifiant INAO"}),
                         hide_index=True, height=420,
                         column_config={"Part des communes (%)": st.column_config.ProgressColumn(format="%.0f %%", min_value=0, max_value=100)})
            pc = resultat("siqo_communes")
            if pc is not None:
                gc = t.communes.merge(pc, left_on="code", right_on="CI", how="left")
                gc["nb_siqo"] = gc["nb_siqo"].fillna(0)
                m = cartes.base_map(t.bounds)
                cartes.choropleth(m, gc, "nb_siqo", "Nombre d'aires SIQO", "Purples", "{:.0f}")
                cartes.add_wms(m, ["AOC viticoles – délimitation parcellaire (INAO)"], show=False)
                cartes.add_emprise(m, st.session_state.get("emprise"))
                cartes.finalize(m)
                st_folium(m, height=460, use_container_width=True, returned_objects=[], key="map_siqo")
        source("INAO – Aires géographiques des AOC/AOP et des IGP/IG par commune, et produits rattachés (data.gouv.fr, Licence Ouverte). "
               "Les délimitations officielles figurent dans les cahiers des charges.")

with tab2:
    bio = resultat("bio")
    if bio is None:
        if st.button("📥 Charger les opérateurs bio", type="primary"):
            with st.spinner("Interrogation de l'annuaire Agence Bio (par département)…"):
                try:
                    bio = bio_siqo.operateurs_bio(t.codes_departements, codes)
                except DataSourceError as e:
                    st.error(str(e))
                    st.stop()
            stocker("bio", bio)
            st.rerun()
    else:
        if bio.empty:
            st.info("Aucun opérateur bio recensé.")
        else:
            synth = bio_siqo.synthese_bio(bio)
            eng = bio[bio["etat_certification"].eq("ENGAGEE")]
            ra = resultat("ra2020")
            exp = ra["synth"][0]["Exploitations 2020"] if ra else None
            kpis([("Opérateurs engagés", fnum(len(eng)), "certification « engagée »"),
                  ("dont producteurs", fnum(int(eng["activites"].str.contains("Production", na=False).sum())), "activité de production"),
                  ("dont préparateurs", fnum(int(eng["activites"].str.contains("Préparation", na=False).sum())), "transformation"),
                  ("Certifications arrêtées", fnum(int(bio["etat_certification"].eq("ARRETEE").sum())), "historique de l'annuaire")])
            texte_auto(texte_bio(bio, exp))
            c1, c2 = st.columns([2, 3])
            fig = px.bar(synth, x="operateurs_engages", y="activite", orientation="h", labels={"operateurs_engages": "Opérateurs engagés", "activite": ""},
                         color_discrete_sequence=["#6E9E3A"])
            fig.update_layout(height=320, margin=dict(l=10, r=10, t=30, b=10))
            c1.plotly_chart(fig)
            with c2:
                m = cartes.base_map(t.bounds)
                cartes.add_territoire(m, t.communes)
                cartes.add_points(m, eng, "Opérateurs bio engagés", "#6E9E3A", ["nom", "activites", "productions", "commune"])
                cartes.add_wms(m, ["RPG 2025 – parcelles bio"], show=False)
                cartes.finalize(m)
                st_folium(m, height=420, use_container_width=True, returned_objects=[], key="map_bio")
            st.dataframe(bio.drop(columns=["latitude", "longitude"]), hide_index=True, height=360)
        source("Agence Bio – annuaire des opérateurs (opendata.agencebio.org). Opérateurs dont une adresse active est située sur le territoire.")

st.page_link("app_pages/p07_foncier.py", label="Étape suivante : foncier agricole", icon="➡️")
