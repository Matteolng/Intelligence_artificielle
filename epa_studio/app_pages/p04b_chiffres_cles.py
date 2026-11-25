import streamlit as st

from epa import agreste, figures
from epa.branding import branding_courant
from epa.chiffres_cles import LIGNE_FRANCE, comparaison, departement_reference
from epa.gabarits import phrase_evolution
from epa.http import DataSourceError
from epa.projet import site_courant
from epa.sources import enregistrer
from epa.territoire import list_departements, list_regions
from epa.theme import anneaux, barres, ornement, photo_territoire
from epa.ui import (bouton_png, entete_nuit, fmt_val, manquant, phrase, require_territoire, resultat, stocker,
                    tuile_comparee, tuiles)

require_territoire()
t = st.session_state["territoire"]
deps = list_departements().set_index("code")
code_dep = departement_reference(t.communes, site_courant(st.session_state, t.communes))
code_reg = str(deps["codeRegion"].get(code_dep, t.code_region or ""))
nom_dep = deps["nom"].get(code_dep, code_dep)
nom_reg = list_regions().set_index("code")["nom"].get(code_reg, code_reg)

with st.spinner("Préparation de la photographie aérienne du territoire…"):
    photo = photo_territoire(t.communes)
entete_nuit("Étape 2 sur 4, état initial", "Chiffres clés", "de l'agriculture",
            f"{t.nom} : {len(t.communes)} communes, comparées à leur département ({nom_dep}), à leur région ({nom_reg}) "
            "et à la France, d'après les recensements agricoles 2010 et 2020.", photo=photo)

res = resultat("chiffres_cles")
if res is None or res.get("dep") != code_dep or res.get("reg") != code_reg:
    with st.spinner("Lecture des recensements agricoles (Observatoire des territoires)…"):
        try:
            dc, dd, dr = agreste.ra2020("commune"), agreste.ra2020("departement"), agreste.ra2020("region")
        except DataSourceError as e:
            manquant("Recensement agricole 2020", "Agreste via l'Observatoire des territoires",
                     f"Le service n'a pas répondu ({e}). Réessayez dans un instant.")
            st.stop()
    comp = comparaison(dc, dd, t.codes_communes, code_dep, "Périmètre d'étude", df_reg=dr, code_reg=code_reg)
    res = {"dep": code_dep, "reg": code_reg, "comp": comp}
    stocker("chiffres_cles", res)

comp = res["comp"]
p, d, r, f = (comp.iloc[i].to_dict() for i in range(4))
noms = [t.nom, nom_dep, nom_reg, "Somme des départements"]
labels = ["Périmètre", "Département", "Région", "France"]
EXP, SAU = "Évolution exploitations 2010-2020 (%)", "Évolution SAU 2010-2020 (%)"

c1, c2 = st.columns([1, 1])
indic = c1.segmented_control("Indicateur", ["Exploitations", "Surface agricole utilisée"], default="Exploitations",
                             label_visibility="collapsed") or "Exploitations"
sel = c2.segmented_control("Échelle mise en avant", labels, default="Périmètre", label_visibility="collapsed") or "Périmètre"
exp = indic == "Exploitations"
col_v, col_e = ("Exploitations 2020", EXP) if exp else ("SAU 2020 (ha)", SAU)
unite = "" if exp else "ha"
echelles = [{"label": labels[i], "nom": noms[i], "valeur": fmt_val(row.get(col_v), unite, 0),
             "evol": fmt_val(row.get(col_e), "%", 1, signe=True) + " depuis 2010"} for i, row in enumerate((p, d, r, f))]
txt = phrase_evolution("Le nombre d'exploitations" if exp else "La surface agricole utilisée", not exp,
                       p.get(col_e), d.get(col_e), f.get(col_e), v_reg=r.get(col_e), avec_region=True)
st.markdown(
    f'<div class="epa-nuit"><h2 style="margin:0 0 1.4rem">{"Exploitations" if exp else "Surface agricole utilisée"}, '
    f'<em>quatre échelles</em></h2>{anneaux(echelles, labels.index(sel))}'
    f'<div class="epa-phrase">{txt}<small>Phrase générée à partir des chiffres calculés, à relire.</small></div>'
    f'<div class="epa-source">Source : Agreste, recensements agricoles 2010 et 2020, via l\'Observatoire des territoires (ANCT). '
    f'France : somme des départements. Données localisées au siège de l\'exploitation.</div></div>',
    unsafe_allow_html=True)
enregistrer("ra2020")

st.markdown(ornement(), unsafe_allow_html=True)
st.markdown("### Évolution 2010-2020")
cb1, cb2 = st.columns(2, gap="large")
with cb1:
    st.markdown("**Nombre d'exploitations**")
    st.markdown(barres([{"nom": noms[i], "valeur": row.get(EXP)} for i, row in enumerate((p, d, r, f))],
                       branding_courant().couleur), unsafe_allow_html=True)
with cb2:
    st.markdown("**Surface agricole utilisée**")
    st.markdown(barres([{"nom": noms[i], "valeur": row.get(SAU)} for i, row in enumerate((p, d, r, f))],
                       branding_courant().couleur), unsafe_allow_html=True)
phrase(phrase_evolution("La surface agricole utilisée" if exp else "Le nombre d'exploitations", exp,
                        p.get(SAU if exp else EXP), d.get(SAU if exp else EXP), f.get(SAU if exp else EXP),
                        v_reg=r.get(SAU if exp else EXP), avec_region=True))

st.write("")
tuiles([
    tuile_comparee("SAU moyenne par exploitation", dict(zip(labels, (row.get("SAU moyenne par exploitation (ha)") for row in (p, d, r, f)))), "ha", 1),
    tuile_comparee("Communes non diffusées", {"Périmètre": p.get("Communes sans donnée (secret ou absence)")}, "", 0,
                   sous=f"sur {len(t.communes)} communes (secret statistique ou absence)"),
    "",
])

png = figures.evolutions_comparees(comp.assign(Territoire=["Périmètre d'étude", nom_dep, nom_reg, "France"]))
with st.expander("Figure pour le rapport, tableau détaillé et méthode"):
    if png:
        st.image(png, width="stretch")
        bouton_png(png, "evolutions_2010_2020")
    st.dataframe(comp, hide_index=True, column_config={c: st.column_config.NumberColumn(format="%.1f") for c in comp.columns if c != "Territoire"})
    st.caption(f"Périmètre : somme des communes ; évolutions recalculées à partir des valeurs 2010 reconstituées. Département de "
               f"référence : {nom_dep}, celui de la commune du site (ou, à défaut, le plus étendu dans le périmètre) ; région : {nom_reg}. "
               f"« {LIGNE_FRANCE} » : somme des départements publiés.")
    st.download_button("Télécharger le tableau (CSV)", comp.to_csv(index=False, sep=";").encode("utf-8-sig"), "chiffres_cles.csv", "text/csv")
