from datetime import date

import pandas as pd
import streamlit as st

from epa import figures, rpg
from epa import teledetection as TD
from epa import catalogue as CAT
from epa.http import DataSourceError
from epa.projet import surface_ha
from epa.sources import enregistrer
from epa.territoire import L93
from epa.theme import calendrier, carte_indice, courbes, ornement, photo_territoire
from epa.ui import (bouton_png, entete_nuit, manquant, phrase, progress_callback, require_territoire, resultat, sources, stocker,
                    tuile_comparee, tuiles)

require_territoire()
t = st.session_state["territoire"]
emprise = st.session_state.get("emprise")

entete_nuit("Étape 2 sur 4, état initial", "Le site", "vu par satellite",
            "Chaque parcelle de l'emprise suivie image après image par Sentinel-2 : cycles de culture, périodes de sol nu, "
            "eau dans la végétation, et comparaison avec les parcelles voisines de même culture.",
            photo=photo_territoire(t.communes))

# --- Les indicateurs, expliqués -------------------------------------------------------------------------------
st.markdown('<div class="epa-nuit"><h2 style="margin:0">Quatre indicateurs, <em>et ce qu\'ils disent</em></h2>'
            '<div class="epa-indices">' + "".join(carte_indice(i) for i in TD.INDICES.values()) + "</div>"
            '<div class="epa-source" style="margin-top:1rem">Formules : catalogue Awesome Spectral Indices (Montero et al., 2023, '
            'Scientific Data 10:197). Images : Copernicus Sentinel-2 niveau 2A (ESA), 10 m (20 m pour le SWIR) ; nuages, ombres et neige masqués '
            '(une date n\'est retenue que si 60 % de l\'emprise est dégagée).</div></div>',
            unsafe_allow_html=True)

if emprise is None or emprise.empty:
    manquant("Emprise du projet", "page Projet et emprise", "L'analyse porte sur l'emprise : importez-la, dessinez-la, ou lancez une "
             "démonstration depuis l'accueil.")
    st.page_link("app_pages/p02_projet.py", label="Renseigner l'emprise", icon=":material/arrow_forward:")
    st.stop()

# --- Paramètres --------------------------------------------------------------------------------------------------
annee = date.today().year
c1, c2, c3 = st.columns([1.4, 1, 1])
annees = c1.multiselect("Années analysées", list(range(annee, annee - 6, -1)), default=[annee - 1, annee], placeholder="Choisir",
                        help="Une année complète prend environ 40 secondes au premier calcul, puis elle est en cache.")
rayon = c2.select_slider("Voisinage comparé", options=[0, 1000, 2000, 3000], value=2000,
                         format_func=lambda r: "aucun" if r == 0 else f"{r // 1000} km")
c3.write("")
lancer = c3.button("Analyser le site", type="primary", icon=":material/satellite_alt:", width="stretch")
if st.session_state.get("emprise_fictive"):
    st.caption("Emprise fictive de démonstration : remplacez-la par celle du projet.")

