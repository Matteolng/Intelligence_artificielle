import streamlit as st

from epa.sources import enregistrer
from streamlit_folium import st_folium

from epa import cartes, territoire as T
from epa.analyse import fnum
from epa.http import DataSourceError
from epa.ui import hero, kpis, source, sources, texte_auto
from epa.analyse import texte_territoire

hero("Territoire d'étude", "Sélectionnez la région, le(s) département(s) et la ou les intercommunalités composant le "
     "territoire concerné par le projet. Vous pouvez ensuite ajouter ou retirer des communes.", "Étape 1 sur 4 : cadrage")

try:
    regions = T.list_regions()
    deps = T.list_departements()
except DataSourceError as e:
    st.error(f"Impossible de joindre l'API Découpage administratif : {e}")
    st.stop()

cfg = st.session_state.setdefault("territoire_cfg", {})

# --- Proposition automatique à partir de l'emprise du projet -----------------------------------------------
from epa import perimetre as PER  # noqa: E402
from epa import projet as PJ  # noqa: E402

with st.expander("Proposer le périmètre à partir de l'emprise du projet", expanded=st.session_state.get("territoire") is None):
    emp = st.session_state.get("emprise")
    if emp is None or emp.empty:
        up_e = st.file_uploader("Emprise du projet (GeoJSON, shapefile zippé, GeoPackage, KML)",
                                type=["geojson", "json", "zip", "gpkg", "kml"], key="emprise_terr")
        if up_e is not None:
            try:
                emp = PJ.lire_emprise(up_e.name, up_e.getvalue())
                st.session_state["emprise"] = emp
                st.session_state["emprise_fictive"] = False
            except Exception as e:  # format non reconnu : message clair
                st.error(f"Emprise illisible : {e}")
                emp = None
    if emp is not None and not emp.empty:
        st.caption(f"Emprise : {PJ.surface_ha(emp):.1f} ha".replace(".", ",") + (" (fictive, démonstration)" if st.session_state.get("emprise_fictive") else ""))
        if st.button("Proposer le périmètre", type="primary", icon=":material/auto_awesome:"):
            with st.spinner("Recherche des communes et intercommunalités concernées…"):
                try:
                    prop = PER.proposer(emp)
                    t_new = T.build_territoire(prop["epcis"], prop["communes_hors_epci"], [], None)
                except DataSourceError as e:
                    st.error(str(e))
                    st.stop()
            st.session_state["territoire"] = t_new
            st.session_state["communes_emprise"] = prop["communes_emprise"]
            st.session_state["territoire_cfg"] = cfg = {
                "region": t_new.code_region, "tous_deps": len(t_new.codes_departements) > 1, "departements": t_new.codes_departements,
                "epcis": [e["code"] for e in prop["epcis"]], "communes_ajoutees": prop["communes_hors_epci"], "communes_retirees": [],
                "nom": t_new.nom}
            st.rerun()

c1, c2 = st.columns([1, 2])
with c1:
    reg_labels = {r["code"]: r["nom"] for _, r in regions.iterrows()}
    reg_codes = list(reg_labels)
    reg = st.selectbox("Région", reg_codes, format_func=lambda c: reg_labels[c],
                       index=reg_codes.index(cfg["region"]) if cfg.get("region") in reg_codes else None,
                       placeholder="Choisir une région")
    tous = st.toggle("Autoriser des départements d'autres régions", value=cfg.get("tous_deps", False),
                     help="Utile pour un territoire d'étude à cheval sur deux régions.")
with c2:
    dep_df = deps if (tous or reg is None) else deps[deps["codeRegion"] == reg]
    dep_labels = {r["code"]: f"{r['code']} – {r['nom']}" for _, r in dep_df.iterrows()}
    default_deps = [d for d in cfg.get("departements", []) if d in dep_labels]
    sel_deps = st.multiselect("Département(s)", list(dep_labels), default=default_deps, format_func=lambda c: dep_labels[c],
                              placeholder="Choisir un ou plusieurs départements")

epci_opts: dict[str, str] = {}
for d in sel_deps:
    try:
        for _, r in T.list_epcis_departement(d).iterrows():
            epci_opts[r["code"]] = r["nom"]
    except DataSourceError as e:
        st.warning(f"EPCI du département {d} indisponibles : {e}")

default_epcis = [e for e in cfg.get("epcis", []) if e in epci_opts]
sel_epcis = st.multiselect("Intercommunalité(s) – EPCI à fiscalité propre", list(epci_opts), default=default_epcis,
                           format_func=lambda c: f"{epci_opts[c]} ({c})", placeholder="Choisir une ou plusieurs communautés de communes / agglomérations")

with st.expander("Ajuster la liste des communes (facultatif)"):
    q = st.text_input("Rechercher une commune à ajouter", placeholder="Nom de commune")
    ajout = list(cfg.get("communes_ajoutees", []))
    if q and len(q) >= 2:
        try:
            res = T.search_communes(q)
            if not res.empty:
                opts = {r["code"]: f"{r['nom']} ({r['code']}, dép. {r.get('codeDepartement', '')})" for _, r in res.iterrows()}
                choix = st.multiselect("Résultats", list(opts), format_func=lambda c: opts[c], placeholder="Choisir")
                if st.button("Ajouter ces communes") and choix:
                    ajout = sorted(set(ajout) | set(choix))
                    cfg["communes_ajoutees"] = ajout
        except DataSourceError as e:
            st.warning(str(e))
    if ajout:
        st.write("Communes ajoutées : " + ", ".join(ajout))
        if st.button("Vider les communes ajoutées"):
            cfg["communes_ajoutees"] = []
            ajout = []
    t_prev = st.session_state.get("territoire")
    retirees = cfg.get("communes_retirees", [])
    if t_prev is not None:
        all_c = {r["code"]: f"{r['nom']} ({r['code']})" for _, r in t_prev.communes.iterrows()}
        all_c.update({c: c for c in retirees if c not in all_c})
        retirees = st.multiselect("Communes à retirer du territoire", list(all_c), default=[c for c in retirees if c in all_c],
                                  format_func=lambda c: all_c[c], placeholder="Choisir")

