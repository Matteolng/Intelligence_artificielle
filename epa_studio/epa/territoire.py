"""Découpage administratif : régions, départements, EPCI, communes (API Découpage administratif)."""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field

import geopandas as gpd
import pandas as pd
from shapely.geometry import shape

from .config import GEO_API
from .http import DataSourceError, disk_cache, get_json

L93 = "EPSG:2154"


def _sans_accents(txt: str) -> str:
    return unicodedata.normalize("NFKD", str(txt)).encode("ascii", "ignore").decode().lower()

WGS84 = "EPSG:4326"


@disk_cache("geo")
def list_regions() -> pd.DataFrame:
    data = get_json(f"{GEO_API}/regions", limiter="geo")
    df = pd.DataFrame(data)
    return df.sort_values("nom", key=lambda s: s.map(_sans_accents)).reset_index(drop=True)


@disk_cache("geo")
def list_departements() -> pd.DataFrame:
    data = get_json(f"{GEO_API}/departements", params={"fields": "nom,code,codeRegion"}, limiter="geo")
    return pd.DataFrame(data).sort_values("code").reset_index(drop=True)


@disk_cache("geo")
def communes_departement(code_dep: str) -> pd.DataFrame:
    """Communes d'un département (sans géométrie) avec leur EPCI de rattachement."""
    data = get_json(
        f"{GEO_API}/departements/{code_dep}/communes",
        params={"fields": "nom,code,codeEpci,epci,population,surface,codeDepartement,codeRegion"},
        limiter="geo",
    )
    df = pd.DataFrame(data)
    if df.empty:
        return df
    df["nom_epci"] = df["epci"].apply(lambda e: e.get("nom") if isinstance(e, dict) else None)
    return df.drop(columns=["epci"], errors="ignore")


def list_epcis_departement(code_dep: str) -> pd.DataFrame:
    """EPCI ayant au moins une commune dans le département."""
    df = communes_departement(code_dep)
    if df.empty or "codeEpci" not in df:
        return pd.DataFrame(columns=["code", "nom", "nb_communes_dep"])
    g = (
        df.dropna(subset=["codeEpci"])
        .groupby(["codeEpci", "nom_epci"], as_index=False)
        .agg(nb_communes_dep=("code", "count"))
        .rename(columns={"codeEpci": "code", "nom_epci": "nom"})
        .sort_values("nom", key=lambda s: s.map(_sans_accents))
        .reset_index(drop=True)
    )
    return g


@disk_cache("geo")
def epci_info(code_epci: str) -> dict:
    return get_json(f"{GEO_API}/epcis/{code_epci}", limiter="geo")


def _features_to_gdf(fc: dict) -> gpd.GeoDataFrame:
    feats = fc.get("features", []) if isinstance(fc, dict) else []
    if not feats:
        return gpd.GeoDataFrame(geometry=[], crs=WGS84)
    rows = []
    for f in feats:
        props = dict(f.get("properties") or {})
        props["geometry"] = shape(f["geometry"]) if f.get("geometry") else None
        rows.append(props)
    return gpd.GeoDataFrame(rows, geometry="geometry", crs=WGS84)


_COMMUNE_FIELDS = "nom,code,codeEpci,codeDepartement,codeRegion,population,surface"


@disk_cache("geo")
def communes_epci_geo(code_epci: str) -> gpd.GeoDataFrame:
    fc = get_json(
        f"{GEO_API}/epcis/{code_epci}/communes",
        params={"format": "geojson", "geometry": "contour", "fields": _COMMUNE_FIELDS},
        limiter="geo",
    )
    return _features_to_gdf(fc)


@disk_cache("geo")
def communes_departement_geo(code_dep: str) -> gpd.GeoDataFrame:
    fc = get_json(
        f"{GEO_API}/departements/{code_dep}/communes",
        params={"format": "geojson", "geometry": "contour", "fields": _COMMUNE_FIELDS},
        limiter="geo",
    )
    return _features_to_gdf(fc)