res = resultat("teledec")
cle = (tuple(sorted(annees)), rayon, round(surface_ha(emprise), 2))
if (lancer or (st.session_state.get("mode_demo") and res is None)) and annees:
    bar = st.progress(0.0, text="Parcelles du registre parcellaire graphique…")
    try:
        RPG_LAYERS = CAT.rpg_couches()
        lay = RPG_LAYERS[next(iter(RPG_LAYERS))]
        site = rpg.rpg_emprise(lay, emprise)
        vois = None
        if rayon:
            b = emprise.to_crs(L93).buffer(rayon).to_crs(4326).total_bounds
            vois = rpg.normalise(rpg.fetch_rpg_bbox(lay, tuple(round(v, 6) for v in b)))
        zones = TD.zones_analyse(emprise, site, vois)
        out = TD.analyser(emprise, zones, f"{min(annees)}-01-01", f"{max(annees)}-12-31", progress=progress_callback(bar))
    except DataSourceError as e:
        bar.empty()
        manquant("Images Sentinel-2", "Copernicus via Earth Search", f"{e} Réessayez dans un instant.")
        st.stop()
    bar.empty()
    noms = {}
    zs = zones[zones["type"] != "voisin"].copy()
    zs["ha"] = zs.to_crs(L93).area / 1e4
    for i, r in enumerate(zs.sort_values("ha", ascending=False).itertuples(), start=1):
        if r.zone == "hors_rpg":
            noms[r.zone] = f"Hors RPG ({r.ha:.1f} ha)".replace(".", ",")
        else:
            noms[r.zone] = f"Parcelle {i} – {r.culture or 'culture non renseignée'} ({r.ha:.1f} ha)".replace(".", ",")
    noms["emprise"] = "Emprise entière"
    affichees = [z for z in zs.sort_values("ha", ascending=False)["zone"] if z != "emprise"][:7]
    b_ = TD.bilan(out["series"], zones)
    if not b_.empty:
        b_.insert(0, "Zone (nom)", b_["Zone"].map(noms).fillna(b_["Zone"]))
    an_ref = int(CAT.annee_de_couche(lay) or CAT.annee_rpg_recente())  # millésime des cultures : comparaisons sur cette année
    v_ = TD.voisinage(out["series"], zones, an_ref) if rayon else pd.DataFrame()
    if not v_.empty:
        v_.insert(0, "Parcelle (nom)", v_["Parcelle"].map(noms).fillna(v_["Parcelle"]))
    gif = figures.animation_ndvi(out["anim"], emprise, zs, out["bbox_anim"], crs=out.get("anim_crs"), bornes=out.get("anim_bornes"))
    cults = zs[zs["zone"].isin(affichees) & zs["culture"].notna()]
    c_princ = cults.groupby("culture")["ha"].sum().idxmax() if not cults.empty else None
    f_ndvi = TD.fourchette(out["series"], zones, c_princ, annee=an_ref) if c_princ and rayon else None
    png = figures.series_indices(out["series"], affichees, noms,
                                 note=f"{len(affichees)} plus grandes zones de l'emprise sur {len(zs)}" if len(zs) > len(affichees) else "",
                                 fourchette=f_ndvi, fourchette_label=f"parcelles voisines – {c_princ.lower()} (25e-75e centile)" if c_princ else "")
    res = {"cle": cle, "series": out["series"].assign(zone_nom=out["series"]["zone"].map(noms)), "bilan": b_, "voisinage": v_,
           "zones": zones, "noms": noms, "affichees": affichees, "annee_ref": an_ref, "images": out["images"],
           "dates": out["dates_valides"], "erreurs": out["erreurs"], "figures": {"satellite_ndvi_anime": gif, "satellite_indices": png}}
    stocker("teledec", res)

if res is None:
    st.info("Lancez l'analyse : les images Sentinel-2 de l'emprise sont lues sur la période choisie (les nuages sont écartés).",
            icon=":material/satellite_alt:")
    st.stop()
if res["cle"] != cle:
    st.caption("Résultats affichés pour d'autres paramètres : relancez l'analyse pour les mettre à jour.")
enregistrer("s2")
enregistrer("asi")
enregistrer("usgs_ndvi")
enregistrer("timesat")
enregistrer(f"rpg:{res['annee_ref']}")

S, z, noms = res["series"], res["zones"], res["noms"]
_fcache = res.setdefault("_fourchettes", {})


def fourchette(culture, indice):
    """Fourchette des voisines (année du RPG), mémorisée dans le résultat : calculée une fois par culture et indice."""
    k = (culture, indice)
    if k not in _fcache:
        _fcache[k] = TD.fourchette(S, z, culture, indice, annee=res["annee_ref"])
    return _fcache[k]
emp = S[S["zone"] == "emprise"]

# --- Le film du site et les chiffres -------------------------------------------------------------------------------
st.markdown(ornement(), unsafe_allow_html=True)
st.markdown('<h2>Le site, <em style="color:var(--accent)">image après image</em></h2>', unsafe_allow_html=True)
g1, g2 = st.columns([1.15, 1], gap="large")
with g1:
    if res["figures"]["satellite_ndvi_anime"]:
        st.image(res["figures"]["satellite_ndvi_anime"], width="stretch")
        st.caption("NDVI de l'emprise (contour sombre) et des parcelles déclarées (contours blancs) : du beige (sol nu) au vert "
                   "foncé (végétation dense). Gris : pixels masqués par les nuages.")
    else:
        manquant("Animation NDVI", "Sentinel-2", "Pas assez d'images sans nuage sur l'emprise.")
