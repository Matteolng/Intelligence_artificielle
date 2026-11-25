import pandas as pd
import plotly.express as px
import streamlit as st

from epa.sources import enregistrer
from streamlit_folium import st_folium

from epa import bibliotheque, cartes, rpg
from epa.analyse import fnum, texte_rpg
from epa import catalogue as CAT
from epa.config import FAMILLE_COLORS
from epa.http import DataSourceError
from epa.ui import hero, kpis, progress_callback, require_territoire, resultat, source, stocker, texte_auto

hero("Occupation agricole du territoire", "Assolement, cultures, prairies permanentes et surfaces en agriculture biologique "
     "d'après le Registre parcellaire graphique (déclarations PAC).", "Étape 2 sur 4 : état initial, production primaire")
require_territoire()
t = st.session_state["territoire"]

c1, c2 = st.columns([2, 1])
RPG_LAYERS = CAT.rpg_couches()
annee = c1.selectbox("Millésime du RPG", list(RPG_LAYERS), index=0)
c2.write("")
c2.write("")
lancer = c2.button("Charger / mettre à jour le RPG", type="primary", width="stretch")

res = resultat("rpg")
if res is not None and res["annee"] != annee:
    st.caption(f"Résultats affichés : RPG {res['annee']}. Cliquez sur le bouton pour charger le millésime sélectionné.")
if lancer:
    bar = st.progress(0.0, text="Préparation…")
    try:
        g = bibliotheque.rpg_territoire(RPG_LAYERS[annee], annee.split(' ')[0], t, progress=progress_callback(bar))
    except DataSourceError as e:
        st.error(f"Le service WFS de la Géoplateforme n'a pas répondu : {e}")
        st.stop()
    bar.empty()
    res = {
        "annee": annee, "gdf": g, "ind": rpg.indicateurs(g), "asso": rpg.assolement(g),
        "familles": rpg.assolement(g, by="famille"), "cultures": rpg.cultures_detail(g), "communes": rpg.par_commune(g),
    }
    stocker("rpg", res)

if res is None:
    st.info("Cliquez sur **Charger le RPG** pour télécharger les parcelles du territoire (quelques secondes à quelques minutes "
            "selon la taille du territoire ; les données sont ensuite en cache).")
    st.stop()

g, ind, asso = res["gdf"], res["ind"], res["asso"]
if g.empty:
    st.warning("Aucune parcelle trouvée.")
    st.stop()

annee_lbl = res["annee"].split(" ")[0]
surf_moy = ind.get("Surface moyenne d'une parcelle (ha)")
kpis([
    ("Surface déclarée PAC", fnum(ind["Surface déclarée (ha)"]) + " ha", f"{fnum(100 * ind['Surface déclarée (ha)'] / t.surface_ha, 1)} % du territoire"),
    ("Parcelles", fnum(ind["Nombre de parcelles"]), f"{fnum(surf_moy, 2)} ha en moyenne"),
    ("Prairies perm., estives, landes", fnum(ind["Part prairies permanentes, estives et landes (%)"], 1) + " %", "de la surface déclarée"),
    ("Parcelles déclarées en bio", fnum(ind.get("Part de la surface déclarée en bio (%)"), 1) + " %", "de la surface déclarée"),
])
texte_auto(texte_rpg(ind, asso, annee_lbl, t.surface_ha))

tab1, tab2, tab3, tab4 = st.tabs(["Assolement", "Carte", "Par commune", "Évolution"])

with tab1:
    c1, c2 = st.columns([3, 2])
    a = asso.copy()
    a["famille"] = a["groupe"].map(rpg.FAMILLE_PAR_LIBELLE).fillna("Gel et divers")
    fig = px.bar(a.sort_values("surface_ha"), x="surface_ha", y="groupe", color="famille", orientation="h",
                 color_discrete_map=FAMILLE_COLORS, labels={"surface_ha": "Surface (ha)", "groupe": "", "famille": "Famille"},
                 hover_data={"part_pct": ":.1f", "nb_parcelles": True})
    fig.update_layout(height=max(380, 26 * len(a)), margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h", y=-0.15),
                      title=f"Surfaces déclarées par groupe de cultures – RPG {annee_lbl}", yaxis={"categoryorder": "total ascending"})
    c1.plotly_chart(fig)
    fams = res["familles"]
    fig2 = px.pie(fams, values="surface_ha", names="famille", hole=0.55, color="famille", color_discrete_map=FAMILLE_COLORS)
    fig2.update_layout(height=420, margin=dict(l=10, r=10, t=30, b=10), showlegend=True, legend=dict(orientation="h", y=-0.2),
                       title="Répartition par grande famille")
    fig2.update_traces(textinfo="percent", textposition="inside")
    fig2.update_layout(uniformtext_minsize=11, uniformtext_mode="hide")
    c2.plotly_chart(fig2)
    st.markdown("##### Détail par culture déclarée")
    st.dataframe(res["cultures"].rename(columns={"culture": "Culture", "surface_ha": "Surface (ha)", "nb_parcelles": "Parcelles", "part_pct": "Part (%)"}),
                 hide_index=True, height=360,
                 column_config={"Surface (ha)": st.column_config.NumberColumn(format="%.1f"), "Part (%)": st.column_config.ProgressColumn(format="%.1f %%", min_value=0, max_value=100)})
    enregistrer("rpg:" + str(annee_lbl)[:4])
    source(f"Registre parcellaire graphique {annee_lbl} – IGN / ASP, Géoplateforme (WFS). Surfaces calculées en Lambert-93.")

