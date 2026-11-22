import streamlit as st

from epa import compensation as C
from epa.analyse import fnum, texte_compensation
from epa.ui import hero, kpis, require_territoire, resultat, source, stocker, texte_auto

hero("Compensation collective agricole", "Évaluation financière de l'impact du projet sur l'économie agricole et montant de la "
     "compensation collective, selon une méthode paramétrable conforme à la structure des doctrines départementales.",
     "Étape 3 sur 4 : impacts, évaluation financière")
require_territoire()
re_ = resultat("rpg_emprise")
if re_ is None or re_["gdf"].empty:
    st.info("Analysez d'abord l'emprise du projet (page **Effets du projet**) : le calcul s'appuie sur les cultures déclarées dans l'emprise.")
    st.page_link("app_pages/p09_effets.py", label="Analyser l'emprise", icon=":material/arrow_forward:")
    st.stop()

pj = st.session_state.get("projet")
ge = re_["gdf"]
base = ge.groupby("groupe", as_index=False)["surface_ha"].sum().sort_values("surface_ha", ascending=False)

with st.expander("Méthode de calcul", expanded=False):
    st.markdown(
        """
**Perte annuelle primaire** = Σ (surface affectée effective × produit brut par ha)
– surfaces soustraites (pistes, postes, locaux…) : 100 % du produit brut ;
– zone agrivoltaïque : taux de baisse de production attendu, ou écart de produit brut en cas de changement de production.

**Perte annuelle aval** = perte primaire × coefficient filières aval
**Impact cumulé** = (primaire + aval) × durée de reconstitution
**Montant de compensation** = impact cumulé ÷ ratio d'investissement

Les coefficients (produit brut ou valeur ajoutée par ha, coefficient aval, durée, ratio) sont fixés par la **doctrine
départementale** (DDT / chambre d'agriculture) : renseignez ceux du département concerné. Exemples publiés : durée d'environ
7 ans (doctrine de l'Ardèche), ratio de 5,6 (guide de la DDT de la Haute-Saône), 6,69 € de production par € investi (Chambre
d'agriculture des Bouches-du-Rhône, PACA). Voir « Cadre réglementaire et sources ».
"""
    )

st.markdown("##### 1. Produit brut par hectare des cultures de l'emprise")
st.caption("Sources possibles : coefficients de production brute standard (Agreste), RICA, références des chambres d'agriculture, "
           "comptabilités des exploitations concernées. Indiquez la source retenue dans le rapport.")
prev = st.session_state.get("pb_table")
tab = base.copy()
tab["pb_eur_ha"] = 0.0
if prev is not None:
    tab = tab.drop(columns="pb_eur_ha").merge(prev[["groupe", "pb_eur_ha"]], on="groupe", how="left").fillna({"pb_eur_ha": 0.0})
c1, c2 = st.columns([1, 3])
val_unique = c1.number_input("Valeur unique (€/ha)", min_value=0.0, value=0.0, step=50.0)
if c1.button("Appliquer à tous les groupes"):
    tab["pb_eur_ha"] = val_unique
    st.session_state.pop("ed_pb", None)  # repart des nouvelles valeurs dans l'éditeur
with c2:
    tab = st.data_editor(tab, hide_index=True, key="ed_pb", disabled=["groupe", "surface_ha"],
                         column_config={"groupe": "Groupe de cultures", "surface_ha": st.column_config.NumberColumn("Surface dans l'emprise (ha)", format="%.2f"),
                                        "pb_eur_ha": st.column_config.NumberColumn("Produit brut (€/ha/an)", min_value=0.0, step=10.0, format="%.0f")})
st.session_state["pb_table"] = tab
source_pb = st.text_input("Source des valeurs de produit brut", st.session_state.get("source_pb", ""), placeholder="ex. PBS 2017 Agreste – région X ; références CA…")
st.session_state["source_pb"] = source_pb

st.markdown("##### 2. Paramètres")
p0: C.Parametres = st.session_state.get("comp_params") or C.Parametres(
    type_projet="Agrivoltaïque" if (pj is None or pj.type_projet == "Agrivoltaïque") else "Artificialisation",
    surface_infrastructures_ha=float(getattr(pj, "surface_infrastructures_ha", 0.0) or 0.0))
c1, c2, c3 = st.columns(3)
with c1:
    typ = st.radio("Nature de l'impact", ["Agrivoltaïque", "Artificialisation"], index=0 if p0.type_projet == "Agrivoltaïque" else 1,
                   help="Agrivoltaïque : production maintenue avec une baisse ; artificialisation : perte totale sur l'emprise.")
    infra = st.number_input("Surfaces soustraites à la production (ha)", min_value=0.0, value=float(p0.surface_infrastructures_ha), step=0.1, disabled=typ != "Agrivoltaïque")
