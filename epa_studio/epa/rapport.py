"""Génération du rapport (DOCX) et des exports tabulaires (XLSX).

Le plan suit l'article D. 112-1-19 du code rural et de la pêche maritime.
Le document produit est une base de travail : il doit être relu, complété
(enquêtes, entretiens, analyse experte) et validé par le chargé d'études.
"""
from __future__ import annotations

import io
from datetime import date

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from docx import Document  # noqa: E402
from docx.enum.section import WD_ORIENT  # noqa: E402
from docx.enum.table import WD_TABLE_ALIGNMENT  # noqa: E402
from docx.enum.text import WD_ALIGN_PARAGRAPH  # noqa: E402
from docx.oxml import OxmlElement  # noqa: E402
from docx.oxml.ns import qn  # noqa: E402
from docx.shared import Cm, Pt, RGBColor  # noqa: E402

from . import analyse  # noqa: E402
from .config import APP_NAME, APP_VERSION  # noqa: E402
from .reglementation import REFERENTIEL, SOURCES_DONNEES  # noqa: E402

VERT = RGBColor(0x1F, 0x5F, 0x3F)
GRIS = RGBColor(0x5F, 0x6B, 0x66)


# ---------------------------------------------------------------------------
# Graphiques
# ---------------------------------------------------------------------------

def graph_barres(df: pd.DataFrame, x: str, y: str, titre: str, xlabel: str, color: str = "#1F5F3F",
                 colors: list[str] | None = None, top: int = 12) -> bytes:
    d = df.head(top).iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, max(2.5, 0.38 * len(d) + 1)))
    ax.barh(d[x].astype(str), d[y], color=colors[::-1] if colors else color)
    ax.set_xlabel(xlabel)
    ax.set_title(titre, loc="left", fontsize=12, fontweight="bold")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="x", alpha=0.3)
    for i, v in enumerate(d[y]):
        ax.text(v, i, " " + analyse.fnum(v, 0), va="center", fontsize=8)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=160)
    plt.close(fig)
    return buf.getvalue()


def graph_ligne(df: pd.DataFrame, x: str, y: str, titre: str, ylabel: str) -> bytes:
    fig, ax = plt.subplots(figsize=(8, 3.4))
    ax.plot(df[x], df[y], marker="o", color="#1F5F3F")
    ax.set_ylabel(ylabel)
    ax.set_title(titre, loc="left", fontsize=12, fontweight="bold")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=160)
    plt.close(fig)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Helpers DOCX
# ---------------------------------------------------------------------------

def _shade(cell, hex_color: str) -> None:
    tcPr = cell._element.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def _fmt(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float):
        if pd.isna(v):
            return "n.d."
        return analyse.fnum(v, 1 if abs(v) < 100 else 0)
    if isinstance(v, (int,)) and not isinstance(v, bool):
        return analyse.fnum(v)
    try:
        import numpy as np

        if isinstance(v, np.integer):
            return analyse.fnum(int(v))
        if isinstance(v, np.floating):
            return _fmt(float(v))
    except Exception:
        pass
    return str(v)


def add_table(doc: Document, df: pd.DataFrame, max_rows: int = 60, font_size: int = 8, col_widths: list[float] | None = None) -> None:
    if df is None or df.empty:
        doc.add_paragraph("Aucune donnée.", style="Normal")
        return
    d = df.head(max_rows)
    table = doc.add_table(rows=1, cols=len(d.columns))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for j, c in enumerate(d.columns):
        cell = table.rows[0].cells[j]
        cell.text = str(c)
        _shade(cell, "1F5F3F")
        for p in cell.paragraphs:
            for r in p.runs:
                r.font.bold = True
                r.font.size = Pt(font_size)
                r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    for i, (_, row) in enumerate(d.iterrows()):
        cells = table.add_row().cells
        for j, c in enumerate(d.columns):
            cells[j].text = _fmt(row[c])
            if i % 2 == 1:
                _shade(cells[j], "EEF4EF")
            for p in cells[j].paragraphs:
                for r in p.runs:
                    r.font.size = Pt(font_size)
    if col_widths:
        for row in table.rows:
            for j, w in enumerate(col_widths):
                row.cells[j].width = Cm(w)
    if len(df) > max_rows:
        doc.add_paragraph(f"(Tableau tronqué : {max_rows} lignes sur {len(df)} – voir l'export Excel.)").runs[0].font.size = Pt(8)


