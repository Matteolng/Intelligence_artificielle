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


def bloc(cle: str, titre: str, description: str, generer, src: tuple[str, ...], requis: str | None = None):
    st.markdown(f"#### {titre}")
    st.caption(description)
    if requis:
        manquant(titre, ", ".join(src), requis)
        st.divider()
        return
    png = resultat(f"fig::{cle}")
    if png is None:
        if st.button("Générer la figure", key=f"gen_{cle}"):
            with st.spinner("Génération de la figure…"):
                try:
                    png = generer()
                except DataSourceError as e:
                    st.error(f"Un service de données n'a pas répondu : {e}. Réessayez dans un instant.")
                    png = None
            if png is None:
                st.warning("La figure n'a pas pu être produite : la donnée nécessaire n'est pas disponible.")
            else:
                stocker(f"fig::{cle}", png)
    if png:
        st.image(png, width="stretch")
        bouton_png(png, cle)
        from epa import sources as S
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
    st.session_state["fig_rpg_annees"] = st.multiselect("Millésimes du RPG", sorted(annees_dispo, reverse=True), default=choix)
    choix = st.session_state["fig_rpg_annees"]
bloc("rpg_annees", "Cultures déclarées sur le site, année par année", "Parcelles du RPG intersectant l'emprise, sur photographie aérienne.",
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
st.markdown("#### Réserve utile et profondeur des sols")
manquant("Réserve utile et profondeur des sols", "INRAE / Gis Sol",
         "Ces couches ne sont pas diffusées par le service WMS de la Géoplateforme interrogé par l'application "
         "(vérifié dans ses GetCapabilities). Joignez vos propres cartes au rapport.")
st.divider()

# 5. OTEX
st.markdown("#### Orientation technico-économique des communes (OTEX)")
st.caption("Importez un export Cartostat ou DISAR (Agreste, RA 2020) contenant le code commune et l'OTEX.")
up = st.file_uploader("Export OTEX par commune (xlsx ou csv)", type=["xlsx", "xls", "csv"], key="otex_up")
if up is not None:
    try:
        df = agreste.lire_fichier_utilisateur(up.name, up.getvalue())
        col = st.selectbox("Colonne contenant l'OTEX", [c for c in df.columns if c != "codgeo"])
        if st.button("Générer la figure", key="gen_otex"):
            stocker("fig::otex", figures.carte_otex(t.communes, df.rename(columns={col: "otex"})))
    except DataSourceError as e:
        st.error(str(e))
png = resultat("fig::otex")
if png:
    st.image(png, width="stretch")
    bouton_png(png, "otex")
    from epa import sources as S
    S.enregistrer("cartostat")
elif up is None:
    manquant("OTEX par commune", "Agreste, RA 2020 (Cartostat / DISAR)",
             "L'Observatoire des territoires ne diffuse pas l'OTEX communale : importez l'export ci-dessus.")
st.divider()

# 6. Évolutions
cc = resultat("chiffres_cles")
st.markdown("#### Évolution 2010-2020 comparée")
if cc:
    nom_dep = T.list_departements().set_index("code")["nom"].get(cc["dep"], cc["dep"])
    png = figures.evolutions_comparees(cc["comp"].assign(Territoire=["Périmètre d'étude", nom_dep, "France"]))
    st.image(png, width="stretch")
    bouton_png(png, "evolutions_2010_2020")
    sources("ra2020")
else:
    st.page_link("app_pages/p04b_chiffres_cles.py", label="Calculer d'abord les chiffres clés", icon=":material/arrow_forward:")
