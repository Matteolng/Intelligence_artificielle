"""Figures types d'une étude préalable agricole, exportées en PNG 300 dpi avec titre, source, échelle et nord.

Chaque fonction renvoie les octets PNG, ou None quand la donnée d'entrée manque (jamais de substitut).
Fonds et couches : Géoplateforme IGN (WMS). Couleurs : palette catégorielle du système de visualisation
(ordre fixe, jamais recyclé), gris neutres pour le contexte, couleur du bureau d'études pour la mise en évidence.
"""
from __future__ import annotations

import io
import math
import re
import textwrap

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
from PIL import Image  # noqa: E402

from . import cartes  # noqa: E402
from .branding import branding_courant  # noqa: E402
from .config import GPF_WMS_RASTER  # noqa: E402
from .http import DataSourceError, disk_cache, get, get_bytes  # noqa: E402

DPI = 300
M = "EPSG:3857"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
AUTRE = "#B8B8BE"
TEXTE, SECOND, FILET = "#1D1D1F", "#6E6E73", "#D2D2D7"
ORTHO = "ORTHOIMAGERY.ORTHOPHOTOS"
PLAN = "GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2"

plt.rcParams.update({"font.family": ["Inter", "DejaVu Sans"], "font.size": 8, "text.color": TEXTE})


# ---------------------------------------------------------------------------
# Outils communs
# ---------------------------------------------------------------------------

def _bbox(g3857: gpd.GeoDataFrame, pad: float = 0.08, carre: bool = False):
    minx, miny, maxx, maxy = g3857.total_bounds
    w, h = maxx - minx, maxy - miny
    if carre:
        c = max(w, h)
        cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
        minx, maxx, miny, maxy = cx - c / 2, cx + c / 2, cy - c / 2, cy + c / 2
        w = h = c
    return (minx - w * pad, miny - h * pad, maxx + w * pad, maxy + h * pad)


def _cadre(ax, bbox) -> None:
    ax.set_xlim(bbox[0], bbox[2])
    ax.set_ylim(bbox[1], bbox[3])
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlabel("")
    ax.set_ylabel("")
    for s in ax.spines.values():
        s.set_edgecolor(FILET)
        s.set_linewidth(0.6)


def _echelle(ax, bbox) -> None:
    """Barre d'échelle en distance au sol (correction de la déformation Web Mercator par cos(latitude))."""
    minx, miny, maxx, maxy = bbox
    lat = math.degrees(2 * math.atan(math.exp(((miny + maxy) / 2) / 6378137)) - math.pi / 2)
    k = math.cos(math.radians(lat))
    sol = (maxx - minx) * k * 0.22
    pas = 10 ** math.floor(math.log10(sol))
    long_m = max(n * pas for n in (1, 2, 5) if n * pas <= sol)
    x0, y0 = minx + (maxx - minx) * 0.04, miny + (maxy - miny) * 0.05
    ax.plot([x0, x0 + long_m / k], [y0, y0], color=TEXTE, lw=1.6, solid_capstyle="butt", zorder=10)
    lab = f"{long_m / 1000:g} km" if long_m >= 1000 else f"{long_m:g} m"
    ax.text(x0, y0 + (maxy - miny) * 0.02, lab, fontsize=6.5, color=TEXTE, zorder=10,
            bbox={"facecolor": "white", "alpha": 0.75, "edgecolor": "none", "pad": 1})


def _nord(ax) -> None:
    ax.annotate("N", xy=(0.955, 0.955), xytext=(0.955, 0.865), xycoords="axes fraction", ha="center", va="center",
                fontsize=7, fontweight="bold", color=TEXTE, arrowprops={"arrowstyle": "-|>", "color": TEXTE, "lw": 1})


def _fond(ax, bbox, couche: str, alpha: float = 1.0) -> bool:
    minx, miny, maxx, maxy = bbox
    w = 1800
    h = min(2600, max(200, int(w * (maxy - miny) / (maxx - minx))))
    try:
        img = Image.open(io.BytesIO(cartes._wms_image(couche, bbox, w, h, GPF_WMS_RASTER)))
    except Exception:
        return False
    ax.imshow(img, extent=(minx, maxx, miny, maxy), zorder=0, alpha=alpha)
    return True


def _export(fig, titre: str, source: str, sous_titre: str = "") -> bytes:
    h = fig.get_size_inches()[1]
    fig.text(0.012, 1 - 0.12 / h, titre, fontsize=12, fontweight="semibold", color=TEXTE, va="top", ha="left")
    if sous_titre:
        fig.text(0.012, 1 - 0.36 / h, sous_titre, fontsize=8, color=SECOND, va="top", ha="left")
    b = branding_courant()
    from datetime import date as _d
    fig.text(0.012, 0.012, f"Source : {source}. Données consultées le {_d.today().strftime('%d/%m/%Y')}.",
             fontsize=6.5, color=SECOND, ha="left", va="bottom")
    fig.text(0.988, 0.012, b.nom, fontsize=6.5, color=SECOND, ha="right", va="bottom")
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=DPI, facecolor="white")
    plt.close(fig)
    return buf.getvalue()


