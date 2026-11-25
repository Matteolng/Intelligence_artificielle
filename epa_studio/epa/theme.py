"""Identité visuelle v2 (maquette validée le 25/11/2026) : nuit, verre dépoli, photo aérienne IGN, gravure du parcellaire.

- Variante « nuit » (accueil, démonstration, en-têtes, chiffres clés) : photo aérienne du territoire, voile vert nuit,
  titres Cormorant Garamond avec une seconde partie en italique, panneaux translucides, animations sobres.
- Variante « sobre » (pages denses et de conclusion) : feuille translucide posée sur la gravure claire du parcellaire.
Les animations sont coupées quand l'utilisateur demande moins de mouvement (prefers-reduced-motion).
"""
from __future__ import annotations

import hashlib
import html
import io
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps

STATIC = Path(__file__).resolve().parents[1] / "static"
GEN = STATIC / "gen"
URL = "app/static"  # servi par Streamlit (server.enableStaticServing)

NUIT, NUIT2, OLIVE, CREME, CLAIR, TEXTE, SECOND = "#18211A", "#1F2A22", "#56653E", "#F4ECDF", "#DCE5BC", "#1F2A22", "#4F5649"
SERIF = "'Cormorant Garamond', Georgia, serif"
SANS = "Inter, system-ui, sans-serif"
ETOILE = ('<svg width="12" height="12" viewBox="0 0 14 14" aria-hidden="true"><path d="M7 0C7.6 5 9 6.4 14 7 9 7.6 7.6 9 '
          '7 14 6.4 9 5 7.6 0 7 5 6.4 6.4 5 7 0Z" fill="currentColor"/></svg>')


