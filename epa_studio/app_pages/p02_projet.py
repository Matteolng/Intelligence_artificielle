import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from epa import cartes, projet as P
from epa.reglementation import ZONES, test_assujettissement
from epa.ui import badge, hero, kpis, require_territoire, source

hero("Projet et emprise", "Décrivez le projet (agrivoltaïque, photovoltaïque au sol ou autre aménagement), importez ou dessinez son "
     "emprise, puis vérifiez l'assujettissement à l'étude préalable agricole.", "Étape 1 sur 4 : cadrage")
require_territoire()
t = st.session_state["territoire"]
pj: P.Projet = st.session_state.setdefault("projet", P.Projet())


def _f(x):
    return None if x is None else float(x)


tab1, tab2, tab3 = st.tabs(["Caractéristiques du projet", "Emprise", "Assujettissement et critères"])

with tab1:
    with st.form("form_projet"):
        c1, c2, c3 = st.columns(3)
        nom = c1.text_input("Nom du projet", pj.nom)
        mo = c2.text_input("Maître d'ouvrage", pj.maitre_ouvrage)
        typ = c3.selectbox("Type de projet", P.TYPES_PROJET, index=P.TYPES_PROJET.index(pj.type_projet))
        c1, c2, c3, c4 = st.columns(4)
        pui = c1.number_input("Puissance (MWc)", min_value=0.0, value=_f(pj.puissance_mwc), step=0.1, placeholder="—")
        tc = c2.number_input("Taux de couverture des sols (%)", min_value=0.0, max_value=100.0, value=_f(pj.taux_couverture_pct), step=1.0, placeholder="—")
        hmin = c3.number_input("Hauteur minimale des modules (m)", min_value=0.0, value=_f(pj.hauteur_min_m), step=0.1, placeholder="—")
        duree = c4.number_input("Durée d'exploitation (ans)", min_value=0.0, value=_f(pj.duree_exploitation_ans), step=1.0, placeholder="—")
        c1, c2 = st.columns(2)
        techno = c1.text_input("Technologie (trackers, structures fixes, persiennes…)", pj.technologie)
        prod = c2.text_input("Production agricole prévue (ex. pâturage ovin, grandes cultures…)", pj.production_agricole_prevue)
        c1, c2 = st.columns(2)
        exploitant = c1.text_input("Exploitant agricole", pj.exploitant_agricole)
        zt_opts = ["À définir", "Oui – zone témoin prévue", "Dérogation (taux < 40 % et impossibilité technique)",
                   "Dérogation (installation similaire avec zone témoin)", "Dérogation (technologie éprouvée)"]
        zt = c2.selectbox("Zone témoin", zt_opts, index=zt_opts.index(pj.zone_temoin) if pj.zone_temoin in zt_opts else 0)
        services = st.multiselect("Services apportés à la parcelle (art. L. 314-36 code de l'énergie)", P.SERVICES_AGRIVOLTAIQUES, pj.services)
        infra = st.number_input("Surfaces soustraites définitivement à la production : pistes, postes, locaux, bases de vie… (ha)",
                                min_value=0.0, value=float(pj.surface_infrastructures_ha), step=0.1)
        desc = st.text_area("Description libre du projet", pj.description, height=110)
        if st.form_submit_button("Enregistrer", type="primary"):
            st.session_state["projet"] = P.Projet(nom, mo, typ, pui, techno, tc, hmin, duree, prod, exploitant, services,
                                                  zt or "À définir", infra, desc)
            st.success("Projet enregistré.")
            pj = st.session_state["projet"]