with g2:
    nd = emp[emp["indice"] == "NDVI"]
    tuiles([tuile_comparee("Images examinées", {"Emprise": float(res["images"])}, "", 0, sous=f"{res['dates']} dates sans nuage sur l'emprise"),
            tuile_comparee("NDVI maximal", {"Emprise": float(nd["valeur"].max()) if not nd.empty else None}, "", 2,
                           sous=f"le {pd.Timestamp(nd.loc[nd['valeur'].idxmax(), 'date']).strftime('%d/%m/%Y')}" if not nd.empty else "")])
    st.write("")
    bil = res["bilan"]
    be = bil[bil["Zone"] == "emprise"] if not bil.empty else bil
    tuiles([tuile_comparee("Sol nu probable", {"Emprise": float(be["Sol nu probable (% des dates)"].mean()) if not be.empty else None}, "%", 0,
                           sous="part des dates sans nuage"),
            tuile_comparee("Cycles de végétation", {"Emprise": float(be["Cycles de végétation"].mean()) if not be.empty else None}, "", 1,
                           sous="par an, en moyenne")])

# --- Courbes animées ---------------------------------------------------------------------------------------------------
st.markdown("### Les courbes, parcelle par parcelle")
ci, cp = st.columns([1, 2.2])
ind = ci.segmented_control("Indicateur", list(TD.INDICES), default="NDVI", label_visibility="collapsed") or "NDVI"
choix = cp.multiselect("Parcelles affichées", res["affichees"], default=res["affichees"][:4], format_func=lambda k: noms.get(k, k),
                       placeholder="Choisir des parcelles", label_visibility="collapsed")
choix = choix or res["affichees"][:1]
serie = {noms.get(k, k): [(d, v) for d, v in S[(S["zone"] == k) & (S["indice"] == ind)].sort_values("date")[["date", "valeur"]].itertuples(index=False)]
         for k in choix}
ref, ref_lab, fch, c0 = None, "", None, None
_zs = z[z["zone"].isin([a for a in choix if a.startswith("site:")]) & z["culture"].notna()].copy()
if not _zs.empty:
    _zs["ha"] = _zs.to_crs(L93).area / 1e4
    c0 = _zs.groupby("culture")["ha"].sum().idxmax()
    f_ind = fourchette(c0, ind)
    if not f_ind.empty:
        ref = list(zip(f_ind["date"], f_ind["p50"]))
        ref_lab = f"médiane des parcelles voisines – {c0.lower()} au RPG {res['annee_ref']} ({int(f_ind['n'].max())} au plus par date)"
        fch = list(zip(f_ind["date"], f_ind["p25"], f_ind["p75"]))
I = TD.INDICES[ind]
st.markdown(courbes(serie, figures.SERIES, I.vmin, I.vmax, ref, ref_lab,
                    bandes=TD.REPERES_NDVI if ind == "NDVI" else None, fourchette=fch), unsafe_allow_html=True)
st.caption(f"{I.code} : {I.montre} " + ("Bandes de fond : repères de lecture de l'USGS. " if ind == "NDVI" else "")
           + ("Bande grise : la moitié centrale des parcelles voisines de même culture, la même année ; une courbe qui en sort "
              "s'écarte du comportement local. " if fch else "") + "Survolez un point pour lire sa date et sa valeur.")

with st.expander("Lire ces courbes sans être spécialiste"):
    st.markdown(
        "- **Repères généraux du NDVI** (USGS) : 0,1 ou moins pour la roche, le sable, la neige ou le sol nu ; environ 0,2 à 0,5 "
        "pour une végétation clairsemée, une prairie ou une culture en fin de cycle ; environ 0,6 à 0,9 pour une végétation dense "
        "ou une culture à son pic.\n"
        "- **Référence locale** : la bande grise regroupe la moitié centrale des parcelles voisines déclarées avec la même culture, "
        "la même année : même météo, mêmes sols, même calendrier. C'est la comparaison la plus juste.\n"
        "- **Une culture d'hiver** (blé, orge, colza) monte au printemps et chute à la récolte en été ; **une culture de printemps** "
        "(maïs, tournesol) culmine en été ; **une prairie** reste haute presque toute l'année.\n"
        "- **Les dates clés** (début, pic, fin de saison) sont calculées quand la courbe franchit la moitié de son amplitude annuelle "
        "(méthode du seuil d'amplitude, logiciel TIMESAT).")

_toutes = TD.phrases(res["bilan"], res["voisinage"], noms, res["annee_ref"])
_vis = [noms.get(k, k) for k in choix] + ["Emprise entière"]
_haut = sorted([p for p in _toutes if any(p.startswith(n) for n in _vis)])
_reste = sorted([p for p in _toutes if p not in _haut])
for p in _haut:
    phrase(p)
if _reste:
    with st.expander(f"Phrases des {len(_reste)} autres zones"):
        for p in _reste:
            phrase(p)
