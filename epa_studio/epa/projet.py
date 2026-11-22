"""Projet : caractéristiques et emprise (import de fichier SIG ou dessin sur la carte)."""
from __future__ import annotations

import io
import json
import tempfile
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

import geopandas as gpd
from shapely.geometry import shape
from shapely.ops import unary_union

from .territoire import L93, WGS84

TYPES_PROJET = [
    "Agrivoltaïque",
    "Photovoltaïque au sol (hors agrivoltaïsme)",
    "Autre aménagement (zone d'activités, infrastructure…)",
]

SERVICES_AGRIVOLTAIQUES = [
    "Amélioration du potentiel et de l'impact agronomiques",
    "Adaptation au changement climatique",
    "Protection contre les aléas",
    "Amélioration du bien-être animal",
]


@dataclass
class Projet:
    nom: str = "Projet"
    maitre_ouvrage: str = ""
    type_projet: str = TYPES_PROJET[0]
    puissance_mwc: float | None = None
    technologie: str = ""
    taux_couverture_pct: float | None = None
    hauteur_min_m: float | None = None
    duree_exploitation_ans: float | None = None
    production_agricole_prevue: str = ""
    exploitant_agricole: str = ""
    services: list[str] = field(default_factory=list)
    zone_temoin: str = "À définir"
    surface_infrastructures_ha: float = 0.0
    description: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def lire_emprise(nom_fichier: str, contenu: bytes) -> gpd.GeoDataFrame:
    """Lit un GeoJSON, KML, GPKG ou shapefile zippé et renvoie des polygones en WGS84."""
    suffix = Path(nom_fichier).suffix.lower()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / f"emprise{suffix}"
        path.write_bytes(contenu)
        if suffix == ".zip":
            with zipfile.ZipFile(io.BytesIO(contenu)) as z:
                z.extractall(tmp)
            shp = next(Path(tmp).rglob("*.shp"), None)
            if shp is None:
                raise ValueError("Archive sans fichier .shp")
            gdf = gpd.read_file(shp)
        else:
            gdf = gpd.read_file(path)
    if gdf.crs is None:
        gdf = gdf.set_crs(WGS84)
    gdf = gdf.to_crs(WGS84)
    gdf = gdf[gdf.geometry.notna() & gdf.geometry.geom_type.isin(["Polygon", "MultiPolygon"])]
    if gdf.empty:
        raise ValueError("Le fichier ne contient aucun polygone.")
    return gdf[["geometry"]].reset_index(drop=True)


def emprise_depuis_dessins(drawings: list[dict] | None) -> gpd.GeoDataFrame | None:
    if not drawings:
        return None
    geoms = [shape(d["geometry"]) for d in drawings if d.get("geometry", {}).get("type") in ("Polygon", "MultiPolygon")]
    if not geoms:
        return None
    return gpd.GeoDataFrame(geometry=[unary_union(geoms)], crs=WGS84)


def surface_ha(gdf: gpd.GeoDataFrame | None) -> float:
    if gdf is None or gdf.empty:
        return 0.0
    return float(gdf.to_crs(L93).geometry.union_all().area / 1e4)


def emprise_to_geojson(gdf: gpd.GeoDataFrame | None) -> str | None:
    if gdf is None or gdf.empty:
        return None
    return gdf.to_crs(WGS84).to_json()


def emprise_from_geojson(txt: str | None) -> gpd.GeoDataFrame | None:
    if not txt:
        return None
    fc = json.loads(txt)
    return gpd.GeoDataFrame.from_features(fc["features"], crs=WGS84)


def communes_concernees(emprise: gpd.GeoDataFrame, communes: gpd.GeoDataFrame) -> list[str]:
    e = emprise.to_crs(WGS84).geometry.union_all()
    return communes.loc[communes.intersects(e), "nom"].tolist()


def code_commune_site(emprise: gpd.GeoDataFrame | None, communes: gpd.GeoDataFrame) -> str | None:
    """Code INSEE de la commune qui porte la plus grande part de l'emprise (None sans emprise ou hors territoire)."""
    if emprise is None or emprise.empty:
        return None
    e = emprise.to_crs(L93).geometry.union_all()
    c = communes.to_crs(L93)
    inter = c.geometry.intersection(e).area
    return str(c.loc[inter.idxmax(), "code"]) if inter.max() > 0 else None


def site_courant(state, communes: gpd.GeoDataFrame) -> str | None:
    """Commune du site : déduite de l'emprise si elle existe, sinon choisie par l'utilisateur (ou la démonstration)."""
    return code_commune_site(state.get("emprise"), communes) or state.get("site_commune")


def controle_agrivoltaique(p: Projet) -> list[tuple[str, str, str]]:
    """Points de contrôle (critère, statut, commentaire) – à confronter au texte en vigueur."""
    out = []
    out.append((
        "Au moins un service rendu à la parcelle (L. 314-36 c. énergie)",
        "OK" if p.services else "À compléter",
        ", ".join(p.services) if p.services else "Aucun service déclaré.",
    ))
    if p.taux_couverture_pct is None:
        out.append(("Taux de couverture", "À compléter", "Renseigner le taux de couverture des sols."))
    else:
        grand = (p.puissance_mwc or 0) > 10
        if p.taux_couverture_pct <= 40:
            out.append(("Taux de couverture ≤ 40 %", "OK", f"{p.taux_couverture_pct:g} %."))
        else:
            out.append((
                "Taux de couverture ≤ 40 %",
                "Vigilance" if not grand else "Non conforme ?",
                f"{p.taux_couverture_pct:g} % – plafond de 40 % applicable au moins aux installations > 10 MWc hors technologie "
                "éprouvée (vérifier l'arrêté listant les technologies éprouvées).",
            ))
    out.append((
        "Rendement ≥ 90 % de la zone témoin / du référentiel (hors élevage)",
        "À démontrer",
        "Prévoir le protocole de suivi agronomique et la zone témoin (ou la dérogation applicable).",
    ))
    out.append(("Zone témoin", "OK" if p.zone_temoin.startswith("Oui") else "À compléter", p.zone_temoin))
    out.append((
        "Production agricole principale et exploitant identifié",
        "OK" if p.production_agricole_prevue and p.exploitant_agricole else "À compléter",
        f"Production : {p.production_agricole_prevue or '—'} ; exploitant : {p.exploitant_agricole or '—'}",
    ))
    out.append(("Avis conforme de la CDPENAF (L. 111-27 c. urbanisme)", "À prévoir", "Saisine via l'autorisation d'urbanisme."))
    return out
