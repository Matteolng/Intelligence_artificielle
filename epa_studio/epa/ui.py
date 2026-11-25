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


def setup_page() -> None:
    from .theme import css

    b = branding_courant()
    st.markdown(css(b.couleur, b.police_titres, b.police_texte), unsafe_allow_html=True)


def entete(etape: str | None, titre: str, intro: str = "", italique: str = "") -> None:
    """En-tête sobre (pages denses et de conclusion)."""
    from .theme import tete

    st.markdown(tete(etape, titre, italique, intro), unsafe_allow_html=True)


def entete_nuit(etape: str | None, titre: str, italique: str = "", intro: str = "", photo: str | None = None,
                credit: str = "Photographie aérienne : IGN, Géoplateforme", grand: bool = False) -> None:
    """En-tête « nuit » avec la photo aérienne du territoire (accueil, démonstration, chiffres clés)."""
    from .theme import hero as _hero

    st.markdown(_hero(etape, titre, italique, intro, photo, credit, grand), unsafe_allow_html=True)


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
        st.markdown(f'<div style="font-family:var(--serif);font-size:1.5rem;line-height:1.1">{html.escape(b.nom)}</div>'
                    f'<div style="font-size:.8rem;opacity:.75">{APP_NAME}</div>', unsafe_allow_html=True)
        st.write("")
        if t is not None:
            demo = " (démonstration)" if st.session_state.get("mode_demo") else ""
            st.markdown(f"**{html.escape(t.nom)}**{demo}  \n{len(t.communes)} communes")
        else:
            st.caption("Aucun territoire défini")
        e = st.session_state.get("emprise")
        if e is not None and not e.empty:
            from .projet import surface_ha

            fict = " (fictive)" if st.session_state.get("emprise_fictive") else ""
            st.caption(f"Emprise du projet : {surface_ha(e):.1f} ha".replace(".", ",") + fict)
        modules = {"RPG": "rpg", "RA 2020": "ra2020", "Filières": "filieres", "SIQO": "siqo", "Bio": "bio",
                   "Foncier": "dvf", "Compensation": "compensation"}
        if t is not None:
            done = sum(resultat(v) is not None for v in modules.values())
            st.progress(done / len(modules), text=f"{done} modules calculés sur {len(modules)}")
