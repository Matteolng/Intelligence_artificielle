"""Catalogue des sources interrogées par l'application et bibliographie générée à partir de celles réellement utilisées.

Titres relevés dans les GetCapabilities de la Géoplateforme IGN et sur les sites des producteurs (novembre 2026).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable, MutableMapping


@dataclass(frozen=True)
class Source:
    producteur: str
    titre: str
    millesime: str
    url: str

    def courte(self) -> str:
        return f"{self.producteur}, {self.titre} ({self.millesime})"


CATALOGUE: dict[str, Source] = {
    "geo": Source("DINUM / Etalab", "API Découpage administratif (communes, EPCI, population INSEE)", "consultation",
                  "https://geo.api.gouv.fr"),
    "ra2020": Source("Agreste – SSP, ministère de l'Agriculture", "Recensements agricoles 2010 et 2020, via l'Observatoire des territoires (ANCT)",
                     "2020", "https://www.observatoire-des-territoires.gouv.fr"),
    "sirene": Source("INSEE", "Répertoire SIRENE, via l'API Recherche d'entreprises (DINUM)", "consultation",
                     "https://recherche-entreprises.api.gouv.fr"),
    "agencebio": Source("Agence Bio", "Annuaire des opérateurs de l'agriculture biologique", "consultation",
                        "https://opendata.agencebio.org"),
    "inao": Source("INAO", "Aires géographiques des AOC/AOP et des IGP/IG", "2025", "https://www.data.gouv.fr"),
    "dvf": Source("DGFiP / Cerema", "Demandes de valeurs foncières (DVF), API Données foncières", "consultation",
                  "https://apidf-preprod.cerema.fr"),
    "sols": Source("INRAE – Gis Sol", "Les sols dominants de France métropolitaine – carte harmonisée (RRP 1/250 000)", "consultation",
                   "https://data.geopf.fr/wms-r/wms (INRAE_CARTE-SOLS)"),
    "ru_bdgsf": Source("INRAE – Gis Sol", "Carte de la réserve utile en eau issue de la Base de données géographique des sols "
                       "de France (1/1 000 000), doi:10.15454/JPB9RB", "consultation",
                       "https://geodata.inrae.fr/geoserver/ows (inra_bdgsf:bdgsf_classe_ru)"),
    "s2": Source("Copernicus / ESA", "Images Sentinel-2 niveau 2A (réflectance de surface), via le catalogue Earth Search "
                 "(Element 84) et AWS Open Data", "consultation", "https://earth-search.aws.element84.com/v1"),
    "asi": Source("Montero D. et al.", "A standardized catalogue of spectral indices to advance the use of remote sensing in Earth "
                  "system research, Scientific Data 10:197, doi:10.1038/s41597-023-02096-0", "2023",
                  "https://github.com/awesome-spectral-indices/awesome-spectral-indices"),
    "usgs_ndvi": Source("USGS", "NDVI, the Foundation for Remote Sensing Phenology (repères de valeurs du NDVI)", "consultation",
                        "https://www.usgs.gov/special-topics/remote-sensing-phenology/science/ndvi-foundation-remote-sensing-phenology"),
    "timesat": Source("Jönsson P., Eklundh L.", "TIMESAT – a program for analyzing time-series of satellite sensor data, "
                      "Computers & Geosciences 30:833-845 (méthode du seuil d'amplitude)", "2004",
                      "https://www.nateko.lu.se/sv/lars-eklundh/publikation/6c6391c2-1d30-4311-8cbc-5092ae9a369c"),
    "ortho": Source("IGN", "Photographies aériennes (ORTHOIMAGERY.ORTHOPHOTOS), date de prise de vue variable selon le département",
                    "consultation", "https://data.geopf.fr/wmts"),
    "plan_ign": Source("IGN", "Plan IGN v2", "consultation", "https://data.geopf.fr/wmts"),
    "osm": Source("Contributeurs OpenStreetMap", "Fond de carte OpenStreetMap", "consultation", "https://www.openstreetmap.org"),
    "otex": Source("Agreste – SSP (RA 2020), fichier publié par TACCT sur data.gouv.fr",
                   "Spécialisation territoriale de la production agricole par commune (OTEX en 12 postes)", "2020",
                   "https://www.data.gouv.fr/datasets/specialisation-territoriale-de-la-production-agricole-par-commune-en-2020-otex-en-12-postes"),
    "cartostat": Source("Agreste – SSP", "Export Cartostat / DISAR importé par l'utilisateur", "selon fichier importé",
                        "https://stats.agriculture.gouv.fr/cartostat"),
}


def _rpg(annee: str) -> Source:
    return Source("IGN / ASP", "Registre parcellaire graphique (RPG), Géoplateforme WFS", annee, "https://data.geopf.fr/wfs/ows")


def get(cle: str) -> Source:
    """Clé du catalogue, « rpg:AAAA » ou « clc:AAAA » pour un millésime. Clé inconnue → KeyError.
    Pour les fichiers data.gouv.fr suivis automatiquement (INAO, OTEX), la date de la version utilisée est ajoutée."""
    if cle in ("inao", "otex"):
        from dataclasses import replace

        try:
            from .catalogue import ressource

            d = ressource("inao_ao" if cle == "inao" else "otex")[1]
        except Exception:
            d = ""
        s = CATALOGUE[cle]
        if not d:
            return s
        # INAO : le millésime est celui de la version ; OTEX : il reste celui du recensement (2020)
        return replace(s, titre=f"{s.titre}, version du {d[8:10]}/{d[5:7]}/{d[:4]}", millesime=d[:4] if cle == "inao" else s.millesime)
    if cle.startswith("rpg:"):
        return _rpg(cle.split(":", 1)[1])
    if cle.startswith("clc:"):
        an = cle.split(":", 1)[1]
        return Source("Union européenne – Copernicus / SDES", "CORINE Land Cover – France métropolitaine", an,
                      f"https://data.geopf.fr/wms-r/wms (LANDCOVER.CLC{an[2:]}_FR)")
    return CATALOGUE[cle]


def citer(cle: str) -> str:
    return get(cle).courte()


def enregistrer(cle: str, state: MutableMapping | None = None) -> None:
    get(cle)  # valide la clé
    if state is None:
        import streamlit as st

        state = st.session_state
    state.setdefault("sources_utilisees", {})
    state["sources_utilisees"].setdefault(cle, date.today().strftime("%d/%m/%Y"))


def bibliographie(cles: Iterable[str] | dict[str, str]) -> list[str]:
    """Références triées et dédoublonnées : « Producteur (millésime). Titre. URL. Consulté le JJ/MM/AAAA. »"""
    dates = cles if isinstance(cles, dict) else {c: None for c in cles}
    out = set()
    for cle, d in dates.items():
        s = get(cle)
        ref = f"{s.producteur} ({s.millesime}). {s.titre}. {s.url}."
        out.add(ref + (f" Consulté le {d}." if d else ""))
    return sorted(out, key=str.casefold)