with c2:
    chg = st.checkbox("Changement de production sur la zone agrivoltaïque", value=p0.pb_apres_projet_eur_ha is not None, disabled=typ != "Agrivoltaïque")
    taux = st.number_input("Baisse de production attendue (%)", min_value=0.0, max_value=100.0, value=float(p0.taux_perte_zone_agri_pct), step=1.0,
                           disabled=(typ != "Agrivoltaïque" or chg),
                           help="10 % correspond au plafond implicite du critère de rendement (≥ 90 % de la zone témoin) : scénario majorant.")
    pb_apres = st.number_input("Produit brut après projet (€/ha)", min_value=0.0, value=float(p0.pb_apres_projet_eur_ha or 0.0), step=10.0,
                               disabled=(typ != "Agrivoltaïque" or not chg))
with c3:
    coef = st.number_input("Coefficient filières aval", min_value=0.0, value=float(p0.coefficient_aval), step=0.05, format="%.2f",
                           help="Valeur ajoutée générée par l'aval pour 1 € de production primaire (doctrine départementale).")
    duree = st.number_input("Durée de reconstitution (ans)", min_value=1.0, max_value=30.0, value=float(p0.duree_reconstitution_ans), step=1.0)
    preset = st.selectbox("Ratio d'investissement", ["Personnalisé", "5,6 – guide DDT Haute-Saône (2020)", "6,69 – Chambre d'agriculture 13 (PACA)"])
    ratio_def = {"5,6 – guide DDT Haute-Saône (2020)": 5.6, "6,69 – Chambre d'agriculture 13 (PACA)": 6.69}.get(preset, float(p0.ratio_investissement))
    ratio = st.number_input("Valeur du ratio", min_value=0.1, value=ratio_def, step=0.1, disabled=preset != "Personnalisé")
c1, c2 = st.columns(2)
etp = c1.number_input("Emplois agricoles par 100 ha (facultatif, ETP)", min_value=0.0, value=float(p0.etp_pour_100ha or 0.0), step=0.1,
                      help="Ex. ETP du RA 2020 (import Cartostat) rapportés à la SAU du territoire.")
valide = c2.checkbox("Les paramètres correspondent à la doctrine départementale applicable", value=p0.parametres_valides)

p = C.Parametres(typ, infra, taux, pb_apres if chg else None, coef, duree, ratio, etp or None, valide)
st.session_state["comp_params"] = p
res = C.calcul(tab[["groupe", "surface_ha", "pb_eur_ha"]], p)
if "erreur" in res:
    st.error(res["erreur"])
    st.stop()
sens = C.sensibilite(tab[["groupe", "surface_ha", "pb_eur_ha"]], p)
stocker("compensation", res)
stocker("compensation_sens", sens)

st.markdown("##### 3. Résultats")
if res["groupes_sans_pb"]:
    st.warning("Produit brut non renseigné pour : " + ", ".join(res["groupes_sans_pb"]) + ". Le résultat est sous-estimé.")
if not valide:
    st.warning("Paramètres non validés : le rapport signalera que le calcul est provisoire.")
kpis([
    ("Perte primaire", fnum(res["perte_primaire_eur_an"]) + " €/an", f"{fnum(res['surface_equivalente_perdue_ha'], 2)} ha équivalents perdus"),
    ("Perte aval", fnum(res["perte_aval_eur_an"]) + " €/an", f"coefficient {fnum(coef, 2)}"),
    ("Impact cumulé", fnum(res["impact_cumule_eur"]) + " €", f"sur {fnum(duree)} ans"),
    ("Compensation collective", fnum(res["montant_compensation_eur"]) + " €", f"ratio {fnum(ratio, 2)}"),
])
texte_auto(texte_compensation(res))
det = res["detail"].copy()
show = [c for c in ["groupe", "surface_ha", "pb_eur_ha", "surface_soustraite_ha", "surface_zone_agri_ha", "perte_primaire_eur_an", "surface_equivalente_perdue_ha"] if c in det]
st.dataframe(det[show], hide_index=True, column_config={c: st.column_config.NumberColumn(format="%.2f") for c in show if c != "groupe"})
if res.get("etp_concernes") is not None:
    st.metric("Emplois agricoles concernés (estimation)", fnum(res["etp_concernes"], 2) + " ETP")
st.markdown("##### Analyse de sensibilité – montant (€) selon la durée et le ratio")
st.dataframe(sens.style.format("{:,.0f}"))
source("Calcul EPA Studio à partir des surfaces RPG de l'emprise et des paramètres saisis. Méthode générique : à adapter à la doctrine départementale.")
st.page_link("app_pages/p11_rapport.py", label="Étape suivante : générer le rapport", icon=":material/arrow_forward:")
