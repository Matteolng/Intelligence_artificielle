"""Composants d'interface Streamlit partagés : thème en marque blanche, en-têtes, tuiles, sources, états."""
from __future__ import annotations

import hashlib
import html
import json
import math

import streamlit as st

from .branding import branding_courant
from .config import APP_NAME

GRIS = {"fond": "#F5F5F7", "surface": "#FFFFFF", "texte": "#1D1D1F", "second": "#6E6E73", "filet": "#D2D2D7",
        "muet": "#86868B"}


def _css(accent: str) -> str:
    return f"""
<style>
:root {{ --accent: {accent}; --texte: {GRIS['texte']}; --second: {GRIS['second']}; --filet: {GRIS['filet']};
        --surface: {GRIS['surface']}; --fond: {GRIS['fond']}; --muet: {GRIS['muet']}; }}
.block-container, [data-testid="stMainBlockContainer"] {{ padding-top: 2.4rem; padding-bottom: 4rem; max-width: 1240px; }}
h1, h2, h3, h4 {{ color: var(--texte); letter-spacing: -0.015em; }}
h1 {{ font-weight: 650 !important; }}
h3, h4 {{ font-weight: 600 !important; }}
[data-testid="stSidebar"] {{ border-right: 1px solid var(--filet); }}
[data-testid="stSidebarNav"] a[aria-current="page"] span {{ color: var(--accent); font-weight: 600; }}
[data-testid="stSidebarNavSeparator"] {{ display: none; }}
a, .stPageLink a p {{ color: var(--accent); }}
.stButton button[kind="primary"], .stDownloadButton button[kind="primary"], .stFormSubmitButton button[kind="primary"] {{
  background: var(--accent); border-color: var(--accent); }}
.stButton button[kind="primary"]:hover {{ filter: brightness(1.08); border-color: var(--accent); }}
:focus-visible {{ outline: 2px solid var(--accent) !important; outline-offset: 2px; }}

.epa-head {{ margin: 0 0 1.6rem 0; }}
.epa-head .etape {{ color: var(--accent); font-size: .9rem; font-weight: 600; margin-bottom: .35rem; }}
.epa-head h1 {{ font-size: 2.15rem; line-height: 1.15; margin: 0 0 .5rem 0; padding: 0; }}
.epa-head p {{ color: var(--second); font-size: 1.05rem; line-height: 1.5; margin: 0; max-width: 68ch; }}

.epa-tile {{ background: var(--surface); border-radius: 14px; padding: 1.1rem 1.2rem 1rem; height: 100%;
            border: 1px solid #E8E8ED; }}
.epa-tile .l {{ color: var(--second); font-size: .88rem; line-height: 1.3; }}
.epa-tile .v {{ color: var(--texte); font-size: 2rem; font-weight: 600; line-height: 1.15; margin: .3rem 0 .15rem;
               font-variant-numeric: tabular-nums; letter-spacing: -0.02em; }}
.epa-tile .s {{ color: var(--second); font-size: .82rem; }}
.epa-tile .na {{ color: var(--muet); font-size: 1.05rem; font-weight: 500; }}
.epa-tile .cmp {{ border-top: 1px solid #E8E8ED; margin-top: .7rem; padding-top: .55rem; display: grid;
                 grid-template-columns: 1fr auto; row-gap: .2rem; font-size: .84rem; color: var(--second);
                 font-variant-numeric: tabular-nums; }}
.epa-tile .cmp b {{ color: var(--texte); font-weight: 500; text-align: right; }}

.epa-source {{ font-size: .78rem; color: var(--second); margin-top: .35rem; }}
.epa-phrase {{ border-left: 3px solid var(--accent); padding: .15rem 0 .15rem .9rem; margin: .9rem 0 .4rem;
              color: var(--texte); font-size: 1rem; line-height: 1.55; max-width: 78ch; }}
.epa-phrase small {{ display: block; color: var(--second); font-size: .78rem; margin-top: .25rem; }}
.epa-missing {{ background: var(--surface); border: 1px dashed #C7C7CC; border-radius: 12px; padding: .9rem 1rem;
               color: var(--second); font-size: .9rem; }}
.epa-missing b {{ color: var(--texte); font-weight: 600; }}
.epa-card {{ background: var(--surface); border-radius: 14px; padding: 1.1rem 1.2rem; height: 100%; border: 1px solid #E8E8ED; }}
.epa-card h4 {{ margin: 0 0 .35rem 0; font-size: 1rem; }}
.epa-card p {{ margin: 0; color: var(--second); font-size: .9rem; line-height: 1.45; }}
.epa-badge {{ display:inline-block; padding: 1px 8px; border-radius: 6px; font-size: .78rem; font-weight: 600; }}
.epa-ok {{ background:#E8F3EA; color:#1E5A2B; }} .epa-warn {{ background:#FFF3DC; color:#7A4F00; }}
.epa-ko {{ background:#FDE7E6; color:#9E2620; }}
.epa-brand {{ font-weight: 650; font-size: 1.02rem; color: var(--texte); line-height: 1.25; }}
.epa-brand span {{ display:block; color: var(--second); font-weight: 400; font-size: .8rem; margin-top: .15rem; }}
.epa-home {{ margin: .6rem 0 1.8rem; max-width: 820px; }}
.epa-home .etape {{ color: var(--accent); font-weight: 600; font-size: .95rem; margin-bottom: .6rem; }}
.epa-home h1 {{ font-size: 2.9rem; line-height: 1.08; font-weight: 650; letter-spacing: -0.03em; margin: 0 0 1rem; padding: 0; }}
.epa-home p {{ color: var(--second); font-size: 1.15rem; line-height: 1.55; margin: 0; max-width: 64ch; }}
.epa-step {{ border-top: 2px solid var(--texte); padding-top: .7rem; }}
.epa-step span {{ color: var(--accent); font-weight: 650; font-size: 1.4rem; display: block; line-height: 1; margin-bottom: .45rem;
                 font-variant-numeric: tabular-nums; }}
.epa-step b {{ display: block; font-size: 1rem; margin-bottom: .2rem; }}
.epa-step p {{ color: var(--second); font-size: .9rem; margin: 0; line-height: 1.45; }}
[data-testid="stMetricValue"] {{ font-weight: 600; }}
</style>
"""


