"""Diapositives PowerPoint dans le style validé (nuit, photo aérienne, titres à empattements, panneaux translucides).

`build_pptx(ctx, branding, gabarit)` : si le bureau d'études fournit son gabarit (.pptx), ses masques et dispositions sont
utilisés ; sinon un format 16:9 est créé. Les valeurs viennent du contexte calculé par l'application : rien n'est saisi.
"""
from __future__ import annotations

import io
from datetime import date
from pathlib import Path

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Pt

NUIT, CREME, CLAIR, OLIVE, TEXTE, SECOND = "18211A", "F4ECDF", "DCE5BC", "56653E", "1F2A22", "4F5649"
W, H = Emu(12192000), Emu(6858000)  # 16:9


def _rgb(h: str) -> RGBColor:
    return RGBColor.from_string(h.lstrip("#").upper())


def _fond(slide, couleur: str) -> None:
    f = slide.background.fill
    f.solid()
    f.fore_color.rgb = _rgb(couleur)


def _texte(slide, x, y, w, h, txt, taille, couleur, police, gras=False, italique=False, align=PP_ALIGN.LEFT):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    r = p.add_run()
    r.text = txt
    r.font.size, r.font.bold, r.font.italic, r.font.name = Pt(taille), gras, italique, police
    r.font.color.rgb = _rgb(couleur)
    return tb


def _panneau(slide, x, y, w, h, couleur: str = CREME, transparence: int = 88):
    """Rectangle arrondi translucide (transparence en %)."""
    s = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
    s.adjustments[0] = 0.12
    s.fill.solid()
    s.fill.fore_color.rgb = _rgb(couleur)
    srgb = s.fill._xPr.find(".//{http://schemas.openxmlformats.org/drawingml/2006/main}srgbClr")
    alpha = etree.SubElement(srgb, "{http://schemas.openxmlformats.org/drawingml/2006/main}alpha")
    alpha.set("val", str(int((100 - transparence) * 1000)))
    s.line.color.rgb = _rgb(CREME)
    s.line.width = Pt(0.5)
    s.shadow.inherit = False
    return s


def _cadre(slide, bureau: str, numero: int, police: str) -> None:
    _texte(slide, Emu(500000), Emu(260000), Emu(6000000), Emu(300000), bureau, 10, CREME, police)
    ln = slide.shapes.add_connector(1, Emu(3200000), Emu(400000), Emu(11300000), Emu(400000))
    ln.line.color.rgb = _rgb(CREME)
    ln.line.width = Pt(0.5)
    _texte(slide, Emu(11300000), Emu(6400000), Emu(500000), Emu(300000), str(numero), 10, CREME, police, align=PP_ALIGN.RIGHT)


def _source(slide, txt: str, police: str, couleur: str = CREME) -> None:
    _texte(slide, Emu(500000), Emu(6400000), Emu(10500000), Emu(300000), f"Source : {txt}", 9, couleur, police)


def _nouvelle(prs):
    layout = prs.slide_layouts[6] if len(prs.slide_layouts) > 6 else prs.slide_layouts[-1]
    return prs.slides.add_slide(layout)


