import streamlit as st

from epa.sources import enregistrer
from streamlit_folium import st_folium

from epa import cartes, territoire as T
from epa.analyse import fnum
from epa.http import DataSourceError
from epa.ui import hero, kpis, source, texte_auto
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
                choix = st.multiselect("Résultats", list(opts), format_func=lambda c: opts[c])
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
                                  format_func=lambda c: all_c[c])

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

st.page_link("app_pages/p02_projet.py", label="Étape suivante : décrire le projet et son emprise", icon=":material/arrow_forward:")