def css(accent: str, police_titres: str = "Cormorant Garamond", police_texte: str = "Inter") -> str:
    imp = ""
    if police_titres != "Cormorant Garamond" or police_texte != "Inter":
        fam = "&".join("family=" + p.replace(" ", "+") + ":ital,wght@0,300..700;1,300..700" for p in {police_titres, police_texte})
        imp = f'@import url("https://fonts.googleapis.com/css2?{fam}&display=swap");'
    serif = f"'{police_titres}', Georgia, serif"
    sans = f"'{police_texte}', system-ui, sans-serif"
    return f"""
<style>
{imp}
:root {{ --accent:{accent}; --nuit:{NUIT}; --nuit2:{NUIT2}; --olive:{OLIVE}; --creme:{CREME}; --clair:{CLAIR};
        --texte:{TEXTE}; --second:{SECOND}; --serif:{serif}; --sans:{sans}; }}
body, .stApp, .stMarkdown, p, li, label {{ font-family: var(--sans); }}
@keyframes epaRise {{ from {{opacity:0; transform:translateY(22px)}} to {{opacity:1; transform:none}} }}
@keyframes epaZoom {{ from {{transform:scale(1.03)}} to {{transform:scale(1.13)}} }}
@keyframes epaPan {{ from {{background-position:0% 30%}} to {{background-position:100% 70%}} }}
@keyframes epaLine {{ from {{transform:scaleX(0)}} to {{transform:scaleX(1)}} }}
@keyframes epaGrow {{ from {{transform:scaleX(0)}} to {{transform:scaleX(1)}} }}
@keyframes epaSpin {{ to {{transform:rotate(360deg)}} }}
@keyframes epaTwinkle {{ 0%,100% {{transform:scale(1) rotate(0)}} 50% {{transform:scale(1.25) rotate(45deg)}} }}

/* Fond : gravure claire du parcellaire, feuille translucide pour le contenu */
.stApp {{ background: #ECEEE4 url("{URL}/gravure_claire.jpg") center/150% auto; animation: epaPan 90s linear infinite alternate; }}
[data-testid="stHeader"] {{ background: transparent; }}
.block-container, [data-testid="stMainBlockContainer"] {{ max-width: 1240px; padding: 1.6rem 2.6rem 4rem;
  background: rgba(250,251,246,.84); -webkit-backdrop-filter: blur(10px); backdrop-filter: blur(10px);
  border: 1px solid rgba(63,76,46,.14); border-radius: 26px; margin-top: 1.4rem; margin-bottom: 2rem; }}
h1, h2, h3 {{ font-family: var(--serif) !important; font-weight: 400 !important; letter-spacing: -0.005em; color: var(--texte); }}
h2 {{ font-size: 2.1rem !important; }} h3 {{ font-size: 1.6rem !important; }} h4 {{ font-family: var(--sans) !important; font-weight: 600 !important; }}
a {{ color: var(--accent); }}
.stButton button[kind="primary"], .stDownloadButton button[kind="primary"], .stFormSubmitButton button[kind="primary"] {{
  background: var(--accent); border-color: var(--accent); border-radius: 999px; padding: 0 1.3rem; }}
.stButton button, .stDownloadButton button {{ border-radius: 999px; transition: transform .2s ease; }}
.stButton button:hover, .stDownloadButton button:hover {{ transform: translateY(-1px); }}
:focus-visible {{ outline: 2px solid var(--accent) !important; outline-offset: 2px; }}

/* Barre latérale nuit */
[data-testid="stSidebar"] {{ background: var(--nuit) url("{URL}/gravure_nuit.jpg") center/260% auto; }}
[data-testid="stSidebar"] * {{ color: var(--creme); }}
[data-testid="stSidebarNav"] a[aria-current="page"] {{ background: rgba(220,229,188,.14); }}
[data-testid="stSidebarNav"] a[aria-current="page"] span {{ color: var(--clair); font-weight: 600; }}
[data-testid="stSidebarNavSeparator"] {{ display: none; }}

/* En-tête nuit avec photo du territoire */
.epa-hero {{ position: relative; overflow: hidden; border-radius: 22px; margin: -.4rem 0 1.8rem; background: var(--nuit2); color: var(--creme); }}
.epa-hero img.ph {{ position:absolute; inset:0; width:100%; height:100%; object-fit:cover; opacity:.62; animation: epaZoom 34s ease-in-out infinite alternate; }}
.epa-hero .voile {{ position:absolute; inset:0; background: linear-gradient(100deg, rgba(24,33,26,.94) 0%, rgba(24,33,26,.74) 42%, rgba(24,33,26,.28) 100%); }}
.epa-hero .in {{ position: relative; padding: 2.6rem 2.6rem 2.4rem; }}
.epa-hero .et {{ color: var(--clair); font-size: .9rem; margin-bottom: .8rem; }}
.epa-hero h1 {{ color: var(--creme) !important; font-size: 4rem !important; line-height: 1 !important; font-weight: 300 !important; margin: 0 !important; padding: 0 !important; animation: epaRise .9s cubic-bezier(.2,.7,.2,1) both .1s; }}
.epa-hero h1 em {{ color: var(--clair); font-style: italic; }}
.epa-hero p {{ color: rgba(244,236,223,.86); max-width: 62ch; font-size: 1.02rem; line-height: 1.6; margin: 1rem 0 0; animation: epaRise .9s cubic-bezier(.2,.7,.2,1) both .35s; }}
.epa-hero .credit {{ font-size: .72rem; color: rgba(244,236,223,.6); margin-top: 1.4rem; }}
.epa-hero.grand .in {{ padding: 6rem 3rem 4rem; }}
.epa-hero.grand h1 {{ font-size: 5.6rem !important; }}

/* En-tête sobre */
.epa-head {{ margin: .4rem 0 1.6rem; }}
.epa-head .et {{ color: var(--accent); font-size: .9rem; font-weight: 500; margin-bottom: .3rem; }}
.epa-head h1 {{ font-size: 3rem !important; line-height: 1.05 !important; font-weight: 300 !important; margin: 0 !important; padding: 0 !important; }}
.epa-head h1 em {{ color: var(--accent); }}
.epa-head p {{ color: var(--second); font-size: 1.02rem; line-height: 1.55; margin: .6rem 0 0; max-width: 68ch; }}

/* Panneaux translucides et tuiles */
.epa-glass {{ background: rgba(244,236,223,.10); -webkit-backdrop-filter: blur(16px) saturate(140%); backdrop-filter: blur(16px) saturate(140%);
  border: 1px solid rgba(244,236,223,.24); border-radius: 18px; }}
.epa-tile {{ background: rgba(255,255,255,.72); border: 1px solid rgba(63,76,46,.16); border-radius: 18px; padding: 1.1rem 1.2rem 1rem; height: 100%;
  animation: epaRise .8s cubic-bezier(.2,.7,.2,1) both; }}
.epa-tile .l {{ color: var(--second); font-size: .86rem; }}
.epa-tile .v {{ font-family: var(--serif); font-size: 2.6rem; font-weight: 400; line-height: 1.05; margin: .25rem 0 .1rem; font-variant-numeric: lining-nums tabular-nums; color: var(--texte); }}
.epa-tile .s {{ color: var(--second); font-size: .8rem; }}
.epa-tile .na {{ font-family: var(--sans); color: var(--second); font-size: 1rem; font-weight: 500; }}
.epa-tile .cmp {{ border-top: 1px solid rgba(31,42,34,.14); margin-top: .7rem; padding-top: .55rem; display: grid; grid-template-columns: 1fr auto;
  row-gap: .2rem; font-size: .82rem; color: var(--second); font-variant-numeric: tabular-nums; }}
.epa-tile .cmp b {{ color: var(--texte); font-weight: 500; text-align: right; }}
.epa-phrase {{ font-family: var(--serif); font-size: 1.35rem; line-height: 1.4; color: var(--texte); border-top: 1px solid rgba(31,42,34,.2);
  padding-top: .9rem; margin: 1rem 0 .3rem; max-width: 70ch; }}
.epa-phrase small {{ display:block; font-family: var(--sans); color: var(--second); font-size: .76rem; margin-top: .35rem; }}
.epa-source {{ font-size: .76rem; color: var(--second); margin-top: .35rem; }}
.epa-missing {{ background: rgba(255,255,255,.6); border: 1px dashed rgba(63,76,46,.4); border-radius: 14px; padding: .9rem 1rem; color: var(--second); font-size: .9rem; }}
.epa-missing b {{ color: var(--texte); }}
.epa-orn {{ display:flex; align-items:center; gap:14px; color: var(--accent); margin: 1.8rem 0 1.2rem; }}
.epa-orn span {{ flex:1; height:1px; background: rgba(31,42,34,.2); transform-origin: left; animation: epaLine 1.4s cubic-bezier(.2,.7,.2,1) both; }}

/* Section nuit (cercles des échelles, frise) */
.epa-nuit {{ position: relative; overflow: hidden; border-radius: 22px; background: var(--nuit) url("{URL}/gravure_nuit.jpg") center/150% auto;
  animation: epaPan 80s linear infinite alternate; color: var(--creme); padding: 2.4rem 2.4rem 2.2rem; margin: .6rem 0 1.6rem; }}
.epa-nuit h2, .epa-nuit h3 {{ color: var(--creme) !important; }}
.epa-nuit h2 em {{ color: var(--clair); }}
.epa-rings {{ display:grid; grid-template-columns: minmax(0, 420px) minmax(0, 1fr); gap: 3rem; align-items: center; }}
.epa-rings .spin {{ transform-origin: 210px 210px; animation: epaSpin 120s linear infinite; }}
.epa-scale {{ display:grid; grid-template-columns: 28px minmax(0,1fr) auto; gap: 14px; align-items: baseline; padding: 14px 4px;
  border-top: 1px solid rgba(244,236,223,.18); }}
.epa-scale .n {{ font-family: var(--serif); font-style: italic; font-size: 1.4rem; color: rgba(244,236,223,.45); }}
.epa-scale.on .n {{ color: var(--clair); }}
.epa-scale .lab {{ font-size: .8rem; color: rgba(244,236,223,.72); }}
.epa-scale .nom {{ font-size: 1rem; }}
.epa-scale.on .nom {{ font-weight: 600; }}
.epa-scale .val {{ font-family: var(--serif); font-size: 2.4rem; font-weight: 300; line-height: 1; text-align: right; font-variant-numeric: lining-nums tabular-nums; }}
.epa-scale .ev {{ font-size: .76rem; color: rgba(244,236,223,.72); text-align: right; }}
.epa-nuit .epa-phrase {{ color: var(--creme); border-top-color: rgba(244,236,223,.25); }}
.epa-nuit .epa-phrase small, .epa-nuit .epa-source {{ color: rgba(244,236,223,.72); }}
.epa-frise {{ position: relative; display:grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 2rem; margin-top: 2.2rem; list-style:none; padding:0; }}
.epa-frise::before {{ content:""; position:absolute; left:0; right:0; top: 4.9rem; height:1px; background: rgba(244,236,223,.45); transform-origin:left; animation: epaLine 2s cubic-bezier(.2,.7,.2,1) both .2s; }}
.epa-frise li {{ animation: epaRise .9s cubic-bezier(.2,.7,.2,1) both; }}
.epa-frise li:nth-child(2) {{ animation-delay: .35s; }} .epa-frise li:nth-child(3) {{ animation-delay: .7s; }} .epa-frise li:nth-child(4) {{ animation-delay: 1.05s; }}
.epa-frise .num {{ font-family: var(--serif); font-style: italic; font-weight: 300; font-size: 3.6rem; line-height: 1; color: var(--clair); height: 3.9rem; }}
.epa-frise svg {{ display:block; margin: .45rem 0 1.1rem; color: var(--creme); animation: epaTwinkle 4s ease-in-out infinite; }}
.epa-frise b {{ display:block; font-size: 1.1rem; font-weight: 500; margin-bottom: .35rem; }}
.epa-frise span {{ color: rgba(244,236,223,.84); font-size: .92rem; line-height: 1.55; }}
.epa-bars {{ display:flex; flex-direction:column; gap: 14px; }}
.epa-bar {{ display:grid; grid-template-columns: 200px minmax(0,1fr) 80px; gap: 14px; align-items:center; font-size: .9rem; }}
.epa-bar .track {{ height: 26px; background: rgba(31,42,34,.06); border-radius: 6px; overflow:hidden; }}
.epa-bar .fill {{ height:100%; border-radius: 6px; transform-origin: left; animation: epaGrow 1.1s cubic-bezier(.2,.7,.2,1) both; }}
.epa-bar .v {{ text-align:right; font-variant-numeric: tabular-nums; }}
@keyframes epaDraw {{ from {{stroke-dashoffset:1}} to {{stroke-dashoffset:0}} }}
@keyframes epaPop {{ from {{opacity:0; transform:scale(.4)}} to {{opacity:1; transform:none}} }}
.epa-courbe path.l {{ fill:none; stroke-width:2; stroke-linejoin:round; stroke-linecap:round; stroke-dasharray:1; stroke-dashoffset:1;
  animation: epaDraw 2.2s cubic-bezier(.3,.6,.2,1) forwards; }}
.epa-courbe path.ref {{ fill:none; stroke-width:1.6; stroke-dasharray:4 4; opacity:.85; }}
.epa-courbe circle {{ opacity:0; transform-box: fill-box; transform-origin: center; animation: epaPop .4s ease-out forwards; }}
.epa-courbe circle:hover {{ r: 5; }}
.epa-legende {{ display:flex; flex-wrap:wrap; gap:.4rem 1.1rem; font-size:.82rem; margin:.4rem 0 .2rem; }}
.epa-legende span {{ display:inline-flex; align-items:center; gap:.4rem; }}
.epa-legende i {{ display:inline-block; width:18px; height:3px; border-radius:2px; }}
.epa-indices {{ display:grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 1rem; margin-top: 1.2rem; }}
.epa-indice {{ padding: 1.2rem 1.3rem; }}
.epa-indice .code {{ font-family: var(--serif); font-size: 2.2rem; line-height: 1; color: var(--clair); }}
.epa-indice .nom {{ font-size: .85rem; color: rgba(244,236,223,.78); margin: .2rem 0 .7rem; }}
.epa-indice .f {{ font-family: ui-monospace, monospace; font-size: .8rem; background: rgba(0,0,0,.22); border-radius: 8px; padding: .35rem .6rem;
  display: inline-block; margin-bottom: .6rem; }}
.epa-indice p {{ margin: .25rem 0; font-size: .88rem; line-height: 1.5; color: rgba(244,236,223,.9); }}
.epa-indice .ref {{ font-size: .72rem; color: rgba(244,236,223,.62); margin-top: .5rem; }}
.epa-gamme {{ height: 8px; border-radius: 4px; margin: .7rem 0 .2rem; transform-origin: left; animation: epaGrow 1.4s cubic-bezier(.2,.7,.2,1) both .3s; }}
.epa-gamme-l {{ display:flex; justify-content:space-between; font-size:.7rem; color: rgba(244,236,223,.7); }}
@media (max-width: 900px) {{ .epa-indices {{ grid-template-columns: minmax(0,1fr); }} }}
@media (max-width: 900px) {{ .epa-rings {{ grid-template-columns: minmax(0,1fr); }} .epa-frise {{ grid-template-columns: minmax(0,1fr) minmax(0,1fr); }}
  .epa-hero h1, .epa-hero.grand h1 {{ font-size: 3rem !important; }} .epa-bar {{ grid-template-columns: 120px minmax(0,1fr) 64px; }} }}
@media (prefers-reduced-motion: reduce) {{ *, *::before {{ animation: none !important; transition: none !important; }} }}
</style>
"""


