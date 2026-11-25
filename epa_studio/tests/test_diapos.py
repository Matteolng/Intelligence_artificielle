"""Export PowerPoint : fichier valide, contenu issu du contexte, gabarit du bureau pris en compte."""
import io

from pptx import Presentation

from epa.diapos import build_pptx

CTX = {"titre": "Projet test", "territoire": "CC Test", "echelles": [
    {"label": l, "nom": l, "exp": "1", "evol_exp": "−1,0 %", "sau": "10 ha", "evol_sau": "+1,0 %"} for l in ("Périmètre", "Département", "Région", "France")],
    "phrases": ["Le nombre d'exploitations recule de 1,0 %."], "figures": [], "bibliographie": ["Agreste (2020). RA. URL."]}


def _textes(data):
    prs = Presentation(io.BytesIO(data))
    return prs, [sh.text_frame.text for sl in prs.slides for sh in sl.shapes if sh.has_text_frame]


def test_pptx_contenu():
    prs, txt = _textes(build_pptx(CTX, "Bureau Test", "#56653E"))
    assert len(prs.slides) == 3 and "Bureau Test" in " ".join(txt) and "Le nombre d'exploitations recule de 1,0 %." in txt
    assert round(prs.slide_width / prs.slide_height, 2) == 1.78


def test_pptx_gabarit():
    tpl = Presentation()
    tpl.slide_width, tpl.slide_height = 9144000, 6858000  # gabarit 4:3 du bureau
    b = io.BytesIO()
    tpl.save(b)
    prs, _ = _textes(build_pptx(CTX, "B", "#56653E", gabarit=b.getvalue()))
    assert prs.slide_width == 9144000