def add_source(doc: Document, txt: str) -> None:
    p = doc.add_paragraph()
    r = p.add_run("Source : " + txt)
    r.italic = True
    r.font.size = Pt(8)
    r.font.color.rgb = GRIS


def add_image(doc: Document, png: bytes | None, width_cm: float = 16) -> None:
    if png:
        doc.add_picture(io.BytesIO(png), width=Cm(width_cm))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER


def add_text(doc: Document, txt: str, italic: bool = False) -> None:
    if not txt:
        return
    p = doc.add_paragraph()
    r = p.add_run(txt)
    r.italic = italic


def add_a_completer(doc: Document, txt: str) -> None:
    p = doc.add_paragraph()
    r = p.add_run("[À compléter par le chargé d'études] " + txt)
    r.font.color.rgb = RGBColor(0xC0, 0x39, 0x2B)
    r.italic = True


def _styles(doc: Document) -> None:
    st = doc.styles["Normal"]
    st.font.name = "Calibri"
    st.font.size = Pt(10)
    for lvl, size in ((1, 16), (2, 13), (3, 11)):
        h = doc.styles[f"Heading {lvl}"]
        h.font.name = "Calibri"
        h.font.size = Pt(size)
        h.font.color.rgb = VERT
    sec = doc.sections[0]
    sec.orientation = WD_ORIENT.PORTRAIT
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)  # A4
    sec.left_margin = sec.right_margin = Cm(2)
    sec.top_margin = sec.bottom_margin = Cm(2)


# ---------------------------------------------------------------------------
# Rapport
# ---------------------------------------------------------------------------

def _document(gabarit: bytes | None) -> Document:
    """Document vierge, ou gabarit Word du bureau d'études (styles, en-têtes et pieds conservés, contenu retiré)."""
    if not gabarit:
        doc = Document()
        _styles(doc)
        return doc
    doc = Document(io.BytesIO(gabarit))
    body = doc.element.body
    for el in list(body):
        if not el.tag.endswith("sectPr"):
            body.remove(el)
    return doc


