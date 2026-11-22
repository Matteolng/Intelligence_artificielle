import streamlit as st

from epa.config import APP_NAME, APP_VERSION
from epa.http import cache_size_mb, clear_cache
from epa.ui import card, hero

hero(
    f"{APP_NAME}",
    "Construisez l'état initial de l'économie agricole d'un territoire en quelques minutes : cartes, tableaux, statistiques "
    "et rapport Word structuré selon l'article D. 112-1-19 du code rural. Pensé pour les bureaux d'études et les projets agrivoltaïques.",
    "Études préalables agricoles · Compensation collective · Agrivoltaïsme",
)

st.markdown("#### Le parcours")
c = st.columns(4)
c[0].markdown(card("1 · Cadrage", "Choisissez la région, le ou les départements, les EPCI et ajustez les communes. "
                                  "Importez ou dessinez l'emprise du projet."), unsafe_allow_html=True)
c[1].markdown(card("2 · État initial", "Assolement RPG, structures RA 2020, filières amont/aval (SIRENE), SIQO et bio, "
                                       "prix du foncier (DVF), atlas des zonages."), unsafe_allow_html=True)
c[2].markdown(card("3 · Impacts", "Cultures concernées par l'emprise, contrôle des critères agrivoltaïques, mesures ERC, "
                                  "calcul paramétrable de la compensation collective."), unsafe_allow_html=True)
c[3].markdown(card("4 · Livrables", "Rapport Word pré-rédigé avec cartes et tableaux, export Excel de toutes les données, "
                                    "sauvegarde du projet."), unsafe_allow_html=True)

st.write("")
st.page_link("app_pages/p01_territoire.py", label="Commencer : définir le territoire d'étude", icon="➡️")

st.markdown("#### Données mobilisées (toutes publiques et ouvertes)")
st.markdown(
    """
| Thème | Source | Échelle |
|---|---|---|
| Limites administratives, population | API Découpage administratif (geo.api.gouv.fr) | Commune, EPCI |
| Occupation agricole, cultures, bio, prairies | Registre parcellaire graphique 2015-2025 (IGN / ASP, Géoplateforme) | Parcelle |
| Exploitations, SAU, évolutions 2010-2020 | Recensement agricole 2020 (Agreste) via l'Observatoire des territoires | Commune → région |
| Indicateurs RA 2020 détaillés (OTEX, PBS, UGB, UTA…) | Import des exports Cartostat / DISAR (Agreste) | Commune |
| Amont, transformation, commercialisation, coopératives, CUMA | SIRENE via l'API Recherche d'entreprises | Établissement |
| Agriculture biologique | Annuaire de l'Agence Bio | Opérateur |
| AOC/AOP, IGP/IG | INAO (data.gouv.fr) | Commune |
| Prix des terres agricoles | DVF (DGFiP) via l'API Données foncières du Cerema | Mutation |
| Zonages environnementaux, urbanisme, sols, potentiel solaire, ZAER | Géoplateforme IGN (WMS) | Couches cartographiques |
"""
)

with st.expander("Bon à savoir"):
    st.markdown(
        """
- Les données sont téléchargées à la demande puis **mises en cache** sur le disque (`~/.cache/epa_studio`) : les
  calculs suivants sont quasi instantanés.
- Chaque tableau indique sa **source** ; les synthèses rédigées automatiquement ne contiennent que des valeurs calculées
  par l'outil et doivent être relues.
- Le **référentiel réglementaire** précise, pour chaque règle, si elle a été vérifiée sur un texte officiel ou sur une
  source secondaire. Le texte consolidé sur Légifrance fait foi.
- L'outil ne remplace pas les enquêtes de terrain, les entretiens avec les exploitants et les filières, ni l'expertise
  du chargé d'études.
"""
    )

with st.expander("Maintenance du cache"):
    st.write(f"Taille actuelle du cache : **{cache_size_mb():.1f} Mo**")
    if st.button("Vider le cache disque"):
        n = clear_cache()
        st.success(f"{n} fichiers supprimés.")

st.caption(f"{APP_NAME} v{APP_VERSION} – logiciel libre d'aide à la décision. Les résultats n'engagent pas les services instructeurs.")
