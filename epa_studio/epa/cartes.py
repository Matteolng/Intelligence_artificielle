"""Cartographie interactive (Folium) et cartes statiques pour le rapport (Matplotlib)."""
from __future__ import annotations

import io

import branca.colormap as bcm
import folium
import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from folium.plugins import Draw, Fullscreen, MarkerCluster, MeasureControl  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
from PIL import Image  # noqa: E402

from .config import BASEMAPS, COLORS, GPF_WMS_RASTER, WMS_LAYERS  # noqa: E402
from .http import DataSourceError, disk_cache, get  # noqa: E402

WEB_MERCATOR = "EPSG:3857"


# ---------------------------------------------------------------------------
# Cartes interactives
# ---------------------------------------------------------------------------

def zoom_pour_emprise(bounds, largeur_px: int = 760, hauteur_px: int = 460) -> int:
    """Niveau de zoom Web Mercator permettant d'afficher l'emprise dans une carte de taille donnée.

    Calculé côté Python : `fit_bounds` de Leaflet échoue lorsque la carte est créée dans un onglet
    masqué (taille nulle au chargement) et renvoie alors une vue du monde entier.
    """
    minx, miny, maxx, maxy = bounds
    dlon = max(maxx - minx, 1e-4)

    def merc(lat: float) -> float:
        lat = max(min(lat, 85.0), -85.0)
        return np.degrees(np.log(np.tan(np.pi / 4 + np.radians(lat) / 2)))

    dlat = max(merc(maxy) - merc(miny), 1e-4)
    z = min(np.log2(largeur_px * 360 / (256 * dlon)), np.log2(hauteur_px * 360 / (256 * dlat)))
    return int(max(2, min(18, np.floor(z))))


def base_map(bounds, basemap: str = "Plan IGN", draw: bool = False) -> folium.Map:
    minx, miny, maxx, maxy = bounds
    m = folium.Map(location=[(miny + maxy) / 2, (minx + maxx) / 2], zoom_start=zoom_pour_emprise(bounds), tiles=None,
                   control_scale=True, prefer_canvas=True)
    for name, bm in BASEMAPS.items():
        folium.TileLayer(tiles=bm["tiles"], attr=bm["attr"], name=name, overlay=False, control=True,
                         show=(name == basemap), max_zoom=19).add_to(m)
    Fullscreen(position="topleft").add_to(m)
    MeasureControl(position="topleft", primary_length_unit="meters", primary_area_unit="hectares").add_to(m)
    if draw:
        Draw(
            export=False,
            position="topleft",
            draw_options={"polyline": False, "circle": False, "circlemarker": False, "marker": False,
                          "rectangle": True, "polygon": {"allowIntersection": False, "showArea": True}},
            edit_options={"edit": True, "remove": True},
        ).add_to(m)
    return m


def add_wms(m: folium.Map, names: list[str], show: bool = True) -> None:
    for name in names:
        cfg = WMS_LAYERS.get(name)
        if not cfg:
            continue
        folium.WmsTileLayer(
            url=cfg["url"], layers=cfg["layer"], name=name, fmt="image/png", transparent=True,
            overlay=True, control=True, opacity=cfg.get("opacity", 0.7), attr="© IGN – Géoplateforme",
            version="1.3.0", show=show,
        ).add_to(m)


def _simplify(gdf: gpd.GeoDataFrame, tol: float = 0.0003) -> gpd.GeoDataFrame:
    g = gdf.copy()
    g["geometry"] = g.geometry.simplify(tol, preserve_topology=True)
    return g


def add_territoire(m: folium.Map, communes: gpd.GeoDataFrame, name: str = "Communes du territoire") -> None:
    g = _simplify(communes[["code", "nom", "geometry"]])
    folium.GeoJson(
        g.to_json(), name=name,
        style_function=lambda f: {"color": COLORS["territoire"], "weight": 1.2, "fillOpacity": 0.0},
        highlight_function=lambda f: {"weight": 3, "color": COLORS["accent"]},
        tooltip=folium.GeoJsonTooltip(fields=["nom", "code"], aliases=["Commune", "Code INSEE"]),
    ).add_to(m)
    contour = gpd.GeoDataFrame(geometry=[communes.geometry.union_all()], crs=communes.crs)
    folium.GeoJson(contour.to_json(), name="Contour du territoire",
                   style_function=lambda f: {"color": COLORS["territoire"], "weight": 3.5, "fillOpacity": 0}).add_to(m)


