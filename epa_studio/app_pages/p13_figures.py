import re

import streamlit as st

from epa import agreste, figures, rpg
from epa import territoire as T
from epa.chiffres_cles import departement_reference
from epa.config import RPG_LAYERS
from epa.http import DataSourceError
from epa.projet import site_courant
from epa.ui import bouton_png, entete, manquant, require_territoire, resultat, sources, stocker

entete("Étape 4 sur 4 : livrables", "Figures du rapport",
       "Les cartes et graphiques types d'une étude préalable agricole, générés depuis les données publiques. "
       "Chaque figure s'exporte en PNG 300 dpi, avec son titre et sa source.")
require_territoire()
t = st.session_state["territoire"]
emprise = st.session_state.get("emprise")
a_emprise = emprise is not None and not emprise.empty

# Commune du site : déduite de l'emprise, sinon choisie ici.
noms = dict(zip(t.communes["code"], t.communes["nom"]))
site = site_courant(st.session_state, t.communes)
if not a_emprise:
    codes = sorted(noms, key=lambda c: noms[c])
    site = st.selectbox("Commune du site", codes, index=codes.index(site) if site in codes else None,
                        format_func=lambda c: f"{noms[c]} ({c})", placeholder="Choisir la commune du projet",
                        help="Renseignez l'emprise du projet (page Projet et emprise) pour que la commune soit déduite automatiquement.")
    st.session_state["site_commune"] = site
code_dep = departement_reference(t.communes, site)

# Les figures dépendent du site et de l'emprise : on les invalide quand ces entrées changent.
from epa.projet import emprise_to_geojson  # noqa: E402

empreinte = (site, emprise_to_geojson(emprise) if a_emprise else None)
if st.session_state.get("fig_empreinte") != empreinte:
    for k in [k for k in st.session_state if str(k).startswith("res::fig::")]:
        del st.session_state[k]
    st.session_state.pop("fig_echecs", None)
    st.session_state["fig_empreinte"] = empreinte


def bloc(cle: str, titre: str, description: str, generer, src: tuple[str, ...], requis: str | None = None):
    from epa import sources as S

    st.markdown(f"#### {titre}")
    st.caption(description)
    if requis:
        attendu = "IGN / ASP, registre parcellaire graphique" if src and src[0].startswith("rpg:") else "; ".join(S.citer(c) for c in src)
        manquant(titre, attendu, requis)
        st.divider()
        return
    png = resultat(f"fig::{cle}")
    echecs = st.session_state.setdefault("fig_echecs", set())
    if png is None:
        # en démonstration, les données sont en cache : la figure est produite directement (une seule tentative)
        auto = st.session_state.get("mode_demo") and cle not in echecs
        if auto or st.button("Générer la figure", key=f"gen_{cle}"):
            with st.spinner("Génération de la figure…"):
                try:
                    png = generer()
                except DataSourceError as e:
                    st.error(f"Un service de données n'a pas répondu : {e}. Réessayez dans un instant.")
                    png = None
            if png is None:
                echecs.add(cle)
                st.warning("La figure n'a pas pu être produite : la donnée nécessaire n'est pas disponible.")
            else:
                stocker(f"fig::{cle}", png)
    if png:
        st.image(png, width="stretch")
        bouton_png(png, cle)
        for c in src:
            S.enregistrer(c)
    st.divider()


# 1. Localisation
def g_loc():
    dep = T.communes_departement_geo(code_dep)
    nom_dep = T.list_departements().set_index("code")["nom"].get(code_dep, code_dep)
    com = t.communes[t.communes["code"] == site]
    return figures.localisation_3_echelles(dep, t.communes, com, emprise if a_emprise else None,
                                           (nom_dep, t.nom, noms.get(site, site)))


bloc("localisation", "Localisation à trois échelles", "Département, périmètre d'étude et commune du site sur photographie aérienne.",
     g_loc, ("geo", "ortho"), None if site else "Choisissez la commune du site ou renseignez l'emprise du projet.")


# 2. Vignettes RPG
annees_dispo = {int(re.match(r"\d{4}", k).group()): v for k, v in RPG_LAYERS.items()}
choix = st.session_state.setdefault("fig_rpg_annees", sorted(annees_dispo)[-5:])


def g_rpg():
    return figures.vignettes_rpg(emprise, {a: rpg.rpg_emprise(annees_dispo[a], emprise) for a in sorted(choix)})


if a_emprise:
    st.session_state["fig_rpg_annees"] = st.multiselect("Millésimes du RPG", sorted(annees_dispo, reverse=True), default=choix, placeholder="Choisir")
    choix = st.session_state["fig_rpg_annees"]