with tab2:
    mode = st.radio("Représentation", ["Famille dominante par commune", "Part des prairies permanentes par commune",
                                        "Surface déclarée par commune", "Parcelles (si moins de 12 000)"], horizontal=True)
    m = cartes.base_map(t.bounds)
    pc = res["communes"]
    gc = t.communes.merge(pc, left_on="code", right_on="code_commune", how="left")
    if mode == "Famille dominante par commune":
        gc["Famille dominante"] = gc["Famille dominante"].fillna("Gel et divers")
        cartes.categorical(m, gc, "Famille dominante", FAMILLE_COLORS, "Famille dominante",
                           ["nom", "Famille dominante"], ["Commune", "Famille dominante"], simplify=0.0003)
        cartes.add_legend(m, {k: v for k, v in FAMILLE_COLORS.items() if k in set(gc["Famille dominante"])}, "Famille dominante")
    elif mode == "Part des prairies permanentes par commune":
        col = "Prairies permanentes, estives et landes"
        gc["part_pp"] = 100 * gc.get(col, 0) / gc["Total RPG (ha)"]
        cartes.choropleth(m, gc, "part_pp", "Part prairies perm. (%)", "Greens", "{:.1f}")
    elif mode == "Surface déclarée par commune":
        cartes.choropleth(m, gc, "Total RPG (ha)", "Surface déclarée PAC (ha)", "YlGn", "{:,.0f}")
    else:
        if len(g) > 12000:
            st.info(f"{fnum(len(g))} parcelles : affichage via le service WMS de l'IGN pour préserver la fluidité.")
            cartes.add_wms(m, [CAT.NOM_RPG_PAC])
        else:
            gp = g[["culture", "groupe", "famille", "surface_ha", "geometry"]].copy()
            gp["surface_ha"] = gp["surface_ha"].round(2)
            cartes.categorical(m, gp, "famille", FAMILLE_COLORS, "Parcelles RPG", ["culture", "groupe", "surface_ha"],
                               ["Culture", "Groupe", "Surface (ha)"], simplify=0.00002)
            cartes.add_legend(m, FAMILLE_COLORS, "Familles de cultures")
    cartes.add_territoire(m, t.communes)
    cartes.add_emprise(m, st.session_state.get("emprise"))
    cartes.finalize(m)
    st_folium(m, height=600, use_container_width=True, returned_objects=[], key="map_rpg")
    source(f"RPG {annee_lbl} – IGN / ASP ; limites communales : API Découpage administratif.")

with tab3:
    pc = res["communes"].copy()
    num = [c for c in pc.columns if c not in ("code_commune", "nom_commune", "Famille dominante")]
    st.dataframe(pc.rename(columns={"code_commune": "Code INSEE", "nom_commune": "Commune"}), hide_index=True, height=480,
                 column_config={c: st.column_config.NumberColumn(format="%.1f") for c in num})
    source(f"RPG {annee_lbl} – surfaces (ha) par commune de localisation de la parcelle.")

with tab4:
    st.caption("Compare l'assolement déclaré entre deux millésimes du RPG (les nomenclatures de cultures ont évolué depuis 2015 : "
               "comparer de préférence au niveau des groupes de cultures).")
    _autres = [k for k in RPG_LAYERS if k != res["annee"]]
    ref = st.selectbox("Millésime de comparaison", _autres, index=min(4, len(_autres) - 1))
    if st.button("Comparer"):
        bar = st.progress(0.0, text="Téléchargement…")
        try:
            g2 = bibliotheque.rpg_territoire(RPG_LAYERS[ref], ref.split(' ')[0], t, progress=progress_callback(bar))
        except DataSourceError as e:
            st.error(str(e))
            st.stop()
        bar.empty()
        a1 = rpg.assolement(g)[["groupe", "surface_ha"]].rename(columns={"surface_ha": f"{annee_lbl} (ha)"})
        a2 = rpg.assolement(g2)[["groupe", "surface_ha"]].rename(columns={"surface_ha": f"{ref.split(' ')[0]} (ha)"})
        ev = a2.merge(a1, on="groupe", how="outer").fillna(0)
        c_old, c_new = ev.columns[1], ev.columns[2]
        ev["Évolution (ha)"] = ev[c_new] - ev[c_old]
        ev["Évolution (%)"] = 100 * ev["Évolution (ha)"] / ev[c_old].where(ev[c_old] > 0)
        tot = pd.DataFrame([{"groupe": "TOTAL", c_old: ev[c_old].sum(), c_new: ev[c_new].sum(),
                             "Évolution (ha)": ev["Évolution (ha)"].sum(),
                             "Évolution (%)": 100 * ev["Évolution (ha)"].sum() / ev[c_old].sum() if ev[c_old].sum() else None}])
        ev = pd.concat([ev.sort_values(c_new, ascending=False), tot], ignore_index=True)
        stocker("rpg_evolution", ev)
        st.dataframe(ev.rename(columns={"groupe": "Groupe de cultures"}), hide_index=True,
                     column_config={c: st.column_config.NumberColumn(format="%.1f") for c in ev.columns if c != "groupe"})
        source(f"RPG {ref.split(' ')[0]} et {annee_lbl} – IGN / ASP.")

st.page_link("app_pages/p04_exploitations.py", label="Étape suivante : structures des exploitations (RA 2020)", icon=":material/arrow_forward:")