def build_pptx(ctx: dict, bureau: str, accent: str, police_titres: str = "Georgia", police_texte: str = "Calibri",
               gabarit: bytes | None = None) -> bytes:
    """ctx : titre, territoire, photo (chemin), echelles [{label, nom, exp, evol_exp, sau, evol_sau}], phrases [str],
    figures [(titre, png, source)], bibliographie [str]."""
    prs = Presentation(io.BytesIO(gabarit)) if gabarit else Presentation()
    if not gabarit:
        prs.slide_width, prs.slide_height = W, H
    W_, H_ = prs.slide_width, prs.slide_height
    n = 0

    # 1. Couverture
    s = _nouvelle(prs)
    n += 1
    _fond(s, NUIT)
    photo = ctx.get("photo")
    if photo and Path(photo).exists():
        s.shapes.add_picture(str(photo), int(W_ * 0.5), 0, int(W_ * 0.5), H_)
    _texte(s, Emu(600000), Emu(1700000), Emu(5600000), Emu(900000), "Étude préalable", 54, CREME, police_titres)
    _texte(s, Emu(600000), Emu(2550000), Emu(5600000), Emu(900000), "agricole", 54, CLAIR, police_titres, italique=True)
    _texte(s, Emu(600000), Emu(3700000), Emu(5400000), Emu(800000), ctx.get("titre") or "", 18, CREME, police_texte)
    _texte(s, Emu(600000), Emu(4200000), Emu(5400000), Emu(800000), ctx.get("territoire") or "", 14, CLAIR, police_texte)
    _texte(s, Emu(600000), Emu(6100000), Emu(5400000), Emu(400000), f"{bureau}, {date.today().strftime('%d/%m/%Y')}", 11, CREME, police_texte)
    if photo and Path(photo).exists():
        _texte(s, int(W_ * 0.5) + Emu(150000), Emu(6450000), Emu(5500000), Emu(300000), "Photographie aérienne : IGN, Géoplateforme", 8, CREME, police_texte)

    # 2. Chiffres clés à quatre échelles
    ech = ctx.get("echelles") or []
    if ech:
        s = _nouvelle(prs)
        n += 1
        _fond(s, NUIT)
        _cadre(s, bureau, n, police_texte)
        _texte(s, Emu(600000), Emu(700000), Emu(9000000), Emu(800000), "Chiffres clés,", 40, CREME, police_titres)
        _texte(s, Emu(600000), Emu(1350000), Emu(9000000), Emu(800000), "quatre échelles", 40, CLAIR, police_titres, italique=True)
        larg = Emu(2650000)
        for i, e in enumerate(ech[:4]):
            x = Emu(600000) + i * (larg + Emu(150000))
            _panneau(s, x, Emu(2450000), larg, Emu(2300000))
            _texte(s, x + Emu(150000), Emu(2550000), larg - Emu(300000), Emu(300000), e["label"], 11, CLAIR, police_texte)
            _texte(s, x + Emu(150000), Emu(2850000), larg - Emu(300000), Emu(500000), e["nom"], 12, CREME, police_texte, gras=True)
            _texte(s, x + Emu(150000), Emu(3350000), larg - Emu(300000), Emu(700000), e["exp"], 34, CREME, police_titres)
            _texte(s, x + Emu(150000), Emu(4000000), larg - Emu(300000), Emu(300000), f"exploitations, {e['evol_exp']}", 10, CREME, police_texte)
            _texte(s, x + Emu(150000), Emu(4300000), larg - Emu(300000), Emu(300000), f"SAU {e['sau']}, {e['evol_sau']}", 10, CREME, police_texte)
        y = Emu(5000000)
        for ph in (ctx.get("phrases") or [])[:2]:
            _texte(s, Emu(600000), y, Emu(10900000), Emu(600000), ph, 14, CREME, police_titres)
            y += Emu(620000)
        _source(s, "Agreste, recensements agricoles 2010 et 2020, via l'Observatoire des territoires ; France : somme des départements.", police_texte)

    # 3. Figures (fond crème, sobre)
    for titre, png, src in ctx.get("figures") or []:
        if not png:
            continue
        s = _nouvelle(prs)
        n += 1
        _fond(s, CREME)
        _texte(s, Emu(500000), Emu(250000), Emu(9000000), Emu(600000), titre, 28, TEXTE, police_titres)
        pic = s.shapes.add_picture(io.BytesIO(png), Emu(500000), Emu(950000), height=Emu(5300000))
        if pic.width > W_ - Emu(1000000):
            ratio = (W_ - Emu(1000000)) / pic.width
            pic.width, pic.height = int(pic.width * ratio), int(pic.height * ratio)
        _source(s, src, police_texte, SECOND)
        _texte(s, Emu(11300000), Emu(6400000), Emu(500000), Emu(300000), str(n), 10, SECOND, police_texte, align=PP_ALIGN.RIGHT)

    # 4. Sources
    biblio = ctx.get("bibliographie") or []
    if biblio:
        s = _nouvelle(prs)
        n += 1
        _fond(s, NUIT)
        _cadre(s, bureau, n, police_texte)
        _texte(s, Emu(600000), Emu(700000), Emu(9000000), Emu(800000), "Sources", 40, CREME, police_titres)
        tb = s.shapes.add_textbox(Emu(600000), Emu(1600000), Emu(10900000), Emu(4600000))
        tf = tb.text_frame
        tf.word_wrap = True
        for i, ref in enumerate(biblio[:14]):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            r = p.add_run()
            r.text = ref
            r.font.size, r.font.name = Pt(10), police_texte
            r.font.color.rgb = _rgb(CREME)
    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()