# ---------------------------------------------------------------------------
# Images du territoire (photo aérienne et gravure du parcellaire), servies en fichiers statiques
# ---------------------------------------------------------------------------

def gravure(img: Image.Image, nuit: bool = False) -> Image.Image:
    """Trace les limites de parcelles d'une photo aérienne en gravure fine (claire ou nuit)."""
    g = img.convert("L")
    e = ImageOps.autocontrast(g.filter(ImageFilter.GaussianBlur(1.2)).filter(ImageFilter.FIND_EDGES), cutoff=2)
    mask = e.point(lambda v: 255 if v > 70 else int(v * v / 4900 * 153)).filter(ImageFilter.GaussianBlur(0.6))
    fond, encre, k = ((24, 33, 26), (220, 229, 188), 0.42) if nuit else ((236, 238, 228), (86, 101, 62), 0.55)
    return Image.composite(Image.new("RGB", g.size, encre), Image.new("RGB", g.size, fond), mask.point(lambda v: int(v * k)))


def photo_territoire(communes, largeur: int = 1800) -> str | None:
    """URL statique d'une photo aérienne IGN couvrant le territoire (None si le service ne répond pas)."""
    from .cartes import _wms_image
    from .figures import ORTHO

    c = communes.to_crs(3857)
    minx, miny, maxx, maxy = c.total_bounds
    cx, cy, w = (minx + maxx) / 2, (miny + maxy) / 2, max(maxx - minx, (maxy - miny) * 2.2) * 1.05
    bbox = (cx - w / 2, cy - w / 4.4, cx + w / 2, cy + w / 4.4)
    cle = hashlib.sha1(repr(tuple(round(v) for v in bbox)).encode()).hexdigest()[:14]
    f = GEN / f"ortho_{cle}.jpg"
    if not f.exists():
        try:
            img = Image.open(io.BytesIO(_wms_image(ORTHO, bbox, largeur, int(largeur / 2.2)))).convert("RGB")
            GEN.mkdir(parents=True, exist_ok=True)
            img.save(f, quality=74, optimize=True, progressive=True)
        except Exception:  # service indisponible ou dossier non inscriptible : en-tête sans photo
            return None
    return f"{URL}/gen/{f.name}"