if c0:
    f_nd = fourchette(c0, "NDVI")
    fen = TD.fenetre_saison(f_nd.set_index("date")["p50"]) if not f_nd.empty else None
    for k in [a for a in choix if a.startswith("site:") and z.set_index("zone").loc[a, "culture"] == c0]:
        pos = TD.position_fourchette(S[(S["zone"] == k) & (S["indice"] == "NDVI")][["date", "valeur"]], f_nd, fen)
        if pos:
            periode = (f"pendant la saison de la culture ({c0.lower()}, {fen[0].strftime('%d/%m')} – {fen[1].strftime('%d/%m/%Y')})"
                       if fen else f"en {res['annee_ref']}")
            txt = (f"{noms.get(k, k)} : {periode}, {pos['dedans_pct']} % des {pos['n']} dates dans la fourchette des "
                   f"parcelles voisines")
            if pos["sous"]:
                txt += f" ; en dessous en {TD.mois_txt(pos['sous'])}"
            if pos["dessus"]:
                txt += f" ; au-dessus en {TD.mois_txt(pos['dessus'])}"
            phrase(txt + ".")

# --- Calendrier cultural observé --------------------------------------------------------------------------------------------
st.markdown('<h3>Calendrier cultural <em style="color:var(--accent)">observé</em></h3>', unsafe_allow_html=True)
lignes_cal = []
for k in choix:
    nd = S[(S["zone"] == k) & (S["indice"] == "NDVI")].set_index("date")["valeur"].sort_index()
    jal = []
    for an, g in nd.groupby(nd.index.year):
        ph = TD.phenologie(g)
        jal += [(ph.get("debut"), f"Début de saison {an}"), (ph.get("pic"), f"Pic {an}"), (ph.get("fin"), f"Fin de saison {an}")]
    lignes_cal.append({"nom": noms.get(k, k), "points": list(nd.items()), "jalons": jal})
if c0 and ref:
    _fm = fourchette(c0, "NDVI")
    lignes_cal.append({"nom": f"Voisines – {c0.lower()} {res['annee_ref']}", "points": [(d, v) for d, v in _fm[["date", "p50"]].itertuples(index=False)],
                       "jalons": [(TD.phenologie(_fm.set_index('date')['p50']).get(k), f"{lab} (voisines)") for k, lab in
                                  (("debut", "Début de saison"), ("pic", "Pic"), ("fin", "Fin de saison"))]})
if lignes_cal:
    st.markdown(calendrier(lignes_cal, S["date"].min(), S["date"].max()), unsafe_allow_html=True)
    st.caption("Chaque bande suit le NDVI de la parcelle au fil des dates sans nuage : beige pour le sol nu, vert foncé pour une "
               "végétation dense. Les triangles marquent le début, le pic et la fin de chaque saison. Survolez pour lire les dates.")

# --- Tableaux -------------------------------------------------------------------------------------------------------------
st.markdown("### Bilan par parcelle et par année")
if not res["bilan"].empty:
    st.dataframe(res["bilan"].drop(columns=["Zone"]), hide_index=True, width="stretch")
st.caption("Règles de lecture de l'outil (repères indicatifs, à confirmer sur le terrain) : " + " ; ".join(TD.REGLES.values()) + ".")
if res["annee_ref"] not in annees:
    st.caption(f"Les comparaisons au voisinage portent sur {res['annee_ref']}, année du RPG utilisé : ajoutez-la aux années analysées.")
if not res["voisinage"].empty:
    st.markdown(f"### Comparaison au voisinage ({res['annee_ref']})")
    st.dataframe(res["voisinage"].drop(columns=["Parcelle"]), hide_index=True, width="stretch")
    st.caption("NDVI maximal de l'année comparé à celui des parcelles voisines déclarées avec la même culture au RPG. "
               "C'est une observation de vigueur relative, pas un rendement.")

st.markdown("### Figures et données")
e1, e2, e3 = st.columns(3)
with e1:
    bouton_png(res["figures"]["satellite_indices"], "satellite_indices", "Figure des indices (PNG 300 dpi)")
with e2:
    if res["figures"]["satellite_ndvi_anime"]:
        st.download_button("Animation NDVI (GIF)", res["figures"]["satellite_ndvi_anime"], "satellite_ndvi_anime.gif", "image/gif",
                           icon=":material/download:")
with e3:
    st.download_button("Séries complètes (CSV)", S.to_csv(index=False, sep=";").encode("utf-8-sig"), "satellite_series.csv", "text/csv",
                       icon=":material/download:", help="État de référence avant projet : toutes les valeurs, date par date.")
sources("s2", "asi", "usgs_ndvi", "timesat")