nom = st.text_input("Nom du territoire d'étude", value=cfg.get("nom") or (" + ".join(epci_opts[e] for e in sel_epcis) if sel_epcis else ""))

if st.button("Valider le territoire d'étude", type="primary", disabled=not (sel_epcis or cfg.get("communes_ajoutees"))):
    with st.spinner("Chargement des contours communaux…"):
        try:
            t = T.build_territoire([{"code": e, "nom": epci_opts[e]} for e in sel_epcis], cfg.get("communes_ajoutees", []),
                                   retirees, nom or None)
        except DataSourceError as e:
            st.error(str(e))
            st.stop()
    st.session_state["territoire"] = t
    st.session_state["territoire_cfg"] = {
        "region": reg, "tous_deps": tous, "departements": sel_deps, "epcis": sel_epcis,
        "communes_ajoutees": cfg.get("communes_ajoutees", []), "communes_retirees": retirees, "nom": nom,
    }
    st.success(f"Territoire « {t.nom} » enregistré : {len(t.communes)} communes.")

t = st.session_state.get("territoire")
if t is None:
    st.stop()

st.divider()
r = t.resume()
kpis([
    ("Communes", fnum(r["Nombre de communes"]), ", ".join(e["nom"] for e in t.epcis)[:80]),
    ("Superficie", fnum(r["Surface (ha)"]) + " ha", f"{fnum(r['Surface (ha)'] / 100)} km²"),
    ("Population", fnum(r["Population (INSEE, via API Découpage administratif)"]), "habitants"),
    ("Département(s)", r["Départements"], f"Région {t.code_region or '—'}"),
])
texte_auto(texte_territoire(r))

c1, c2 = st.columns([3, 2])
with c1:
    m = cartes.base_map(t.bounds)
    cartes.add_territoire(m, t.communes)
    cartes.add_emprise(m, st.session_state.get("emprise"))
    cartes.finalize(m)
    st_folium(m, height=520, use_container_width=True, returned_objects=[], key="map_territoire")
    enregistrer("geo")
    source("API Découpage administratif (geo.api.gouv.fr) ; fonds IGN Géoplateforme / OpenStreetMap.")
with c2:
    tab = t.communes[["code", "nom", "codeEpci", "population", "surface_ha"]].copy()
    tab = tab.rename(columns={"code": "Code INSEE", "nom": "Commune", "codeEpci": "EPCI", "population": "Population", "surface_ha": "Surface (ha)"})
    st.dataframe(tab, hide_index=True, width="stretch", height=520,
                 column_config={"Surface (ha)": st.column_config.NumberColumn(format="%.0f"), "Population": st.column_config.NumberColumn(format="%d")})
    st.download_button("Télécharger la liste (CSV)", tab.to_csv(index=False, sep=";").encode("utf-8-sig"), "communes_territoire.csv", "text/csv")


# --- Indicateurs recalculés en direct et justification du périmètre ----------------------------------------
from epa import agreste  # noqa: E402
from epa.ui import tuile_comparee, tuiles, phrase  # noqa: E402

codes_live = sorted((set(t.codes_communes) | set(cfg.get("communes_ajoutees", []))) - set(retirees or []))
st.markdown("#### Le périmètre en chiffres")
st.caption("Recalculé à chaque ajout ou retrait de commune, avant même de valider.")
try:
    ra_c = agreste.ra2020("commune")
    s_live = agreste.synthese(ra_c[ra_c["codgeo"].astype(str).isin(codes_live)], "live")
    tuiles([
        tuile_comparee("Communes", {"Périmètre": float(len(codes_live))}, "", 0),
        tuile_comparee("Exploitations en 2020", {"Périmètre": s_live["Exploitations 2020"]}, "", 0),
        tuile_comparee("SAU en 2020", {"Périmètre": s_live["SAU 2020 (ha)"]}, "ha", 0),
        tuile_comparee("Exploitations, évolution 2010-2020", {"Périmètre": s_live["Évolution exploitations 2010-2020 (%)"]}, "%", 1, signe=True),
    ])
    sources("ra2020")
except DataSourceError as e:
    st.warning(f"Recensement agricole indisponible pour le moment : {e}")
try:
    from epa.otex import otex_communes
    otx = otex_communes()
except DataSourceError:
    otx = None
phrase(PER.texte_justification(t.communes[t.communes["code"].isin(codes_live)], t.epcis,
                               st.session_state.get("communes_emprise", []),
                               ajoutees=cfg.get("communes_ajoutees"), retirees=retirees, otex=otx))

st.page_link("app_pages/p02_projet.py", label="Étape suivante : décrire le projet et son emprise", icon=":material/arrow_forward:")