def build_docx(ctx: dict, gabarit: bytes | None = None) -> bytes:
    """ctx : dictionnaire des résultats (cf. app_pages/rapport.py). `gabarit` : .docx du bureau d'études (facultatif)."""
    doc = _document(gabarit)
    projet = ctx.get("projet") or {}
    terr = ctx.get("territoire_resume") or {}

    # --- Page de garde
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r = t.add_run("ÉTUDE PRÉALABLE AGRICOLE")
    r.bold = True
    r.font.size = Pt(26)
    r.font.color.rgb = VERT
    sub = doc.add_paragraph()
    rs = sub.add_run("Articles L. 112-1-3 et D. 112-1-18 à D. 112-1-22 du code rural et de la pêche maritime")
    rs.font.size = Pt(11)
    rs.font.color.rgb = GRIS
    doc.add_paragraph()
    p = doc.add_paragraph()
    rp = p.add_run(projet.get("nom") or "Projet")
    rp.bold = True
    rp.font.size = Pt(18)
    for k, v in (("Maître d'ouvrage", projet.get("maitre_ouvrage")), ("Type de projet", projet.get("type_projet")),
                 ("Territoire d'étude", terr.get("Nom")), ("Date d'édition", date.today().strftime("%d/%m/%Y"))):
        if v:
            q = doc.add_paragraph()
            q.add_run(f"{k} : ").bold = True
            q.add_run(str(v))
    doc.add_paragraph()
    add_text(doc, f"Document de travail généré par {APP_NAME} v{APP_VERSION} à partir de données publiques ouvertes. "
                  "Les tableaux, cartes et synthèses automatiques doivent être vérifiés, complétés par les enquêtes de terrain "
                  "et les entretiens, et validés par le chargé d'études avant transmission au préfet.", italic=True)
    if not (ctx.get("compensation") or {}).get("parametres", {}).get("parametres_valides", True):
        add_a_completer(doc, "Les paramètres de calcul de la compensation n'ont pas été validés au regard de la doctrine départementale.")
    doc.add_page_break()

    # --- Sommaire simplifié
    doc.add_heading("Sommaire", level=1)
    for s in ("1. Description du projet et délimitation du territoire concerné",
              "2. Analyse de l'état initial de l'économie agricole du territoire",
              "3. Effets positifs et négatifs du projet sur l'économie agricole",
              "4. Mesures d'évitement et de réduction",
              "5. Mesures de compensation collective",
              "Annexes : sources, référentiel réglementaire, limites"):
        doc.add_paragraph(s, style="Normal")
    doc.add_page_break()

    # --- 1. Projet & territoire
    doc.add_heading("1. Description du projet et délimitation du territoire concerné", level=1)
    doc.add_heading("1.1 Le projet", level=2)
    if projet:
        lignes = [(k, v) for k, v in (
            ("Nom du projet", projet.get("nom")), ("Maître d'ouvrage", projet.get("maitre_ouvrage")),
            ("Type de projet", projet.get("type_projet")), ("Puissance (MWc)", projet.get("puissance_mwc")),
            ("Technologie", projet.get("technologie")), ("Taux de couverture (%)", projet.get("taux_couverture_pct")),
            ("Hauteur minimale des modules (m)", projet.get("hauteur_min_m")),
            ("Durée d'exploitation (ans)", projet.get("duree_exploitation_ans")),
            ("Production agricole prévue", projet.get("production_agricole_prevue")),
            ("Exploitant agricole", projet.get("exploitant_agricole")),
            ("Services agrivoltaïques revendiqués", ", ".join(projet.get("services") or [])),
            ("Zone témoin", projet.get("zone_temoin")),
            ("Surface de l'emprise (ha)", ctx.get("surface_emprise_ha")),
            ("Surfaces soustraites (infrastructures, ha)", projet.get("surface_infrastructures_ha")),
        ) if v not in (None, "", [])]
        add_table(doc, pd.DataFrame(lignes, columns=["Caractéristique", "Valeur"]), col_widths=[6, 10])
        add_text(doc, projet.get("description") or "")
    else:
        add_a_completer(doc, "Décrire le projet (nature, calendrier, caractéristiques techniques).")
    if ctx.get("controle_agrivoltaique"):
        doc.add_heading("Points de contrôle agrivoltaïques (décret n° 2024-318)", level=3)
        add_table(doc, pd.DataFrame(ctx["controle_agrivoltaique"], columns=["Critère", "Statut", "Commentaire"]), col_widths=[6, 2.5, 7.5])
        add_source(doc, "art. L. 314-36 et R. 314-108 et s. du code de l'énergie – à vérifier sur Légifrance (texte consolidé).")
    if ctx.get("assujettissement"):
        doc.add_heading("Assujettissement à l'étude préalable", level=3)
        verdict, notes = ctx["assujettissement"]
        add_text(doc, verdict)
        for n in notes:
            doc.add_paragraph(n, style="List Bullet")

    doc.add_heading("1.2 Délimitation du territoire concerné", level=2)
    if terr:
        add_text(doc, analyse.texte_territoire(terr))
        add_table(doc, pd.DataFrame(list(terr.items()), columns=["Élément", "Valeur"]), col_widths=[7, 9])
    add_image(doc, ctx.get("carte_localisation"))
    if ctx.get("carte_localisation"):
        add_source(doc, "API Découpage administratif ; fond Plan IGN (Géoplateforme).")
    add_a_completer(doc, "Justifier le périmètre retenu (bassins de production, aires d'approvisionnement des filières, "
                         "aires des SIQO, cohérence avec la doctrine départementale).")
    if ctx.get("communes_table") is not None:
        doc.add_heading("Communes du territoire d'étude", level=3)
        add_table(doc, ctx["communes_table"], max_rows=200)

    # --- 2. État initial
    doc.add_page_break()
    doc.add_heading("2. Analyse de l'état initial de l'économie agricole", level=1)

    doc.add_heading("2.1 Structures des exploitations (recensement agricole 2020)", level=2)
    if ctx.get("ra2020_synthese"):
        add_text(doc, analyse.texte_ra2020(ctx["ra2020_synthese"]))
        add_table(doc, pd.DataFrame(ctx["ra2020_synthese"]))
        add_source(doc, "Agreste – recensement agricole 2020, via l'Observatoire des territoires (ANCT).")
        add_image(doc, ctx.get("carte_ra2020"))
    else:
        add_a_completer(doc, "Module « Exploitations (RA 2020) » non calculé.")
    if ctx.get("ra2020_import") is not None:
        doc.add_heading("Indicateurs complémentaires importés (Cartostat / DISAR)", level=3)
        add_table(doc, ctx["ra2020_import"], max_rows=80)
        add_source(doc, ctx.get("ra2020_import_source") or "fichier importé par l'utilisateur.")
    if ctx.get("naf_production") is not None and not ctx["naf_production"].empty:
        doc.add_heading("Orientations de production (établissements agricoles inscrits au répertoire SIRENE)", level=3)
        add_table(doc, ctx["naf_production"][["naf", "libelle", "unites_legales_actives", "part_pct"]]
                  .rename(columns={"naf": "NAF", "libelle": "Activité", "unites_legales_actives": "Unités légales actives", "part_pct": "Part (%)"}))
        add_source(doc, "INSEE – SIRENE via l'API Recherche d'entreprises (unités légales actives par code NAF, division 01). "
                        "Indicateur complémentaire : le code NAF déclaré ne correspond pas toujours à l'OTEX.")

    doc.add_heading("2.2 Occupation agricole du sol (RPG)", level=2)
    if ctx.get("rpg_indicateurs"):
        add_text(doc, analyse.texte_rpg(ctx["rpg_indicateurs"], ctx["rpg_assolement"], ctx.get("rpg_annee", ""), terr.get("Surface (ha)")))
        asso = ctx["rpg_assolement"].rename(columns={"groupe": "Groupe de cultures", "surface_ha": "Surface (ha)", "nb_parcelles": "Parcelles", "part_pct": "Part (%)"})
        add_table(doc, asso)
        add_source(doc, f"RPG {ctx.get('rpg_annee', '')} – IGN / ASP (Géoplateforme).")
        add_image(doc, ctx.get("graph_assolement"))
        add_image(doc, ctx.get("carte_rpg"))
        if ctx.get("rpg_cultures") is not None:
            doc.add_heading("Principales cultures déclarées", level=3)
            add_table(doc, ctx["rpg_cultures"].rename(columns={"culture": "Culture", "surface_ha": "Surface (ha)", "nb_parcelles": "Parcelles", "part_pct": "Part (%)"}), max_rows=25)
    else:
        add_a_completer(doc, "Module « Occupation agricole (RPG) » non calculé.")

    doc.add_heading("2.3 Signes officiels de qualité et agriculture biologique", level=2)
    if ctx.get("siqo") is not None:
        add_text(doc, analyse.texte_siqo(ctx["siqo"]))
        if not ctx["siqo"].empty:
            add_table(doc, ctx["siqo"][["aire", "famille", "signes", "communes_concernees", "part_communes_pct"]]
                      .rename(columns={"aire": "Aire géographique", "famille": "Famille", "signes": "Signe(s)", "communes_concernees": "Communes", "part_communes_pct": "Part des communes (%)"}))
        add_source(doc, "INAO – aires géographiques des AOC/AOP et IGP/IG par commune (data.gouv.fr).")
    if ctx.get("bio") is not None:
        add_text(doc, analyse.texte_bio(ctx["bio"], (ctx.get("ra2020_synthese") or [{}])[0].get("Exploitations 2020")))
        if ctx.get("bio_synthese") is not None:
            add_table(doc, ctx["bio_synthese"].rename(columns={"activite": "Activité", "operateurs_engages": "Opérateurs engagés"}))
        add_source(doc, "Agence Bio – annuaire des opérateurs (open data).")

    doc.add_heading("2.4 Première transformation et commercialisation", level=2)
    if ctx.get("filieres_synthese") is not None:
        add_text(doc, analyse.texte_filieres(ctx["filieres_synthese"], int(ctx["filieres_synthese"]["etablissements"].sum())))
        add_table(doc, ctx["filieres_synthese"].rename(columns={"categorie": "Catégorie", "etablissements": "Établissements", "effectif_min": "Effectif min.", "effectif_max": "Effectif max.", "employeurs": "Employeurs"}))
        add_source(doc, "INSEE – SIRENE via l'API Recherche d'entreprises (établissements actifs, tranches d'effectifs déclarées).")
        add_image(doc, ctx.get("carte_filieres"))
        if ctx.get("filieres_principales") is not None:
            doc.add_heading("Principaux établissements employeurs", level=3)
            add_table(doc, ctx["filieres_principales"], max_rows=40)
    add_a_completer(doc, "Compléter par les entretiens : coopératives et négoces de collecte, outils d'abattage et de transformation, "
                         "circuits courts, débouchés des exploitations concernées par l'emprise.")

    doc.add_heading("2.5 Foncier agricole", level=2)
    if ctx.get("dvf_stats") is not None:
        add_text(doc, analyse.texte_foncier(ctx["dvf_stats"], ctx.get("dvf_annee_min", 2014), ctx.get("dvf_filtres", "")))
        add_table(doc, ctx["dvf_stats"].rename(columns={"type_bien": "Type de bien", "mutations": "Ventes", "surface_ha": "Surface (ha)", "prix_median_eur_ha": "Prix médian (€/ha)", "prix_q1_eur_ha": "Q1 (€/ha)", "prix_q3_eur_ha": "Q3 (€/ha)", "prix_moyen_pondere_eur_ha": "Prix moyen pondéré (€/ha)"}))
        add_image(doc, ctx.get("graph_dvf"))
        add_source(doc, "DGFiP – DVF, via l'API Données foncières du Cerema. Hors Alsace, Moselle et Mayotte.")
    else:
        add_a_completer(doc, "Module « Foncier (DVF) » non calculé.")

    doc.add_heading("2.6 Contexte environnemental et réglementaire", level=2)
    if ctx.get("couches_consultees"):
        add_text(doc, "Couches cartographiques consultées dans l'atlas : " + ", ".join(ctx["couches_consultees"]) + ".")
    add_a_completer(doc, "Décrire les zonages (PLU, ZAP, PAEN, Natura 2000, ZNIEFF, ZRE…), l'irrigation, la qualité agronomique "
                         "des sols, la présence d'un document-cadre départemental et les autres projets connus (effets cumulés).")

    # --- 3. Effets
    doc.add_page_break()
    doc.add_heading("3. Effets positifs et négatifs du projet sur l'économie agricole", level=1)
    if ctx.get("emprise_comparaison") is not None:
        add_text(doc, analyse.texte_emprise(ctx["emprise_comparaison"], ctx.get("surface_emprise_ha", 0), ctx.get("surface_rpg_emprise_ha", 0), ctx.get("communes_emprise", [])))
        add_table(doc, ctx["emprise_comparaison"].rename(columns={"groupe": "Groupe de cultures", "emprise_ha": "Emprise (ha)", "territoire_ha": "Territoire (ha)", "part_du_territoire_pct": "Part du territoire (%)"}))
        add_source(doc, f"RPG {ctx.get('rpg_annee', '')} croisé avec l'emprise du projet.")
        add_image(doc, ctx.get("carte_emprise"))
    else:
        add_a_completer(doc, "Emprise du projet non renseignée.")
    add_a_completer(doc, "Effets positifs (revenu complémentaire, protection climatique, maintien de l'activité…) et négatifs "
                         "(perte de surface, baisse de rendement, contraintes d'exploitation, effets sur les filières, emploi, "
                         "effets cumulés avec les autres projets connus).")

    # --- 4. ERC
    doc.add_heading("4. Mesures d'évitement et de réduction", level=1)
    if ctx.get("mesures_erc"):
        for m in ctx["mesures_erc"]:
            doc.add_paragraph(m, style="List Bullet")
    else:
        add_a_completer(doc, "Mesures envisagées et retenues pour éviter et réduire les effets négatifs notables du projet.")

    # --- 5. Compensation
    doc.add_heading("5. Mesures de compensation collective", level=1)
    comp = ctx.get("compensation")
    if comp and "erreur" not in comp:
        add_text(doc, analyse.texte_compensation(comp))
        pr = comp["parametres"]
        add_table(doc, pd.DataFrame([
            ("Type de projet", pr["type_projet"]),
            ("Surfaces soustraites à la production (ha)", pr["surface_infrastructures_ha"]),
            ("Taux de perte de production sur la zone agrivoltaïque (%)", pr["taux_perte_zone_agri_pct"]),
            ("Produit brut après projet (€/ha)", pr["pb_apres_projet_eur_ha"]),
            ("Coefficient filières aval", pr["coefficient_aval"]),
            ("Durée de reconstitution (ans)", pr["duree_reconstitution_ans"]),
            ("Ratio d'investissement", pr["ratio_investissement"]),
            ("Paramètres validés (doctrine départementale)", "Oui" if pr["parametres_valides"] else "Non"),
        ], columns=["Paramètre", "Valeur"]), col_widths=[10, 6])
        det = comp["detail"][["groupe", "surface_ha", "pb_eur_ha", "surface_soustraite_ha", "perte_primaire_eur_an"]].rename(columns={
            "groupe": "Groupe de cultures", "surface_ha": "Surface emprise (ha)", "pb_eur_ha": "Produit brut (€/ha)",
            "surface_soustraite_ha": "Surface soustraite (ha)", "perte_primaire_eur_an": "Perte primaire (€/an)"})
        add_table(doc, det)
        res = pd.DataFrame([
            ("Perte de production primaire (€/an)", comp["perte_primaire_eur_an"]),
            ("Perte filières aval (€/an)", comp["perte_aval_eur_an"]),
            ("Impact annuel total (€/an)", comp["impact_annuel_eur"]),
            ("Impact cumulé sur la durée de reconstitution (€)", comp["impact_cumule_eur"]),
            ("Montant de compensation collective (€)", comp["montant_compensation_eur"]),
            ("Emplois concernés (ETP, estimation)", comp.get("etp_concernes")),
        ], columns=["Résultat", "Valeur"])
        add_table(doc, res, col_widths=[10, 6])
        if ctx.get("compensation_sensibilite") is not None:
            doc.add_heading("Analyse de sensibilité (montant en €)", level=3)
            s = ctx["compensation_sensibilite"].reset_index()
            s.columns = [str(c) for c in s.columns]
            add_table(doc, s)
    else:
        add_a_completer(doc, "Calcul de la compensation non réalisé.")
    add_a_completer(doc, "Projets de compensation collective envisagés (outils de transformation, irrigation, installation, "
                         "circuits courts…), coût, porteurs, modalités de mise en œuvre et de suivi.")

    # --- Annexes
    doc.add_page_break()
    doc.add_heading("Annexes", level=1)
    doc.add_heading("A. Sources des données", level=2)
    add_table(doc, pd.DataFrame(SOURCES_DONNEES, columns=["Donnée", "Producteur / diffuseur", "Accès", "Licence"]), font_size=7)
    if ctx.get("bibliographie"):
        doc.add_heading("Bibliographie des sources interrogées", level=3)
        for ref in ctx["bibliographie"]:
            doc.add_paragraph(ref, style="List Bullet")
    doc.add_heading("B. Référentiel réglementaire et méthodologique", level=2)
    add_text(doc, "Statut de vérification de chaque élément au moment de la génération de l'outil (novembre 2026). Le texte consolidé "
                  "sur Légifrance fait foi.", italic=True)
    for it in REFERENTIEL:
        doc.add_heading(f"{it.theme} – {it.titre}", level=3)
        add_text(doc, it.contenu)
        q = doc.add_paragraph()
        q.add_run(f"Statut : {it.statut}. ").bold = True
        q.add_run("Sources : " + " ; ".join(f"{lbl} ({url})" for lbl, url in it.sources)).font.size = Pt(8)
    doc.add_heading("C. Limites des données", level=2)
    for lim in (
        "RPG : seules les surfaces déclarées à la PAC sont recensées.",
        "RA 2020 : données rattachées à la commune du siège de l'exploitation ; secret statistique sur les petites communes.",
        "SIRENE : le code NAF déclaré peut différer de l'activité réelle ; effectifs par tranches déclaratives.",
        "Agence Bio : annuaire déclaratif des opérateurs ; date de mise à jour variable.",
        "DVF : hors Alsace, Moselle, Mayotte ; une mutation peut regrouper des biens hétérogènes.",
        "Les montants de compensation dépendent des paramètres de la doctrine départementale.",
    ):
        doc.add_paragraph(lim, style="List Bullet")

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def build_xlsx(tables: dict[str, pd.DataFrame]) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        for name, df in tables.items():
            if df is None:
                continue
            d = df.copy()
            if "geometry" in d.columns:
                d = d.drop(columns="geometry")
            sheet = "".join(ch for ch in name if ch not in "[]:*?/\\")[:31]
            d.to_excel(xw, sheet_name=sheet, index=False)
    return buf.getvalue()