def add_emprise(m: folium.Map, emprise: gpd.GeoDataFrame | None) -> None:
    if emprise is None or emprise.empty:
        return
    folium.GeoJson(emprise[["geometry"]].to_crs("EPSG:4326").to_json(), name="Emprise du projet",
                   style_function=lambda f: {"color": COLORS["emprise"], "weight": 3, "fillColor": COLORS["emprise"], "fillOpacity": 0.15}).add_to(m)


def choropleth(m: folium.Map, gdf: gpd.GeoDataFrame, column: str, legend: str, palette: str = "YlGn",
               fmt: str = "{:,.0f}", tooltip_fields: list[str] | None = None, tooltip_aliases: list[str] | None = None,
               name: str | None = None) -> None:
    g = _simplify(gdf)
    vals = pd.to_numeric(g[column], errors="coerce")
    if vals.notna().sum() == 0:
        return
    vmin, vmax = float(np.nanmin(vals)), float(np.nanmax(vals))
    if vmin == vmax:
        vmax = vmin + 1
    pal = {
        "YlGn": bcm.linear.YlGn_09, "Greens": bcm.linear.Greens_09, "YlOrBr": bcm.linear.YlOrBr_09,
        "RdYlGn": bcm.linear.RdYlGn_11, "Blues": bcm.linear.Blues_09, "Purples": bcm.linear.Purples_09,
    }.get(palette, bcm.linear.YlGn_09)
    cmap = pal.scale(vmin, vmax)
    cmap.caption = legend
    g = g.assign(_v=vals)
    g["_lbl"] = g["_v"].map(lambda v: "n.d. (secret / absence)" if pd.isna(v) else fmt.format(v).replace(",", " "))

    def style(f):
        v = f["properties"].get("_v")
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return {"fillColor": "#d9d9d9", "color": "#777", "weight": 0.6, "fillOpacity": 0.5, "dashArray": "3"}
        return {"fillColor": cmap(v), "color": "#555", "weight": 0.6, "fillOpacity": 0.75}

    fields = (tooltip_fields or ["nom"]) + ["_lbl"]
    aliases = (tooltip_aliases or ["Commune"]) + [legend]
    keep = list(dict.fromkeys([*fields, "_v", "geometry"]))
    folium.GeoJson(g[keep].to_json(), name=name or legend, style_function=style,
                   tooltip=folium.GeoJsonTooltip(fields=fields, aliases=aliases, localize=True)).add_to(m)
    cmap.add_to(m)


def categorical(m: folium.Map, gdf: gpd.GeoDataFrame, column: str, colors: dict[str, str], name: str,
                tooltip_fields: list[str], tooltip_aliases: list[str], simplify: float = 0.0) -> None:
    g = _simplify(gdf, simplify) if simplify else gdf
    keep = list(dict.fromkeys([*tooltip_fields, column, "geometry"]))

    def style(f):
        c = colors.get(f["properties"].get(column), "#999999")
        return {"fillColor": c, "color": c, "weight": 0.4, "fillOpacity": 0.75}

    folium.GeoJson(g[keep].to_json(), name=name, style_function=style,
                   tooltip=folium.GeoJsonTooltip(fields=tooltip_fields, aliases=tooltip_aliases)).add_to(m)


def legend_html(colors: dict[str, str], title: str) -> str:
    items = "".join(
        f'<div style="display:flex;align-items:center;gap:6px;margin:2px 0"><span style="width:14px;height:14px;'
        f'background:{c};display:inline-block;border-radius:3px"></span><span>{k}</span></div>'
        for k, c in colors.items()
    )
    return (f'<div style="position:fixed;bottom:24px;right:12px;z-index:9999;background:white;padding:8px 10px;'
            f'border-radius:8px;box-shadow:0 1px 6px rgba(0,0,0,.25);font:12px sans-serif;max-width:260px">'
            f'<b>{title}</b>{items}</div>')


def add_legend(m: folium.Map, colors: dict[str, str], title: str) -> None:
    m.get_root().html.add_child(folium.Element(legend_html(colors, title)))