with tab2:
    emprise = st.session_state.get("emprise")
    mode = st.segmented_control("Source de l'emprise", ["Importer un fichier SIG", "Dessiner sur la carte"], default="Importer un fichier SIG")
    if mode == "Importer un fichier SIG":
        up = st.file_uploader("GeoJSON, KML, GeoPackage ou shapefile zippé (.zip)", type=["geojson", "json", "kml", "gpkg", "zip"])
        if up is not None and st.button("Utiliser ce fichier comme emprise", type="primary"):
            try:
                st.session_state["emprise"] = P.lire_emprise(up.name, up.getvalue())
                st.session_state.pop("res::rpg_emprise", None)
                st.success("Emprise importée.")
                emprise = st.session_state["emprise"]
            except Exception as e:  # format non lisible
                st.error(f"Lecture impossible : {e}")
    fond = st.radio("Fond de carte", list(cartes.BASEMAPS), horizontal=True, index=1)
    bounds = tuple(emprise.total_bounds) if emprise is not None and not emprise.empty else t.bounds
    m = cartes.base_map(bounds, basemap=fond, draw=(mode == "Dessiner sur la carte"))
    cartes.add_wms(m, ["RPG 2025 – parcelles PAC"], show=True)
    cartes.add_territoire(m, t.communes)
    cartes.add_emprise(m, emprise)
    cartes.finalize(m)
    out = st_folium(m, height=560, use_container_width=True, key="map_emprise",
                    returned_objects=["all_drawings"] if mode == "Dessiner sur la carte" else [])
    source("RPG 2025 (IGN/ASP) ; fonds IGN Géoplateforme.")
    if mode == "Dessiner sur la carte":
        st.caption("Dessinez un ou plusieurs polygones avec les outils à gauche de la carte, puis validez.")
        if st.button("Utiliser le dessin comme emprise", type="primary"):
            e = P.emprise_depuis_dessins((out or {}).get("all_drawings"))
            if e is None:
                st.warning("Aucun polygone dessiné.")
            else:
                st.session_state["emprise"] = e
                st.session_state.pop("res::rpg_emprise", None)
                st.rerun()
    if emprise is not None and not emprise.empty:
        s = P.surface_ha(emprise)
        communes = P.communes_concernees(emprise, t.communes)
        kpis([("Surface de l'emprise", f"{s:,.2f} ha".replace(",", " "), ""),
              ("Communes concernées", str(len(communes)), ", ".join(communes)[:90] or "hors territoire !")])
        if not communes:
            st.warning("L'emprise ne recoupe aucune commune du territoire d'étude.")
        c1, c2 = st.columns(2)
        c1.download_button("Télécharger l'emprise (GeoJSON)", P.emprise_to_geojson(emprise), "emprise_projet.geojson", "application/geo+json")
        if c2.button("Supprimer l'emprise"):
            st.session_state.pop("emprise", None)
            st.session_state.pop("res::rpg_emprise", None)
            st.rerun()

with tab3:
    st.markdown("##### Test d'assujettissement (art. D. 112-1-18 du CRPM)")
    emprise = st.session_state.get("emprise")
    a = st.session_state.setdefault("assuj_cfg", {})
    c1, c2 = st.columns(2)
    ee = c1.radio("Projet soumis à évaluation environnementale systématique ?", ["Oui", "Non", "À déterminer"],
                  index=["Oui", "Non", "À déterminer"].index(a.get("ee", "À déterminer")), horizontal=True,
                  help="Rubrique de l'annexe à l'article R. 122-2 du code de l'environnement. Pour le photovoltaïque au sol, "
                       "le seuil d'évaluation systématique aurait été relevé de 1 à 3 MWc en juillet 2026 (à vérifier – voir le référentiel).")
    zone = c2.selectbox("Zonage de l'emprise", list(ZONES), index=list(ZONES).index(a["zone"]) if a.get("zone") in ZONES else 0)
    c1, c2, c3 = st.columns(3)
    inconnu = c1.checkbox("Date de dernière activité agricole inconnue", value=a.get("annees") is None)
    annees = None if inconnu else c1.number_input("Dernière activité agricole il y a (années)", min_value=0.0, value=float(a.get("annees") or 0), step=1.0)
    defaut_surf = P.surface_ha(emprise) if emprise is not None else 0.0
    surf = c2.number_input("Surface prélevée définitivement (ha)", min_value=0.0, value=float(a.get("surf", round(defaut_surf, 2))), step=0.1,
                           help="Pour un projet agrivoltaïque, la doctrine locale précise la surface à retenir (emprise clôturée, surfaces artificialisées…).")
    seuil = c3.number_input("Seuil départemental (ha)", min_value=1.0, max_value=10.0, value=float(a.get("seuil", 5.0)), step=0.5,
                            help="5 ha par défaut ; le préfet peut fixer un seuil entre 1 et 10 ha par arrêté.")
    st.session_state["assuj_cfg"] = {"ee": ee, "zone": zone, "annees": annees, "surf": surf, "seuil": seuil}
    verdict, notes = test_assujettissement(ee, zone, annees, surf, seuil)
    st.session_state["assujettissement"] = (verdict, notes)
    (st.success if verdict.startswith("Projet a priori soumis") else st.warning)(f"**{verdict}**")
    for n in notes:
        st.markdown(f"- {n}")

    if pj.type_projet == "Agrivoltaïque":
        st.markdown("##### Points de contrôle agrivoltaïques")
        ctrl = P.controle_agrivoltaique(pj)
        st.session_state["controle_agrivoltaique"] = ctrl
        df = pd.DataFrame(ctrl, columns=["Critère", "Statut", "Commentaire"])
        st.markdown(df.assign(Statut=df["Statut"].map(badge)).to_html(escape=False, index=False), unsafe_allow_html=True)
        st.caption("Critères issus de l'article L. 314-36 et du décret n° 2024-318 (art. R. 314-108 et s. du code de l'énergie). "
                   "Statut de vérification détaillé dans « Cadre réglementaire et sources ».")
    else:
        st.session_state.pop("controle_agrivoltaique", None)

st.page_link("app_pages/p03_occupation.py", label="Étape suivante : occupation agricole du territoire (RPG)", icon=":material/arrow_forward:")
