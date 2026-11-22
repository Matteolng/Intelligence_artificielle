import pandas as pd
import streamlit as st

from epa.reglementation import ADMIN, OFFICIEL, REFERENTIEL, SECONDAIRE, SOURCES_DONNEES
from epa.ui import badge, hero

hero("Cadre réglementaire et sources", "Textes applicables à l'étude préalable agricole, à la compensation collective et à "
     "l'agrivoltaïsme, avec le statut de vérification de chaque élément et les sources des données.", "Étape 4 sur 4 : livrables")

st.markdown(
    f"{badge(OFFICIEL)} lu sur une source officielle &nbsp; {badge(ADMIN)} guide ou page d'un service de l'État &nbsp; "
    f"{badge(SECONDAIRE)} article, cabinet d'avocats ou presse spécialisée",
    unsafe_allow_html=True,
)
st.caption("Référentiel établi en novembre 2026. Le texte consolidé sur Légifrance fait foi ; vérifiez toujours la version en vigueur "
           "et la doctrine du département concerné.")

themes = list(dict.fromkeys(i.theme for i in REFERENTIEL))
for th in themes:
    st.markdown(f"### {th}")
    for it in [i for i in REFERENTIEL if i.theme == th]:
        with st.expander(it.titre):
            st.markdown(badge(it.statut), unsafe_allow_html=True)
            st.markdown(it.contenu.replace("\n", "  \n"))
            st.markdown("**Sources**")
            for lbl, url in it.sources:
                st.markdown(f"- [{lbl}]({url})")

st.markdown("### Bibliographie des sources interrogées")
from epa.sources import bibliographie  # noqa: E402

refs = bibliographie(st.session_state.get("sources_utilisees", {}))
if refs:
    st.markdown("\n".join(f"- {r}" for r in refs))
    st.download_button("Télécharger la bibliographie (texte)", "\n".join(refs).encode("utf-8"), "bibliographie.txt", "text/plain")
else:
    st.caption("Aucune source interrogée pour l'instant : la bibliographie se construit au fil des pages consultées.")

st.markdown("### Sources des données")
st.dataframe(pd.DataFrame(SOURCES_DONNEES, columns=["Donnée", "Producteur / diffuseur", "Accès", "Licence"]), hide_index=True,
             column_config={"Accès": st.column_config.LinkColumn()})