def add_points(m: folium.Map, df: pd.DataFrame, name: str, color: str, popup_cols: list[str],
               icon: str = "circle", cluster: bool = True) -> None:
    d = df.dropna(subset=["latitude", "longitude"])
    if d.empty:
        return
    fg = folium.FeatureGroup(name=name, show=True)
    target = MarkerCluster(name=name).add_to(fg) if cluster else fg
    for _, r in d.iterrows():
        html = "<br>".join(f"<b>{c}</b> : {r[c]}" for c in popup_cols if c in r and pd.notna(r[c]))
        folium.CircleMarker(location=[float(r["latitude"]), float(r["longitude"])], radius=6, color=color, weight=1,
                            fill=True, fill_color=color, fill_opacity=0.85,
                            popup=folium.Popup(html, max_width=320), tooltip=str(r.get("nom", ""))).add_to(target)
    fg.add_to(m)


def finalize(m: folium.Map) -> folium.Map:
    folium.LayerControl(collapsed=True).add_to(m)
    return m


# ---------------------------------------------------------------------------
# Cartes statiques (rapport)
# ---------------------------------------------------------------------------

@disk_cache("wms")
def _wms_image(layer: str, bbox3857: tuple[float, float, float, float], width: int, height: int, url: str = GPF_WMS_RASTER) -> bytes:
    params = {
        "SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetMap", "LAYERS": layer, "STYLES": "",
        "CRS": "EPSG:3857", "BBOX": ",".join(f"{v:.2f}" for v in bbox3857), "WIDTH": width, "HEIGHT": height,
        "FORMAT": "image/png", "TRANSPARENT": "TRUE",
    }
    r = get(url, params=params, timeout=120)
    if "image" not in r.headers.get("Content-Type", ""):
        raise DataSourceError(f"WMS {layer} : réponse non image")
    return r.content


def _fond(ax, bbox3857, layer: str = "GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2", url: str = GPF_WMS_RASTER, alpha: float = 1.0) -> None:
    minx, miny, maxx, maxy = bbox3857
    w = 1600
    h = max(200, int(w * (maxy - miny) / (maxx - minx)))
    h = min(h, 2400)
    try:
        img = Image.open(io.BytesIO(_wms_image(layer, bbox3857, w, h, url)))
        ax.imshow(img, extent=(minx, maxx, miny, maxy), zorder=0, alpha=alpha)
    except Exception:  # fond facultatif : la carte reste lisible sans
        pass


def _padded_bbox(gdf3857: gpd.GeoDataFrame, pad: float = 0.05):
    minx, miny, maxx, maxy = gdf3857.total_bounds
    dx, dy = (maxx - minx) * pad, (maxy - miny) * pad
    return (minx - dx, miny - dy, maxx + dx, maxy + dy)


def _finish(fig, ax, titre: str, source: str) -> bytes:
    ax.set_axis_off()
    ax.set_title(titre, fontsize=13, fontweight="bold", loc="left", color="#1F2A24")
    fig.text(0.01, 0.01, source, fontsize=7, color="#555")
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=160, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def carte_localisation(communes: gpd.GeoDataFrame, emprise: gpd.GeoDataFrame | None, titre: str) -> bytes:
    c = communes.to_crs(WEB_MERCATOR)
    bbox = _padded_bbox(c)
    fig, ax = plt.subplots(figsize=(8, 8))
    _fond(ax, bbox)
    c.boundary.plot(ax=ax, color=COLORS["territoire"], linewidth=0.6, zorder=2)
    gpd.GeoSeries([c.geometry.union_all()], crs=WEB_MERCATOR).boundary.plot(ax=ax, color=COLORS["territoire"], linewidth=2.2, zorder=3)
    handles = [Patch(facecolor="none", edgecolor=COLORS["territoire"], linewidth=2, label="Territoire d'étude")]
    if emprise is not None and not emprise.empty:
        e = emprise.to_crs(WEB_MERCATOR)
        e.plot(ax=ax, facecolor=COLORS["emprise"], edgecolor=COLORS["emprise"], alpha=0.5, zorder=4, linewidth=1.5)
        handles.append(Patch(facecolor=COLORS["emprise"], alpha=0.5, label="Emprise du projet"))
    ax.set_xlim(bbox[0], bbox[2])
    ax.set_ylim(bbox[1], bbox[3])
    ax.legend(handles=handles, loc="lower right", fontsize=8, frameon=True)
    return _finish(fig, ax, titre, "Fond : Plan IGN (Géoplateforme) – Limites : API Découpage administratif")