def _palette(categories_par_poids: list[str], max_slots: int = 7) -> dict[str, str]:
    """Ordre fixe : les catégories les plus étendues prennent les premiers emplacements, le reste « Autres »."""
    return {c: SERIES[i] for i, c in enumerate(categories_par_poids[:max_slots])}


def _legende(ax_or_fig, pal: dict[str, str], autres: bool, **kw) -> None:
    h = [Patch(facecolor=c, edgecolor="white", label=textwrap.fill(str(k), 30)) for k, c in pal.items()]
    if autres:
        h.append(Patch(facecolor=AUTRE, edgecolor="white", label="Autres"))
    ax_or_fig.legend(handles=h, frameon=False, fontsize=7, **kw)


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------

def vignettes_rpg(emprise: gpd.GeoDataFrame | None, rpg_par_annee: dict[int, gpd.GeoDataFrame], colonne: str = "culture") -> bytes | None:
    """Petits multiples : cultures déclarées au RPG sur l'emprise, une vignette par millésime, sur photographie aérienne."""
    if emprise is None or emprise.empty or not rpg_par_annee:
        return None
    annees = sorted(rpg_par_annee)
    tout = pd.concat([g[[colonne, "surface_ha"]] for g in rpg_par_annee.values() if not g.empty], ignore_index=True)
    if tout.empty:
        return None
    ordre = tout.groupby(colonne)["surface_ha"].sum().sort_values(ascending=False).index.tolist()
    pal = _palette(ordre)
    e = emprise.to_crs(M)
    bbox = _bbox(e, pad=0.18, carre=True)
    n = len(annees)
    ncol = min(3, n)
    nrow = math.ceil(n / ncol)
    fig = plt.figure(figsize=(3.2 * ncol + 2.4, 3.3 * nrow + 0.9))
    gs = fig.add_gridspec(nrow, ncol + 1, width_ratios=[1] * ncol + [0.75], left=0.02, right=0.98, top=0.88, bottom=0.07,
                          wspace=0.06, hspace=0.18)
    for i, a in enumerate(annees):
        ax = fig.add_subplot(gs[i // ncol, i % ncol])
        _fond(ax, bbox, ORTHO)
        g = rpg_par_annee[a]
        if not g.empty:
            g = g.to_crs(M)
            g.plot(ax=ax, color=[pal.get(v, AUTRE) for v in g[colonne]], alpha=0.78, edgecolor="white", linewidth=0.6, zorder=2)
        e.boundary.plot(ax=ax, color="white", linewidth=1.6, zorder=3)
        e.boundary.plot(ax=ax, color=TEXTE, linewidth=0.6, zorder=4)
        _cadre(ax, bbox)
        ax.set_title(f"RPG {a}", fontsize=9, fontweight="semibold", loc="left", color=TEXTE)
        if i == 0:
            _echelle(ax, bbox)
            _nord(ax)
    lax = fig.add_subplot(gs[:, ncol])
    lax.axis("off")
    _legende(lax, pal, autres=len(ordre) > len(pal), loc="upper left", title="Culture déclarée", title_fontsize=7.5,
             alignment="left")
    return _export(fig, "Cultures déclarées sur le site d'étude", f"IGN / ASP, RPG {annees[0]}-{annees[-1]} ; IGN, photographies aériennes",
                   "Parcelles du registre parcellaire graphique intersectant l'emprise du projet")


def localisation_3_echelles(departement: gpd.GeoDataFrame, perimetre: gpd.GeoDataFrame, commune_site: gpd.GeoDataFrame,
                            emprise: gpd.GeoDataFrame | None, noms: tuple[str, str, str]) -> bytes:
    """Département → périmètre d'étude → site, de gauche à droite."""
    acc = branding_courant().couleur
    d, p, c = departement.to_crs(M), perimetre.to_crs(M), commune_site.to_crs(M)
    fig, axs = plt.subplots(1, 3, figsize=(12, 4.6), gridspec_kw={"wspace": 0.05})
    fig.subplots_adjust(left=0.01, right=0.99, top=0.84, bottom=0.12)
    # 1. département
    b1 = _bbox(d, 0.04, carre=True)
    d.plot(ax=axs[0], color="#EDEDF0", edgecolor="white", linewidth=0.3)
    p.plot(ax=axs[0], color=acc, alpha=0.35, edgecolor="none")
    gpd.GeoSeries([d.union_all()], crs=M).boundary.plot(ax=axs[0], color=TEXTE, linewidth=0.8)
    c.plot(ax=axs[0], color=acc, edgecolor="none")
    # 2. périmètre
    b2 = _bbox(p, 0.06, carre=True)
    p.plot(ax=axs[1], color="#EDEDF0", edgecolor="white", linewidth=0.5)
    gpd.GeoSeries([p.union_all()], crs=M).boundary.plot(ax=axs[1], color=TEXTE, linewidth=0.8)
    c.plot(ax=axs[1], color=acc, edgecolor="white", linewidth=0.5)
    # 3. site
    ref = emprise.to_crs(M) if emprise is not None and not emprise.empty else c
    b3 = _bbox(c, 0.08, carre=True)
    _fond(axs[2], b3, ORTHO)
    c.boundary.plot(ax=axs[2], color="white", linewidth=3)
    c.boundary.plot(ax=axs[2], color=acc, linewidth=1.6)
    if ref is not c:
        ref.plot(ax=axs[2], facecolor="none", edgecolor="white", linewidth=1.8, zorder=3)
        ref.plot(ax=axs[2], facecolor="none", edgecolor=TEXTE, linewidth=0.8, zorder=4)
    for ax, b, n in zip(axs, (b1, b2, b3), noms):
        _cadre(ax, b)
        _echelle(ax, b)
        ax.set_title(n, fontsize=9, fontweight="semibold", loc="left", color=TEXTE)
    _nord(axs[2])
    h = [Patch(color=acc, label="Commune du site"), Patch(color=acc, alpha=0.35, label="Périmètre d'étude")]
    if ref is not c:
        h.append(Patch(facecolor="none", edgecolor=TEXTE, label="Emprise du projet"))
    fig.legend(handles=h, loc="lower center", ncol=len(h), frameon=False, fontsize=7, bbox_to_anchor=(0.5, 0.035))
    return _export(fig, "Localisation du projet", "DINUM, API Découpage administratif ; IGN, photographies aériennes",
                   "Du département à la commune du site")


def carte_otex(communes: gpd.GeoDataFrame, df_otex: pd.DataFrame | None, col_code: str = "codgeo", col_otex: str = "otex",
               source: str = "Agreste, recensement agricole 2020, OTEX en 12 postes (data.gouv.fr)") -> bytes | None:
    """Orientation technico-économique dominante par commune (export Cartostat/DISAR importé). None sans fichier."""
    if df_otex is None or df_otex.empty or col_otex not in df_otex:
        return None
    o = df_otex[[col_code, col_otex]].copy()
    o[col_code] = o[col_code].astype(str).str.zfill(5)
    g = communes.to_crs(M).merge(o, left_on="code", right_on=col_code, how="left")
    g[col_otex] = g[col_otex].where(g[col_otex].notna(), None).map(lambda v: "Non diffusé (secret statistique ou absence)" if v is None or str(v).strip() in ("", "nan") else str(v))
    ordre = g.assign(_a=g.area).groupby(col_otex)["_a"].sum().sort_values(ascending=False).index.tolist()
    ordre = [x for x in ordre if not x.startswith("Non diffusé")]
    pal = _palette(ordre)
    bbox = _bbox(g, 0.05)
    fig = plt.figure(figsize=(10, 6.2))
    ax = fig.add_axes([0.01, 0.07, 0.68, 0.82])
    colors = [pal.get(v, "#FFFFFF" if v.startswith("Non diffusé") else AUTRE) for v in g[col_otex]]
    g.plot(ax=ax, color=colors, edgecolor="white", linewidth=0.5, hatch=None)
    nd = g[g[col_otex].str.startswith("Non diffusé")]
    if not nd.empty:
        nd.plot(ax=ax, facecolor="white", edgecolor=FILET, hatch="////", linewidth=0.4)
    gpd.GeoSeries([g.union_all()], crs=M).boundary.plot(ax=ax, color=TEXTE, linewidth=0.8)
    _cadre(ax, bbox)
    _echelle(ax, bbox)
    _nord(ax)
    h = [Patch(facecolor=c, edgecolor="white", label=textwrap.fill(str(k), 34)) for k, c in pal.items()]
    if len(ordre) > len(pal):
        h.append(Patch(facecolor=AUTRE, label="Autres orientations"))
    if not nd.empty:
        h.append(Patch(facecolor="white", edgecolor=FILET, hatch="////", label="Non diffusé"))
    fig.legend(handles=h, loc="upper left", bbox_to_anchor=(0.71, 0.88), frameon=False, fontsize=7, title="OTEX dominante",
               title_fontsize=7.5, alignment="left")
    return _export(fig, "Orientation technico-économique des communes", source,
                   "OTEX dominante par commune du périmètre d'étude")


@disk_cache("wms")
def legende_wms(couche: str) -> bytes | None:
    """Image de légende publiée dans les GetCapabilities de la Géoplateforme (LegendURL)."""
    caps = get(GPF_WMS_RASTER, params={"SERVICE": "WMS", "REQUEST": "GetCapabilities", "VERSION": "1.3.0"}, timeout=120).text
    i = caps.find(f"<Name>{couche}</Name>")
    if i < 0:
        return None
    j = caps.find("</Layer>", i)
    m = re.search(r'<LegendURL[^>]*>.*?href="([^"]+)"', caps[i:j], re.S)
    return get_bytes(m.group(1)) if m else None


def carte_wms_perimetre(perimetre: gpd.GeoDataFrame, couche: str, titre: str, source: str, sous_titre: str = "",
                        legende: bool = True) -> bytes | None:
    """Couche WMS (ex. CORINE Land Cover, sols INRAE) découpée visuellement au périmètre, avec sa légende officielle."""
    p = perimetre.to_crs(M)
    bbox = _bbox(p, 0.05)
    leg = None
    if legende:
        try:
            leg = legende_wms(couche)
        except (DataSourceError, Exception):
            leg = None
    fig = plt.figure(figsize=(11, 6.4))
    ax = fig.add_axes([0.01, 0.07, 0.66 if leg else 0.98, 0.82])
    _fond(ax, bbox, PLAN, alpha=0.35)
    if not _fond(ax, bbox, couche, alpha=0.95):
        plt.close(fig)
        return None
    outside = gpd.GeoSeries([gpd.GeoSeries.from_xy([bbox[0]], [bbox[1]]).buffer(1e7).iloc[0].difference(p.union_all())], crs=M)
    outside.plot(ax=ax, color="white", alpha=0.72, zorder=5)
    p.boundary.plot(ax=ax, color="white", linewidth=0.5, zorder=6)
    gpd.GeoSeries([p.union_all()], crs=M).boundary.plot(ax=ax, color=TEXTE, linewidth=1, zorder=7)
    _cadre(ax, bbox)
    _echelle(ax, bbox)
    _nord(ax)
    if leg:
        img = Image.open(io.BytesIO(leg))
        lax = fig.add_axes([0.69, 0.07, 0.3, 0.82])
        lax.imshow(img)
        lax.axis("off")
    return _export(fig, titre, source, sous_titre)


def evolutions_comparees(comp: pd.DataFrame) -> bytes | None:
    """Barres horizontales : évolution 2010-2020 des exploitations et de la SAU, périmètre mis en évidence."""
    cols = [("Évolution exploitations 2010-2020 (%)", "Nombre d'exploitations"), ("Évolution SAU 2010-2020 (%)", "Surface agricole utilisée")]
    if comp is None or comp.empty or not any(c in comp for c, _ in cols):
        return None
    acc = branding_courant().couleur
    lab = comp["Territoire"].tolist()
    fig, axs = plt.subplots(1, 2, figsize=(9, 2.9), sharey=True)
    fig.subplots_adjust(left=0.15, right=0.98, top=0.76, bottom=0.12, wspace=0.04)
    for ax, (c, t) in zip(axs, cols):
        v = pd.to_numeric(comp.get(c), errors="coerce")
        y = list(range(len(lab)))[::-1]
        colors = [acc] + ["#A1A1A6"] * (len(lab) - 1)
        ax.barh(y, v.fillna(0), color=colors, height=0.56)
        span = max(1.0, float(v.abs().max(skipna=True) or 1))
        for yi, vi in zip(y, v):
            txt = "non disponible" if pd.isna(vi) else (("+" if vi > 0 else "−" if vi < 0 else "") + f"{abs(vi):.1f}".replace(".", ",") + " %")
            ax.text((vi if pd.notna(vi) else 0) + (span * 0.03 if (pd.isna(vi) or vi >= 0) else -span * 0.03), yi, txt,
                    va="center", ha="left" if (pd.isna(vi) or vi >= 0) else "right", fontsize=7.5, color=TEXTE)
        ax.axvline(0, color=TEXTE, lw=0.8)
        ax.set_xlim(-span * 1.45, span * 1.45)
        ax.set_yticks(y, lab, fontsize=8)
        ax.set_xticks([])
        for s in ("top", "right", "bottom", "left"):
            ax.spines[s].set_visible(False)
        ax.tick_params(axis="y", length=0)
        ax.set_title(t, fontsize=9, fontweight="semibold", loc="left", color=TEXTE)
    return _export(fig, "Évolution de l'agriculture entre 2010 et 2020", "Agreste, recensements agricoles 2010 et 2020, via l'Observatoire des territoires (ANCT)")