bloc("rpg_" + "_".join(map(str, sorted(choix))), "Cultures déclarées sur le site, année par année", "Parcelles du RPG intersectant l'emprise, sur photographie aérienne.",
     g_rpg, tuple(f"rpg:{a}" for a in sorted(choix)) + ("ortho",),
     None if a_emprise else "Renseignez l'emprise du projet (page Projet et emprise) pour produire cette figure.")

# 3. CLC
bloc("clc", "Occupation du sol (Corine Land Cover 2018)", "Couche CLC 2018 sur le périmètre d'étude, avec la légende officielle.",
     lambda: figures.carte_wms_perimetre(t.communes, "LANDCOVER.CLC18_FR", "Occupation du sol du périmètre d'étude",
                                         "Union européenne – Copernicus / SDES, CORINE Land Cover 2018 ; IGN, Géoplateforme",
                                         "Corine Land Cover 2018, nomenclature en 44 postes"), ("clc2018", "plan_ign"))

# 4. Sols
bloc("sols", "Sols dominants", "Carte harmonisée des sols dominants (Référentiels régionaux pédologiques, 1/250 000).",
     lambda: figures.carte_wms_perimetre(t.communes, "INRAE_CARTE-SOLS", "Sols dominants du périmètre d'étude",
                                         "INRAE – Gis Sol, sols dominants de France métropolitaine ; IGN, Géoplateforme",
                                         "Référentiels régionaux pédologiques au 1/250 000"), ("sols", "plan_ign"))
bloc("ru", "Réserve utile en eau des sols", "Classes de réserve utile de la Base de données géographique des sols de "
     "France (Gis Sol, échelle 1/1 000 000 : à lire comme un ordre de grandeur, pas à la parcelle).",
     lambda: figures.carte_wms_perimetre(t.communes, "inra_bdgsf:bdgsf_classe_ru", "Réserve utile en eau des sols du périmètre",
                                         "INRAE – Gis Sol, réserve utile en eau issue de la BDGSF (1/1 000 000) ; IGN, Géoplateforme",
                                         "Base de données géographique des sols de France, échelle 1/1 000 000",
                                         url=figures.GISSOL_WMS), ("ru_bdgsf", "plan_ign"))
st.markdown("#### Profondeur des sols")
manquant("Profondeur des sols", "INRAE – Gis Sol",
         "Aucune couche de profondeur des sols n'est publiée par les services cartographiques du Gis Sol (geodata.inrae.fr, "
         "vérifié dans ses GetCapabilities) ni par la Géoplateforme. Joignez vos propres données si besoin.")
st.divider()

# 5. OTEX
def g_otex():
    from epa.otex import otex_communes
    return figures.carte_otex(t.communes, otex_communes())


bloc("otex", "Orientation technico-économique des communes (OTEX)",
     "OTEX dominante de chaque commune du périmètre, recensement agricole 2020, en 12 postes.", g_otex, ("otex",))
with st.expander("Remplacer par un export Cartostat ou DISAR"):
    up = st.file_uploader("Export OTEX par commune (xlsx ou csv)", type=["xlsx", "xls", "csv"], key="otex_up")
    if up is not None:
        try:
            df = agreste.lire_fichier_utilisateur(up.name, up.getvalue())
            col = st.selectbox("Colonne contenant l'OTEX", [c for c in df.columns if c != "codgeo"])
            if st.button("Générer depuis ce fichier", key="gen_otex_up"):
                stocker("fig::otex", figures.carte_otex(t.communes, df.rename(columns={col: "otex"}),
                                                        source="Agreste, RA 2020, export Cartostat / DISAR importé"))
                from epa import sources as S
                S.enregistrer("cartostat")
                st.rerun()
        except DataSourceError as e:
            st.error(str(e))
st.divider()

# 6. Évolutions
cc = resultat("chiffres_cles")
st.markdown("#### Évolution 2010-2020 comparée")
if cc:
    nom_dep = T.list_departements().set_index("code")["nom"].get(cc["dep"], cc["dep"])
    noms_cc = ["Périmètre d'étude", nom_dep] + (["Région"] if len(cc["comp"]) == 4 else []) + ["France"]
    if len(cc["comp"]) == 4:
        noms_cc[2] = T.list_regions().set_index("code")["nom"].get(cc.get("reg"), "Région")
    png = figures.evolutions_comparees(cc["comp"].assign(Territoire=noms_cc))
    st.image(png, width="stretch")
    bouton_png(png, "evolutions_2010_2020")
    sources("ra2020")
else:
    st.page_link("app_pages/p04b_chiffres_cles.py", label="Calculer d'abord les chiffres clés", icon=":material/arrow_forward:")