def setup_page() -> None:
    st.markdown(_css(branding_courant().couleur), unsafe_allow_html=True)


def entete(etape: str | None, titre: str, intro: str = "") -> None:
    e = f'<div class="etape">{html.escape(etape)}</div>' if etape else ""
    p = f"<p>{intro}</p>" if intro else ""
    st.markdown(f'<div class="epa-head">{e}<h1>{html.escape(titre)}</h1>{p}</div>', unsafe_allow_html=True)


def hero(titre: str, sous_titre: str, etape: str | None = None) -> None:
    """Compatibilité : ancien en-tête → nouvel en-tête sobre."""
    entete(etape, titre, sous_titre)


def _ok(v) -> bool:
    return v is not None and not (isinstance(v, float) and math.isnan(v))


def fmt_val(v, unite: str = "", dec: int = 0, signe: bool = False) -> str:
    """Format français : espace fine insécable pour les milliers, virgule décimale, vrai signe moins."""
    if not _ok(v):
        return "non disponible"
    txt = f"{abs(v):,.{dec}f}".replace(",", "\u202f").replace(".", ",")
    s = "−" if v < 0 else ("+" if signe and v > 0 else "")
    return f"{s}{txt}" + (f"\u202f{unite}" if unite else "")


def tuile_comparee(libelle: str, valeurs: dict, unite: str = "", dec: int = 1, signe: bool = False, sous: str = "") -> str:
    """Tuile chiffre clé : la première valeur est la principale, les suivantes sont des références (département, France)."""
    items = list(valeurs.items())
    _, v0 = items[0]
    val = f'<div class="v">{fmt_val(v0, unite, dec, signe)}</div>' if _ok(v0) else '<div class="v na">Non disponible</div>'
    cmp = "".join(f"<span>{html.escape(k)}</span><b>{fmt_val(v, unite, dec, signe)}</b>" for k, v in items[1:])
    cmp = f'<div class="cmp">{cmp}</div>' if cmp else ""
    s = f'<div class="s">{html.escape(sous)}</div>' if sous else ""
    return f'<div class="epa-tile"><div class="l">{html.escape(libelle)}</div>{val}{s}{cmp}</div>'


def tuiles(html_tiles: list[str]) -> None:
    cols = st.columns(len(html_tiles))
    for c, t in zip(cols, html_tiles):
        c.markdown(t, unsafe_allow_html=True)


def kpi(label: str, value: str, sub: str = "") -> str:
    s = f'<div class="s">{html.escape(sub)}</div>' if sub else ""
    return f'<div class="epa-tile"><div class="l">{html.escape(label)}</div><div class="v">{html.escape(str(value))}</div>{s}</div>'


def kpis(items: list[tuple[str, str, str]]) -> None:
    tuiles([kpi(l, v, s) for l, v, s in items])