# ---------------------------------------------------------------------------
# Composants HTML
# ---------------------------------------------------------------------------

def titre_html(titre: str, italique: str = "") -> str:
    return html.escape(titre) + (f" <em>{html.escape(italique)}</em>" if italique else "")


def hero(etape: str | None, titre: str, italique: str = "", intro: str = "", photo: str | None = None,
         credit: str = "", grand: bool = False) -> str:
    ph = f'<img class="ph" src="{photo}" alt="">' if photo else ""
    et = f'<div class="et">{html.escape(etape)}</div>' if etape else ""
    p = f"<p>{intro}</p>" if intro else ""
    cr = f'<div class="credit">{html.escape(credit)}</div>' if credit and photo else ""
    return (f'<div class="epa-hero{" grand" if grand else ""}">{ph}<div class="voile"></div><div class="in">{et}'
            f'<h1>{titre_html(titre, italique)}</h1>{p}{cr}</div></div>')


def tete(etape: str | None, titre: str, italique: str = "", intro: str = "") -> str:
    et = f'<div class="et">{html.escape(etape)}</div>' if etape else ""
    p = f"<p>{intro}</p>" if intro else ""
    return f'<div class="epa-head">{et}<h1>{titre_html(titre, italique)}</h1>{p}</div>'


def ornement() -> str:
    return f'<div class="epa-orn">{ETOILE}<span></span></div>'