def carte_choroplethe(communes: gpd.GeoDataFrame, column: str, titre: str, legende: str, cmap: str = "YlGn",
                      source: str = "") -> bytes:
    c = communes.to_crs(WEB_MERCATOR)
    bbox = _padded_bbox(c)
    fig, ax = plt.subplots(figsize=(8, 8))
    _fond(ax, bbox, alpha=0.5)
    vals = pd.to_numeric(c[column], errors="coerce")
    c = c.assign(_v=vals)
    if c["_v"].isna().any():
        c[c["_v"].isna()].plot(ax=ax, color="#dddddd", edgecolor="#888", linewidth=0.4, hatch="///", zorder=2)
    if c["_v"].notna().any():
        c[c["_v"].notna()].plot(ax=ax, column="_v", cmap=cmap, edgecolor="#555", linewidth=0.4, legend=True, zorder=3,
                                legend_kwds={"label": legende, "shrink": 0.6})
    ax.set_xlim(bbox[0], bbox[2])
    ax.set_ylim(bbox[1], bbox[3])
    return _finish(fig, ax, titre, source)


def carte_categories(gdf: gpd.GeoDataFrame, column: str, colors: dict[str, str], titre: str, source: str,
                     contour: gpd.GeoDataFrame | None = None, emprise: gpd.GeoDataFrame | None = None) -> bytes:
    g = gdf.to_crs(WEB_MERCATOR)
    ref = contour.to_crs(WEB_MERCATOR) if contour is not None else g
    bbox = _padded_bbox(ref)
    fig, ax = plt.subplots(figsize=(8, 8))
    _fond(ax, bbox, alpha=0.45)
    present = [k for k in colors if k in set(g[column])]
    for k in present:
        g[g[column] == k].plot(ax=ax, color=colors[k], linewidth=0, zorder=2)
    if contour is not None:
        ref.boundary.plot(ax=ax, color="#333", linewidth=0.5, zorder=3)
    if emprise is not None and not emprise.empty:
        emprise.to_crs(WEB_MERCATOR).boundary.plot(ax=ax, color=COLORS["emprise"], linewidth=2, zorder=4)
    ax.set_xlim(bbox[0], bbox[2])
    ax.set_ylim(bbox[1], bbox[3])
    ax.legend(handles=[Patch(color=colors[k], label=k) for k in present], loc="lower left", fontsize=7, frameon=True)
    return _finish(fig, ax, titre, source)


def carte_points(communes: gpd.GeoDataFrame, df: pd.DataFrame, column: str, titre: str, source: str,
                 palette: dict[str, str] | None = None) -> bytes:
    c = communes.to_crs(WEB_MERCATOR)
    bbox = _padded_bbox(c)
    fig, ax = plt.subplots(figsize=(8, 8))
    _fond(ax, bbox, alpha=0.55)
    c.boundary.plot(ax=ax, color="#555", linewidth=0.4, zorder=2)
    d = df.dropna(subset=["latitude", "longitude"])
    if not d.empty:
        p = gpd.GeoDataFrame(d, geometry=gpd.points_from_xy(d["longitude"], d["latitude"]), crs="EPSG:4326").to_crs(WEB_MERCATOR)
        cats = list(p[column].fillna("Autre").unique())
        base = plt.get_cmap("tab10")
        palette = palette or {k: matplotlib.colors.to_hex(base(i % 10)) for i, k in enumerate(cats)}
        for k in cats:
            p[p[column].fillna("Autre") == k].plot(ax=ax, color=palette.get(k, "#333"), markersize=22, edgecolor="white",
                                                   linewidth=0.5, zorder=3, label=k)
        ax.legend(loc="lower left", fontsize=7, frameon=True)
    ax.set_xlim(bbox[0], bbox[2])
    ax.set_ylim(bbox[1], bbox[3])
    return _finish(fig, ax, titre, source)

