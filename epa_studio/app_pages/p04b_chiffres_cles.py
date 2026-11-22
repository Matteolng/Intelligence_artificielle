import streamlit as st

from epa import agreste, figures
from epa.chiffres_cles import LIGNE_FRANCE, comparaison, departement_reference
from epa.gabarits import phrase_evolution
from epa.http import DataSourceError
from epa.projet import site_courant
from epa.territoire import list_departements
from epa.ui import bouton_png, entete, manquant, phrase, require_territoire, resultat, sources, stocker, tuile_comparee, tuiles

entete("Étape 2 sur 4 : état initial", "Chiffres clés de l'agriculture",
       "Le périmètre d'étude comparé à son département et à la France, d'après les recensements agricoles 2010 et 2020.")
require_territoire()
t = st.session_state["territoire"]

code_dep = departement_reference(t.communes, site_courant(st.session_state, t.communes))

res = resultat("chiffres_cles")
if res is None or res.get("dep") != code_dep:
    with st.spinner("Lecture des recensements agricoles (Observatoire des territoires)…"):
        try:
            dc, dd = agreste.ra2020("commune"), agreste.ra2020("departement")
        except DataSourceError as e:
            manquant("Recensement agricole 2020", "Agreste via l'Observatoire des territoires",
                     f"Le service n'a pas répondu ({e}). Réessayez plus tard ou ouvrez la démonstration, dont les données sont en cache.")
            st.stop()
    comp = comparaison(dc, dd, t.codes_communes, code_dep, "Périmètre d'étude")
    res = {"dep": code_dep, "comp": comp}
    stocker("chiffres_cles", res)

comp = res["comp"]
nom_dep = list_departements().set_index("code")["nom"].get(code_dep, code_dep)
p, d, f = (comp.iloc[i].to_dict() for i in range(3))
ref = {"Périmètre": None, nom_dep: None, "France": None}


def vals(col):
    return dict(zip(ref, (p.get(col), d.get(col), f.get(col))))


tuiles([
    tuile_comparee("Exploitations agricoles en 2020", vals("Exploitations 2020"), "", 0),
    tuile_comparee("Évolution des exploitations 2010-2020", vals("Évolution exploitations 2010-2020 (%)"), "%", 1, signe=True),
    tuile_comparee("Surface agricole utilisée en 2020", vals("SAU 2020 (ha)"), "ha", 0),
    tuile_comparee("Évolution de la SAU 2010-2020", vals("Évolution SAU 2010-2020 (%)"), "%", 1, signe=True),
])
st.write("")
tuiles([
    tuile_comparee("SAU moyenne par exploitation", vals("SAU moyenne par exploitation (ha)"), "ha", 1),
    tuile_comparee("Communes sans donnée diffusée", {"Périmètre": p.get("Communes sans donnée (secret ou absence)")}, "", 0,
                   sous=f"sur {len(t.communes)} communes (secret statistique ou absence)"),
    "", "",
])

phrase(phrase_evolution("Le nombre d'exploitations", False, p.get("Évolution exploitations 2010-2020 (%)"),
                        d.get("Évolution exploitations 2010-2020 (%)"), f.get("Évolution exploitations 2010-2020 (%)")))
phrase(phrase_evolution("La surface agricole utilisée", True, p.get("Évolution SAU 2010-2020 (%)"),
                        d.get("Évolution SAU 2010-2020 (%)"), f.get("Évolution SAU 2010-2020 (%)")))

st.write("")
png = figures.evolutions_comparees(comp.assign(Territoire=["Périmètre d'étude", nom_dep, "France"]))
if png:
    st.image(png, width="stretch")
    bouton_png(png, "evolutions_2010_2020")

with st.expander("Tableau détaillé et méthode"):
    st.dataframe(comp, hide_index=True, column_config={c: st.column_config.NumberColumn(format="%.1f") for c in comp.columns if c != "Territoire"})
    st.caption(f"Périmètre : somme des communes ; évolutions recalculées à partir des valeurs 2010 reconstituées. Département de "
               f"référence : {nom_dep}, celui de la commune du site (ou, à défaut, le plus étendu dans le périmètre). "
               f"« {LIGNE_FRANCE} » : somme des départements publiés. Les données sont localisées au siège de l'exploitation.")
    st.download_button("Télécharger le tableau (CSV)", comp.to_csv(index=False, sep=";").encode("utf-8-sig"), "chiffres_cles.csv", "text/csv")
sources("ra2020")
