"""Composants d'interface Streamlit partagés (style, en-têtes, indicateurs, état)."""
from __future__ import annotations

import hashlib
import json

import streamlit as st

from .config import APP_NAME, APP_TAGLINE, COLORS

CSS = f"""
<style>
:root {{ --epa-green: {COLORS['primary']}; --epa-green-light: {COLORS['primary_light']}; --epa-gold: {COLORS['accent']}; }}
.block-container {{ padding-top: 3.2rem; padding-bottom: 3rem; max-width: 1400px; }}
h1, h2, h3 {{ letter-spacing: -0.01em; }}
.epa-hero {{ background: linear-gradient(120deg, #1F5F3F 0%, #2E7D4F 60%, #6E9E3A 100%); color: #fff; border-radius: 16px;
            padding: 1.4rem 1.6rem; margin-bottom: 1.2rem; box-shadow: 0 4px 18px rgba(31,95,63,.18); }}
.epa-hero h1 {{ color:#fff; margin:0 0 .2rem 0; font-size: 1.75rem; }}
.epa-hero p {{ color: rgba(255,255,255,.92); margin:0; font-size: 1rem; }}
.epa-step {{ display:inline-block; background: rgba(255,255,255,.18); color:#fff; padding: 2px 10px; border-radius: 999px;
            font-size: .78rem; margin-bottom: .45rem; font-weight:600; letter-spacing:.02em; }}
.epa-card {{ background: #fff; border: 1px solid #E3E9E4; border-radius: 14px; padding: 1rem 1.1rem; height: 100%;
            box-shadow: 0 1px 3px rgba(0,0,0,.04); }}
.epa-card h4 {{ margin: 0 0 .35rem 0; color: #1F2A24; font-size: 1rem; }}
.epa-card p {{ margin: 0; color: #5F6B66; font-size: .88rem; }}
.epa-kpi {{ background:#fff; border:1px solid #E3E9E4; border-left: 5px solid var(--epa-green); border-radius: 12px;
           padding: .7rem .9rem; }}
.epa-kpi .v {{ font-size: 1.45rem; font-weight: 700; color: #1F2A24; line-height:1.2; }}
.epa-kpi .l {{ font-size: .8rem; color: #5F6B66; text-transform: uppercase; letter-spacing: .03em; }}
.epa-kpi .s {{ font-size: .78rem; color: #5F6B66; margin-top: 2px; }}
.epa-source {{ font-size: .78rem; color: #5F6B66; border-top: 1px dashed #D5DDD7; margin-top: .4rem; padding-top: .35rem; }}
.epa-badge {{ display:inline-block; padding: 1px 8px; border-radius: 999px; font-size: .75rem; font-weight:600; }}
.epa-ok {{ background:#E3F2E7; color:#1F5F3F; }} .epa-warn {{ background:#FFF4D6; color:#8A6100; }} .epa-ko {{ background:#FDE2E0; color:#A3241A; }}
.epa-text {{ background: var(--epa-green-light); border-radius: 12px; padding: .85rem 1rem; color:#1F2A24; font-size:.95rem; }}
[data-testid="stSidebar"] {{ background: #F4F7F4; }}
[data-testid="stMetricValue"] {{ font-size: 1.4rem; }}
</style>
"""


def setup_page() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def hero(titre: str, sous_titre: str, etape: str | None = None) -> None:
    step = f'<div class="epa-step">{etape}</div>' if etape else ""
    st.markdown(f'<div class="epa-hero">{step}<h1>{titre}</h1><p>{sous_titre}</p></div>', unsafe_allow_html=True)


def kpi(label: str, value: str, sub: str = "") -> str:
    s = f'<div class="s">{sub}</div>' if sub else ""
    return f'<div class="epa-kpi"><div class="l">{label}</div><div class="v">{value}</div>{s}</div>'


def kpis(items: list[tuple[str, str, str]]) -> None:
    cols = st.columns(len(items))
    for c, (l, v, s) in zip(cols, items):
        c.markdown(kpi(l, v, s), unsafe_allow_html=True)


def source(txt: str) -> None:
    st.markdown(f'<div class="epa-source">Source : {txt}</div>', unsafe_allow_html=True)


def texte_auto(txt: str) -> None:
    if txt:
        st.markdown(f'<div class="epa-text">📝 <b>Synthèse rédigée automatiquement</b> (à relire)<br>{txt}</div>', unsafe_allow_html=True)


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
        st.info("Commencez par définir le **territoire d'étude** (région, département, EPCI).", icon="🧭")
        st.page_link("app_pages/p01_territoire.py", label="Définir le territoire d'étude", icon="🗺️")
        st.stop()


def progress_callback(bar):
    def cb(frac: float, msg: str) -> None:
        bar.progress(min(max(frac, 0.0), 1.0), text=msg)
    return cb


def sidebar_status() -> None:
    t = territoire()
    with st.sidebar:
        st.markdown(f"### 🌾 {APP_NAME}")
        st.caption(APP_TAGLINE)
        if t is not None:
            st.success(f"**Territoire** : {t.nom}\n\n{len(t.communes)} communes", icon="🗺️")
        else:
            st.warning("Territoire non défini", icon="🧭")
        e = st.session_state.get("emprise")
        if e is not None and not e.empty:
            from .projet import surface_ha

            st.info(f"**Emprise projet** : {surface_ha(e):.1f} ha", icon="📐")
        modules = {
            "RPG": "rpg", "RA 2020": "ra2020", "Filières": "filieres", "SIQO": "siqo", "Bio": "bio",
            "Foncier": "dvf", "Compensation": "compensation",
        }
        done = [k for k, v in modules.items() if resultat(v) is not None]
        if t is not None:
            st.caption("Modules calculés : " + (", ".join(done) if done else "aucun"))
