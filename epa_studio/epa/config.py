"""Configuration centrale d'EPA Studio.

Toutes les URL de services publics utilisées par l'application sont regroupées
ici, avec la source officielle correspondante. Les identifiants de couches ont
été relevés dans les GetCapabilities de la Géoplateforme IGN (novembre 2026).
"""
from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "EPA Studio"
APP_TAGLINE = "État initial de l'économie agricole pour les études préalables agricoles"
APP_VERSION = "1.0.0"
USER_AGENT = f"EPA-Studio/{APP_VERSION} (outil open source d'aide aux etudes prealables agricoles)"

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = Path(os.environ.get("EPA_CACHE_DIR", Path.home() / ".cache" / "epa_studio"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)
# Cache livré avec l'application : tables nationales préchargées par scripts/precharger_demo.py (lecture seule)
DEMO_CACHE_DIR = Path(os.environ.get("EPA_DEMO_CACHE_DIR", BASE_DIR.parent / "demo_cache"))

# Durée de validité du cache disque (jours) par famille de données
CACHE_TTL_DAYS = {
    "geo": 30,
    "rpg": 60,
    "odt": 60,
    "sirene": 7,
    "bio": 14,
    "inao": 60,
    "dvf": 30,
    "wms": 30,
    "s2": 90,
    "catalogue": 7,
}

# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------
GEO_API = "https://geo.api.gouv.fr"  # API Découpage administratif (DINUM / Etalab)
GPF_WFS = "https://data.geopf.fr/wfs/ows"  # Géoplateforme IGN – WFS
GPF_WMS_RASTER = "https://data.geopf.fr/wms-r/wms"  # Géoplateforme IGN – WMS raster
GPF_WMS_VECTOR = "https://data.geopf.fr/wms-v/ows"  # Géoplateforme IGN – WMS vecteur
GPF_WMTS = "https://data.geopf.fr/wmts"
RECHERCHE_ENTREPRISES = "https://recherche-entreprises.api.gouv.fr/search"  # API Recherche d'entreprises (DINUM)
AGENCE_BIO_API = "https://opendata.agencebio.org/api/gouv/operateurs/"  # Annuaire Agence Bio
DVF_CEREMA_API = "https://apidf-preprod.cerema.fr/dvf_opendata/mutations/"  # API Données foncières Cerema (DVF open data)
OTEX_COMMUNES_CSV = (  # Agreste RA 2020, OTEX communale en 12 postes, publié sur data.gouv.fr par TACCT (09/07/2026)
    "https://static.data.gouv.fr/resources/specialisation-territoriale-de-la-production-agricole-par-commune-en-2020-otex-en-12-postes/"
    "20260709-091116/otex-12-postes.csv"
)
ODT_BASE = "https://www.observatoire-des-territoires.gouv.fr"  # Observatoire des territoires (ANCT)

# INAO – fichiers publiés sur data.gouv.fr (licence ouverte)
INAO_COMMUNES_AO_CSV = (
    "https://static.data.gouv.fr/resources/aires-geographiques-des-aoc-aop/"
    "20251009-122320/2025-10-09-comagri-communes-aires-ao.csv"
)
INAO_COMMUNES_IG_CSV = (
    "https://static.data.gouv.fr/resources/aire-geographique-des-igp-et-des-ig/"
    "20251009-122625/2025-10-09-comagri-communes-aires-ig.csv"
)
INAO_AIRES_PRODUITS_CSV = (
    "https://static.data.gouv.fr/resources/aires-et-produits-aoc-aop-et-igp/"
    "20251009-122906/2025-03-10-comagri-aires-produits.csv"
)

# RPG – couches WFS (Géoplateforme). LATEST = édition 2025 au moment du développement.
RPG_LAYERS = {
    "2025 (dernière édition)": "RPG.LATEST:parcelles_graphiques",
    "2024": "RPG.2024:parcelles_graphiques",
    "2023": "RPG.2023:parcelles_graphiques",
    "2022": "RPG.2022:parcelles_graphiques",
    "2021": "RPG.2021:parcelles_graphiques",
    "2020": "RPG.2020:parcelles_graphiques",
    "2019": "RPG.2019:parcelles_graphiques",
    "2018": "RPG.2018:parcelles_graphiques",
    "2017": "RPG.2017:parcelles_graphiques",
    "2016": "RPG.2016:parcelles_graphiques",
    "2015": "RPG.2015:parcelles_graphiques",
}
RPG_PAGE_SIZE = 5000

# Groupes de cultures du RPG (nomenclature PAC, table codes_cultures du RPG 2025)
RPG_GROUPES = {
    1: "Blé tendre",
    2: "Maïs grain et ensilage",
    3: "Orge",
    4: "Autres céréales",
    5: "Colza",
    6: "Tournesol",
    7: "Autres oléagineux",
    8: "Protéagineux",
    9: "Plantes à fibres",
    11: "Gel (surfaces gelées sans production)",
    14: "Riz",
    15: "Légumineuses à grains",
    16: "Fourrage",
    17: "Estives et landes",
    18: "Prairies permanentes",
    19: "Prairies temporaires",
    20: "Vergers",
    21: "Vignes",
    22: "Fruits à coque",
    23: "Oliviers",
    24: "Autres cultures industrielles",
    25: "Légumes ou fleurs",
    26: "Canne à sucre",
    28: "Divers",
}

# Regroupement en grandes familles (pour les synthèses et cartes)
RPG_FAMILLES = {
    "Céréales": [1, 2, 3, 4, 14],
    "Oléoprotéagineux": [5, 6, 7, 8, 15],
    "Fourrages et prairies temporaires": [16, 19],
    "Prairies permanentes, estives et landes": [17, 18],
    "Cultures pérennes (vignes, vergers…)": [20, 21, 22, 23],
    "Légumes, fleurs et cultures industrielles": [9, 24, 25, 26],
    "Gel et divers": [11, 28],
}

FAMILLE_COLORS = {
    "Céréales": "#E3B505",
    "Oléoprotéagineux": "#F28C28",
    "Fourrages et prairies temporaires": "#8CC084",
    "Prairies permanentes, estives et landes": "#3E7C17",
    "Cultures pérennes (vignes, vergers…)": "#8E3B46",
    "Légumes, fleurs et cultures industrielles": "#4F86C6",
    "Gel et divers": "#A0A0A0",
}

# ---------------------------------------------------------------------------
# Observatoire des territoires – indicateurs RA 2020 (source : Agreste)
# ---------------------------------------------------------------------------
ODT_RA2020_INDICATEURS = {
    "exp2020": {
        "page": "nombre-dexploitations-agricoles",
        "libelle": "Nombre d'exploitations agricoles (2020)",
        "unite": "exploitations",
    },
    "sau2020": {
        "page": "surface-agricole-utilisee-sau",
        "libelle": "Surface agricole utilisée (2020)",
        "unite": "ha",
    },
    "evol_exp": {
        "page": "evolution-du-nombre-dexploitations-agricoles-entre-2010-et-2020",
        "libelle": "Évolution du nombre d'exploitations 2010-2020",
        "unite": "%",
    },
    "evol_sau": {
        "page": "evolution-surface-agricole-utilisee-sau-2010-2020",
        "libelle": "Évolution de la SAU 2010-2020",
        "unite": "%",
    },
}

# ---------------------------------------------------------------------------
# Filières amont / aval – codes NAF rév. 2 (libellés officiels INSEE dans data/naf2008_n5.csv)
# ---------------------------------------------------------------------------
NAF_PRODUCTION_AGRICOLE = [
    "01.11Z", "01.12Z", "01.13Z", "01.14Z", "01.15Z", "01.16Z", "01.19Z",
    "01.21Z", "01.22Z", "01.23Z", "01.24Z", "01.25Z", "01.26Z", "01.27Z", "01.28Z", "01.29Z",
    "01.30Z",
    "01.41Z", "01.42Z", "01.43Z", "01.44Z", "01.45Z", "01.46Z", "01.47Z", "01.49Z",
    "01.50Z",
]

FILIERES = {
    "Services et approvisionnement (amont)": {
        "description": "Travaux agricoles, ETA/CUMA, services à l'élevage, commerce de machines, fabrication d'aliments du bétail, vétérinaires.",
        "naf": ["01.61Z", "01.62Z", "01.63Z", "01.64Z", "10.91Z", "20.15Z", "28.30Z", "46.61Z", "75.00Z"],
    },
    "Première transformation – viandes": {
        "description": "Abattage et transformation des viandes de boucherie et de volailles, charcuterie.",
        "naf": ["10.11Z", "10.12Z", "10.13A", "10.13B"],
    },
    "Première transformation – lait": {
        "description": "Laiteries, fromageries, beurreries.",
        "naf": ["10.51A", "10.51B", "10.51C", "10.51D", "10.52Z"],
    },
    "Première transformation – grains, fruits et légumes": {
        "description": "Meunerie, travail du grain, transformation des fruits, légumes et pommes de terre, huiles, sucre.",
        "naf": ["10.31Z", "10.32Z", "10.39A", "10.39B", "10.41A", "10.41B", "10.61A", "10.61B", "10.62Z", "10.81Z"],
    },
    "Boissons (vins, cidres, spiritueux)": {
        "description": "Vinification, cidres, eaux-de-vie, malterie et brasserie.",
        "naf": ["11.01Z", "11.02A", "11.02B", "11.03Z", "11.05Z", "11.06Z"],
    },
    "Commerce de gros de produits agricoles (collecte, négoce)": {
        "description": "Collecte et négoce de céréales, animaux vivants, fruits et légumes, produits laitiers, viandes.",
        "naf": ["46.11Z", "46.21Z", "46.22Z", "46.23Z", "46.24Z", "46.31Z", "46.32A", "46.32B", "46.33Z", "46.34Z"],
    },
}

# Catégories juridiques INSEE (vérifiées par interrogation de l'API Recherche d'entreprises)
NATURE_JURIDIQUE_AGRI = {
    "6316": "CUMA",
    "6317": "Société coopérative agricole",
    "6318": "Union de sociétés coopératives agricoles",
    "6533": "GAEC",
    "6598": "EARL",
}

# Tranches d'effectifs salariés (nomenclature INSEE)
TRANCHES_EFFECTIFS = {
    "NN": "Non employeuse / non renseigné",
    "00": "0 salarié",
    "01": "1 ou 2 salariés",
    "02": "3 à 5 salariés",
    "03": "6 à 9 salariés",
    "11": "10 à 19 salariés",
    "12": "20 à 49 salariés",
    "21": "50 à 99 salariés",
    "22": "100 à 199 salariés",
    "31": "200 à 249 salariés",
    "32": "250 à 499 salariés",
    "41": "500 à 999 salariés",
    "42": "1 000 à 1 999 salariés",
    "51": "2 000 à 4 999 salariés",
    "52": "5 000 à 9 999 salariés",
    "53": "10 000 salariés et plus",
}
# Borne basse / haute pour une estimation d'effectifs (fourchette, pas une valeur exacte)
TRANCHES_BORNES = {
    "00": (0, 0), "01": (1, 2), "02": (3, 5), "03": (6, 9), "11": (10, 19), "12": (20, 49),
    "21": (50, 99), "22": (100, 199), "31": (200, 249), "32": (250, 499), "41": (500, 999),
    "42": (1000, 1999), "51": (2000, 4999), "52": (5000, 9999), "53": (10000, 10000),
}

# ---------------------------------------------------------------------------
# DVF – typologie des biens (DV3F / DVF+ Cerema) pour les terrains agricoles
# ---------------------------------------------------------------------------
DVF_TYPES_AGRICOLES = {
    "2313": "Terres et prés",
    "2311": "Terrain viticole",
    "2312": "Terrain verger",
    "2319": "Terrain agricole mixte",
}
DVF_DEPARTEMENTS_NON_COUVERTS = {"57", "67", "68", "976"}  # Alsace, Moselle, Mayotte (source : DGFiP / data.gouv.fr)

# ---------------------------------------------------------------------------
# Couches cartographiques (WMS Géoplateforme)
# ---------------------------------------------------------------------------
WMS_LAYERS = {
    # --- Agriculture
    "RPG 2025 – parcelles PAC": {"url": GPF_WMS_RASTER, "layer": "LANDUSE.AGRICULTURE.LATEST", "theme": "Agriculture", "opacity": 0.7},
    "RPG 2025 – parcelles bio": {"url": GPF_WMS_RASTER, "layer": "IGNF_RPG_PARCELLES-BIO_2025", "theme": "Agriculture", "opacity": 0.8},
    "RPG 2025 – prairies permanentes": {"url": GPF_WMS_RASTER, "layer": "IGNF_RPG_PRAIRIES-PERMANENTES_2025", "theme": "Agriculture", "opacity": 0.7},
    "AOC viticoles – délimitation parcellaire (INAO)": {"url": GPF_WMS_VECTOR, "layer": "INAO-AOC_SYMBO_BDD_FXX_WM_WMS", "theme": "Agriculture", "opacity": 0.6},
    "Zones agricoles protégées (ZAP)": {"url": GPF_WMS_VECTOR, "layer": "agricole", "theme": "Agriculture", "opacity": 0.7},
    "Sols dominants (INRAE)": {"url": GPF_WMS_RASTER, "layer": "INRAE_CARTE-SOLS", "theme": "Agriculture", "opacity": 0.6},
    "Prairies sensibles Natura 2000 (BCAE)": {"url": GPF_WMS_VECTOR, "layer": "PRAIRIES.SENSIBLES.BCAE", "theme": "Agriculture", "opacity": 0.7},
    # --- Occupation du sol
    "Corine Land Cover 2018": {"url": GPF_WMS_RASTER, "layer": "LANDCOVER.CLC18_FR", "theme": "Occupation du sol", "opacity": 0.6},
    "OCS GE 2021-2023 – couverture": {"url": GPF_WMS_RASTER, "layer": "OCSGE.COUVERTURE.2021-2023", "theme": "Occupation du sol", "opacity": 0.6},
    "OCS GE 2021-2023 – usage": {"url": GPF_WMS_RASTER, "layer": "OCSGE.USAGE.2021-2023", "theme": "Occupation du sol", "opacity": 0.6},
    "Parcellaire cadastral (PCI)": {"url": GPF_WMS_RASTER, "layer": "CADASTRALPARCELS.PARCELLAIRE_EXPRESS", "theme": "Occupation du sol", "opacity": 0.8},
    # --- Urbanisme
    "Zonage des documents d'urbanisme (GPU)": {"url": GPF_WMS_VECTOR, "layer": "zone_secteur", "theme": "Urbanisme", "opacity": 0.6},
    "Servitudes d'utilité publique (GPU)": {"url": GPF_WMS_VECTOR, "layer": "sup", "theme": "Urbanisme", "opacity": 0.6},
    # --- Environnement
    "Natura 2000 – Directive Habitats (SIC/ZSC)": {"url": GPF_WMS_VECTOR, "layer": "Patrinat_SIC_France", "theme": "Environnement", "opacity": 0.6},
    "Natura 2000 – Directive Oiseaux (ZPS)": {"url": GPF_WMS_VECTOR, "layer": "Patrinat_ZPS_France", "theme": "Environnement", "opacity": 0.6},
    "ZNIEFF de type I": {"url": GPF_WMS_VECTOR, "layer": "Patrinat_ZNIEFF1_France", "theme": "Environnement", "opacity": 0.6},
    "ZNIEFF de type II": {"url": GPF_WMS_VECTOR, "layer": "Patrinat_ZNIEFF2_France", "theme": "Environnement", "opacity": 0.5},
    "Parcs naturels régionaux": {"url": GPF_WMS_VECTOR, "layer": "Patrinat_PNR_France", "theme": "Environnement", "opacity": 0.5},
    "Arrêtés de protection de biotope": {"url": GPF_WMS_VECTOR, "layer": "Patrinat_APB_France", "theme": "Environnement", "opacity": 0.6},
    "Zones de répartition des eaux (ZRE)": {"url": GPF_WMS_VECTOR, "layer": "EAU.ZRE", "theme": "Environnement", "opacity": 0.5},
    "Cours d'eau BCAE – bandes tampons": {"url": GPF_WMS_RASTER, "layer": "HYDROGRAPHY.BCAE.LATEST", "theme": "Environnement", "opacity": 0.8},
    # --- Énergie / solaire
    "Potentiel solaire au sol (Cerema/IGN)": {"url": GPF_WMS_VECTOR, "layer": "POTENTIEL.SOLAIRE.SOL", "theme": "Énergie", "opacity": 0.6},
    "Friches susceptibles d'accueillir du PV": {"url": GPF_WMS_VECTOR, "layer": "POTENTIEL.SOLAIRE.FRICHE", "theme": "Énergie", "opacity": 0.7},
    "Projets de zones d'accélération ENR (ZAER)": {"url": GPF_WMS_VECTOR, "layer": "projets_zones_acceleration_energies_renouvelables_zaer_wms", "theme": "Énergie", "opacity": 0.6},
    "Zones exclues des ZAER sauf toiture (OFB)": {"url": GPF_WMS_VECTOR, "layer": "OFB_INTERDICTION-ZAER-SAUF-TOITURE", "theme": "Énergie", "opacity": 0.6},
    "Capacités d'accueil S3REnR (MW)": {"url": GPF_WMS_VECTOR, "layer": "CAPACITE.ACCUEIL.ELECTRIQUE", "theme": "Énergie", "opacity": 0.8},
    "Contraintes – pentes (ENR)": {"url": GPF_WMS_VECTOR, "layer": "ENR.PERIMETRE.PENTE", "theme": "Énergie", "opacity": 0.6},
}

BASEMAPS = {
    "Plan IGN": {
        "tiles": GPF_WMTS + "?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2"
        "&STYLE=normal&TILEMATRIXSET=PM&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&FORMAT=image/png",
        "attr": "© IGN – Géoplateforme",
    },
    "Photographies aériennes IGN": {
        "tiles": GPF_WMTS + "?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=ORTHOIMAGERY.ORTHOPHOTOS"
        "&STYLE=normal&TILEMATRIXSET=PM&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&FORMAT=image/jpeg",
        "attr": "© IGN – Géoplateforme",
    },
    "OpenStreetMap": {
        "tiles": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        "attr": "© contributeurs OpenStreetMap",
    },
}

# Palette de l'interface
COLORS = {
    "primary": "#1F5F3F",
    "primary_light": "#E8F1EA",
    "accent": "#C8A13A",
    "territoire": "#1F5F3F",
    "emprise": "#C0392B",
    "text_muted": "#5F6B66",
}