@disk_cache("geo")
def commune_geo(code_insee: str) -> gpd.GeoDataFrame:
    f = get_json(
        f"{GEO_API}/communes/{code_insee}",
        params={"format": "geojson", "geometry": "contour", "fields": _COMMUNE_FIELDS},
        limiter="geo",
    )
    if not f or "geometry" not in f:
        raise DataSourceError(f"Commune {code_insee} introuvable")
    return _features_to_gdf({"features": [f]})


@disk_cache("geo")
def search_communes(nom: str, limit: int = 15) -> pd.DataFrame:
    data = get_json(
        f"{GEO_API}/communes",
        params={"nom": nom, "fields": "nom,code,codeDepartement,codeEpci,population", "boost": "population", "limit": limit},
        limiter="geo",
    )
    return pd.DataFrame(data)


@dataclass
class Territoire:
    """Territoire d'étude : ensemble de communes (issues d'un ou plusieurs EPCI)."""

    nom: str
    communes: gpd.GeoDataFrame  # WGS84, colonnes : code, nom, codeEpci, codeDepartement, codeRegion, population, surface
    epcis: list[dict] = field(default_factory=list)  # [{code, nom}]
    code_region: str | None = None
    codes_departements: list[str] = field(default_factory=list)

    @property
    def codes_communes(self) -> list[str]:
        return sorted(self.communes["code"].astype(str).tolist())

    @property
    def emprise(self):
        return self.communes.geometry.union_all()

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        return tuple(self.communes.total_bounds)  # type: ignore[return-value]

    @property
    def surface_ha(self) -> float:
        return float(self.communes.to_crs(L93).area.sum() / 1e4)

    @property
    def population(self) -> int:
        return int(pd.to_numeric(self.communes.get("population"), errors="coerce").fillna(0).sum())

    def resume(self) -> dict:
        return {
            "Nom": self.nom,
            "EPCI": ", ".join(e["nom"] for e in self.epcis) or "—",
            "Départements": ", ".join(self.codes_departements),
            "Nombre de communes": len(self.communes),
            "Surface (ha)": round(self.surface_ha),
            "Population (INSEE, via API Découpage administratif)": self.population,
        }


def build_territoire(
    epcis: list[dict],
    communes_ajoutees: list[str] | None = None,
    communes_retirees: list[str] | None = None,
    nom: str | None = None,
) -> Territoire:
    """Construit le territoire d'étude à partir d'EPCI (+/- communes)."""
    parts = []
    for e in epcis:
        g = communes_epci_geo(e["code"])
        if not g.empty:
            parts.append(g)
    for code in communes_ajoutees or []:
        parts.append(commune_geo(code))
    if not parts:
        raise DataSourceError("Aucune commune sélectionnée pour le territoire d'étude.")
    gdf = gpd.GeoDataFrame(pd.concat(parts, ignore_index=True), geometry="geometry", crs=WGS84)
    gdf["code"] = gdf["code"].astype(str)
    gdf = gdf.drop_duplicates(subset="code")
    if communes_retirees:
        gdf = gdf[~gdf["code"].isin(communes_retirees)]
    gdf = gdf.sort_values("nom").reset_index(drop=True)
    gdf["surface_ha"] = gdf.to_crs(L93).area / 1e4
    deps = sorted(gdf["codeDepartement"].dropna().astype(str).unique().tolist())
    regs = gdf["codeRegion"].dropna().astype(str).value_counts()
    nom = nom or (" + ".join(e["nom"] for e in epcis) if epcis else "Territoire d'étude")
    return Territoire(
        nom=nom,
        communes=gdf,
        epcis=epcis,
        code_region=regs.index[0] if len(regs) else None,
        codes_departements=deps,
    )


def territoire_to_dict(t: Territoire) -> dict:
    return {
        "nom": t.nom,
        "epcis": t.epcis,
        "codes_communes": t.codes_communes,
    }