def anneaux(echelles: list[dict], sel: int) -> str:
    """Quatre cercles emboîtés (périmètre au centre, France à l'extérieur) ; `sel` = 0..3 mis en avant.

    echelles : [{label, nom, valeur, evol}] du périmètre à la France.
    """
    rayons = [44, 92, 140, 188]
    cercles = []
    for i in range(3, -1, -1):
        on = i == sel
        fill = "rgba(220,229,188,.16)" if on else "rgba(244,236,223,.04)"
        stroke, sw = ("#DCE5BC", 2) if on else ("rgba(244,236,223,.5)", 1.2)
        cercles.append(f'<circle cx="210" cy="210" r="{rayons[i]}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
    labels = "".join(f'<text x="210" y="{210 - rayons[i] + 18}" text-anchor="middle" fill="rgba(244,236,223,.9)" '
                     f'font-family="Inter" font-size="12">{html.escape(echelles[i]["label"])}</text>' for i in (3, 2, 1))
    cur = echelles[sel]
    svg = (f'<svg viewBox="0 0 420 420" width="100%" role="img" aria-label="Quatre échelles emboîtées : périmètre, département, région, France">'
           f'<g class="spin"><circle cx="210" cy="210" r="204" fill="none" stroke="rgba(244,236,223,.14)" stroke-dasharray="2 7"/>'
           f'<path d="M210 0C211.4 4 212 4.6 216 6 212 7.4 211.4 8 210 12 208.6 8 208 7.4 204 6 208 4.6 208.6 4 210 0Z" fill="#DCE5BC"/></g>'
           f'{"".join(cercles)}{labels}'
           f'<text x="210" y="212" text-anchor="middle" fill="#F4ECDF" font-family="Cormorant Garamond" font-size="30">{html.escape(cur["valeur"])}</text>'
           f'<text x="210" y="232" text-anchor="middle" fill="rgba(244,236,223,.8)" font-family="Inter" font-size="10.5">{html.escape(cur["label"].lower())}</text></svg>')
    lignes = "".join(
        f'<div class="epa-scale{" on" if i == sel else ""}"><span class="n">{i + 1}</span>'
        f'<span><span class="lab">{html.escape(e["label"])}</span><br><span class="nom">{html.escape(e["nom"])}</span></span>'
        f'<span><div class="val">{html.escape(e["valeur"])}</div><div class="ev">{html.escape(e["evol"])}</div></span></div>'
        for i, e in enumerate(echelles))
    return f'<div class="epa-rings"><div>{svg}</div><div>{lignes}</div></div>'


def barres(lignes: list[dict], accent: str) -> str:
    """Barres horizontales HTML (valeurs signées), la première ligne mise en avant. lignes : [{nom, valeur(float|None)}]."""
    vals = [abs(l["valeur"]) for l in lignes if l["valeur"] is not None]
    m = max(vals) if vals else 1
    out = []
    for i, l in enumerate(lignes):
        v = l["valeur"]
        txt = "non disponible" if v is None else (("+" if v > 0 else "−" if v < 0 else "") + f"{abs(v):.1f}".replace(".", ",") + " %")
        w = 0 if v is None else abs(v) / m * 100
        col = accent if i == 0 else "#A3A895"
        fw = 600 if i == 0 else 400
        out.append(f'<div class="epa-bar"><span style="font-weight:{fw}">{html.escape(l["nom"])}</span>'
                   f'<span class="track"><span class="fill" style="display:block;width:{w:.1f}%;background:{col};animation-delay:{i * .12:.2f}s"></span></span>'
                   f'<span class="v">{txt}</span></div>')
    return f'<div class="epa-bars">{"".join(out)}</div>'


def frise(etapes: list[tuple[str, str, str]]) -> str:
    items = "".join(f'<li><div class="num">{html.escape(n)}</div>{ETOILE.replace("12", "16")}<b>{html.escape(t)}</b>'
                    f'<span>{html.escape(d)}</span></li>' for n, t, d in etapes)
    return f'<ol class="epa-frise">{items}</ol>'


GAMMES = {"NDVI": "linear-gradient(90deg,#8A7A5C,#F4ECDF 18%,#DCE5BC 45%,#56653E 75%,#1F3A1A)",
          "BSI": "linear-gradient(90deg,#1F3A1A,#56653E 35%,#F4ECDF 60%,#C9A26B 80%,#8A5A2B)",
          "NDMI": "linear-gradient(90deg,#8A5A2B,#F4ECDF 45%,#86B6EF 75%,#1C5CAB)",
          "MNDWI": "linear-gradient(90deg,#56653E,#F4ECDF 55%,#6DA7EC 80%,#184F95)"}


def carte_indice(ind) -> str:
    """Carte explicative d'un indice : ce qu'il montre, formule Sentinel-2, lecture, limites, référence, gamme animée."""
    e = html.escape
    return (f'<div class="epa-glass epa-indice"><div class="code">{e(ind.code)}</div><div class="nom">{e(ind.nom)}</div>'
            f'<span class="f">{e(ind.bandes)}</span><p><b>Ce qu\'il montre.</b> {e(ind.montre)}</p><p><b>Comment le lire.</b> {e(ind.lecture)}</p>'
            f'<p><b>Limites.</b> {e(ind.limites)}</p><div class="epa-gamme" style="background:{GAMMES.get(ind.code, "#DCE5BC")}"></div>'
            f'<div class="epa-gamme-l"><span>{ind.vmin:+.1f}</span><span>{ind.vmax:+.1f}</span></div>'
            f'<div class="ref">{e(ind.reference)}</div></div>')


def courbes(series: dict, couleurs: list[str], vmin: float, vmax: float, reference: list | None = None,
            ref_label: str = "", largeur: int = 980, hauteur: int = 280) -> str:
    """Courbes SVG qui se tracent à l'affichage ; survol d'un point : date et valeur. series : {nom: [(date, valeur)]}."""
    import pandas as pd

    pts = [d for v in series.values() for d, _ in v] + [d for d, _ in (reference or [])]
    if not pts:
        return ""
    d0, d1 = pd.Timestamp(min(pts)), pd.Timestamp(max(pts))
    span = max((d1 - d0).days, 1)
    g, dr, hb = 44, 14, 26
    X = lambda d: g + (pd.Timestamp(d) - d0).days / span * (largeur - g - dr)  # noqa: E731
    Y = lambda v: 10 + (vmax - v) / (vmax - vmin) * (hauteur - 10 - hb)  # noqa: E731
    out = [f'<svg class="epa-courbe" viewBox="0 0 {largeur} {hauteur}" width="100%" role="img" aria-label="Évolution de l\'indice par parcelle">']
    for k in range(5):  # grille légère
        v = vmin + (vmax - vmin) * k / 4
        out.append(f'<line x1="{g}" x2="{largeur - dr}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="rgba(31,42,34,.08)"/>'
                   f'<text x="{g - 6}" y="{Y(v) + 4:.1f}" text-anchor="end" font-size="10" fill="#4F5649">{v:.1f}</text>')
    if vmin < 0 < vmax:
        out.append(f'<line x1="{g}" x2="{largeur - dr}" y1="{Y(0):.1f}" y2="{Y(0):.1f}" stroke="rgba(31,42,34,.35)"/>')
    m = pd.date_range(d0.normalize(), d1, freq="MS")  # premiers jours de mois à l'intérieur de la période
    for d in m[:: max(1, len(m) // 12)]:
        out.append(f'<text x="{X(d):.1f}" y="{hauteur - 8}" text-anchor="middle" font-size="10" fill="#4F5649">{MOIS_COURT[d.month - 1]} {str(d.year)[2:]}</text>')
    if reference:
        p = " ".join(f"{'M' if i == 0 else 'L'}{X(d):.1f},{Y(v):.1f}" for i, (d, v) in enumerate(reference))
        out.append(f'<path class="ref" d="{p}" stroke="#8C9180"/>')
    for i, (nom, v) in enumerate(series.items()):
        if not v:
            continue
        c = couleurs[i % len(couleurs)]
        p = " ".join(f"{'M' if j == 0 else 'L'}{X(d):.1f},{Y(val):.1f}" for j, (d, val) in enumerate(v))
        out.append(f'<path class="l" pathLength="1" d="{p}" stroke="{c}" style="animation-delay:{i * .25:.2f}s"/>')
        for j, (d, val) in enumerate(v):
            out.append(f'<circle cx="{X(d):.1f}" cy="{Y(val):.1f}" r="2.6" fill="{c}" style="animation-delay:{1.6 + i * .25 + j * .01:.2f}s">'
                       f'<title>{html.escape(nom)} – {pd.Timestamp(d).strftime("%d/%m/%Y")} : {val:.2f}</title></circle>')
    out.append("</svg>")
    leg = "".join(f'<span><i style="background:{couleurs[i % len(couleurs)]}"></i>{html.escape(n)}</span>' for i, n in enumerate(series))
    if reference:
        leg += f'<span><i style="background:repeating-linear-gradient(90deg,#8C9180 0 4px,transparent 4px 8px)"></i>{html.escape(ref_label)}</span>'
    return "".join(out) + f'<div class="epa-legende">{leg}</div>'


MOIS_COURT = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]