def source(txt: str) -> None:
    st.markdown(f'<div class="epa-source">Source : {txt}</div>', unsafe_allow_html=True)


def sources(*cles: str) -> None:
    """Affiche et enregistre (pour la bibliographie) des sources du catalogue."""
    from . import sources as S

    for c in cles:
        S.enregistrer(c)
    source(" ; ".join(S.citer(c) for c in cles) + ".")


def phrase(txt: str) -> None:
    if txt:
        st.markdown(f'<div class="epa-phrase">{txt}<small>Phrase générée à partir des chiffres calculés, à relire.</small></div>',
                    unsafe_allow_html=True)


def texte_auto(txt: str) -> None:
    phrase(txt)


def manquant(quoi: str, source_txt: str, comment: str = "") -> None:
    c = f"<br>{comment}" if comment else ""
    st.markdown(f'<div class="epa-missing"><b>{html.escape(quoi)} : donnée non disponible.</b> '
                f'Source attendue : {html.escape(source_txt)}.{c}</div>', unsafe_allow_html=True)


def bouton_png(png: bytes | None, nom: str, label: str = "Télécharger en PNG haute définition") -> None:
    if png:
        st.download_button(label, png, f"{nom}.png", "image/png", icon=":material/download:", key=f"png_{nom}")


def badge(statut: str) -> str:
    cls = {"OK": "epa-ok", "Texte officiel": "epa-ok"}.get(statut, "epa-warn")
    if statut.startswith(("Non", "Non conforme")):
        cls = "epa-ko"
    return f'<span class="epa-badge {cls}">{statut}</span>'


def card(titre: str, texte: str) -> str:
    return f'<div class="epa-card"><h4>{titre}</h4><p>{texte}</p></div>'


# ---------------------------------------------------------------------------
# État de session
# ---------------------------------------------------------------------------

def territoire():
    return st.session_state.get("territoire")


def signature_territoire() -> str | None:
    t = territoire()
    if t is None:
        return None
    return hashlib.sha1(json.dumps(t.codes_communes).encode()).hexdigest()[:12]


def resultat(cle: str):
    """Résultat calculé pour le territoire courant (None si territoire modifié depuis)."""
    r = st.session_state.get(f"res::{cle}")
    if r and r.get("sig") == signature_territoire():
        return r["val"]
    return None


def stocker(cle: str, val) -> None:
    st.session_state[f"res::{cle}"] = {"sig": signature_territoire(), "val": val}


def zone_epcis() -> list[str] | None:
    """Codes EPCI si le territoire correspond exactement à des EPCI entiers (filtre API plus rapide), sinon None."""
    t = territoire()
    cfg = st.session_state.get("territoire_cfg", {})
    if t is None or not t.epcis or cfg.get("communes_ajoutees") or cfg.get("communes_retirees"):
        return None
    return [e["code"] for e in t.epcis]


def require_territoire() -> None:
    if territoire() is None:
        st.info("Définissez d'abord le territoire d'étude, ou ouvrez la démonstration depuis l'accueil.", icon=":material/map:")
        st.page_link("app_pages/p01_territoire.py", label="Définir le territoire d'étude", icon=":material/arrow_forward:")
        st.stop()


def progress_callback(bar):
    def cb(frac: float, msg: str) -> None:
        bar.progress(min(max(frac, 0.0), 1.0), text=msg)
    return cb


def sidebar_status() -> None:
    b = branding_courant()
    t = territoire()
    with st.sidebar:
        if b.logo:
            st.logo(str(b.logo), size="large")
        st.markdown(f'<div class="epa-brand">{html.escape(b.nom)}<span>{APP_NAME}</span></div>', unsafe_allow_html=True)
        st.write("")
        if t is not None:
            demo = " (démonstration)" if st.session_state.get("mode_demo") else ""
            st.markdown(f"**{html.escape(t.nom)}**{demo}  \n{len(t.communes)} communes")
        else:
            st.caption("Aucun territoire défini")
        e = st.session_state.get("emprise")
        if e is not None and not e.empty:
            from .projet import surface_ha

            st.caption(f"Emprise du projet : {surface_ha(e):.1f} ha".replace(".", ","))
        modules = {"RPG": "rpg", "RA 2020": "ra2020", "Filières": "filieres", "SIQO": "siqo", "Bio": "bio",
                   "Foncier": "dvf", "Compensation": "compensation"}
        if t is not None:
            done = sum(resultat(v) is not None for v in modules.values())
            st.progress(done / len(modules), text=f"{done} modules calculés sur {len(modules)}")
