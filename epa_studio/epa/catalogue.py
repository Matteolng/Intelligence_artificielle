"""Dernières versions des données, découvertes automatiquement chez les producteurs.

- RPG : catalogue WFS de la Géoplateforme (couches « RPG.AAAA » et « RPG.LATEST », dont le titre donne l'année).
- Couches annuelles WMS (RPG bio, prairies permanentes, Corine Land Cover) : catalogue WMS de la Géoplateforme.
- Fichiers data.gouv.fr (OTEX, INAO) : API data.gouv.fr, ressource CSV la plus récente du jeu de données.
Le catalogue est relu au plus tous les 7 jours (cache). Si un service ne répond pas, l'application garde les versions
connues lors du développement (epa.config) : elle continue de fonctionner, sans rien inventer.
"""
from __future__ import annotations

import re
import time

from .config import (GPF_WFS, GPF_WMS_RASTER, INAO_AIRES_PRODUITS_CSV, INAO_COMMUNES_AO_CSV, INAO_COMMUNES_IG_CSV,
                     OTEX_COMMUNES_CSV, RPG_LAYERS, WMS_LAYERS)
from .http import DataSourceError, disk_cache, get, get_json, memo

DATAGOUV = "https://www.data.gouv.fr/api/1/datasets"
# (jeu de données, URL connue en secours, motif du nom du fichier attendu : un fichier annexe ajouté au jeu est ignoré)
JEUX = {
    "otex": ("specialisation-territoriale-de-la-production-agricole-par-commune-en-2020-otex-en-12-postes", OTEX_COMMUNES_CSV,
             r"otex"),
    "inao_ao": ("aires-geographiques-des-aoc-aop", INAO_COMMUNES_AO_CSV, r"communes.?aires.?ao"),
    "inao_ig": ("aire-geographique-des-igp-et-des-ig", INAO_COMMUNES_IG_CSV, r"communes.?aires.?ig"),
    "inao_produits": ("aires-et-produits-aoc-aop-et-igp", INAO_AIRES_PRODUITS_CSV, r"aires.?produits"),
}
_REPLI: dict[str, float] = {}  # fichier → instant où sa dernière version n'a pas pu être lue (repli pendant 1 h)


# ---------------------------------------------------------------------------
# RPG (WFS)
# ---------------------------------------------------------------------------

def lire_rpg_wfs(caps: str) -> list[dict]:
    """Millésimes « parcelles_graphiques » du catalogue WFS, du plus récent au plus ancien."""
    out = {}
    for m in re.finditer(r"<Name>(RPG\.(\d{4}|LATEST):parcelles_graphiques)</Name>\s*<Title>([^<]*)</Title>", caps):
        nom, an, titre = m.groups()
        annee = int(an) if an.isdigit() else int((re.search(r"(20\d{2})", titre) or [None, 0])[1] or 0)
        if not annee:
            continue
        # « LATEST » et un millésime explicite peuvent coexister : on garde le nom explicite (cache plus sûr)
        if annee not in out or an.isdigit():
            out[annee] = {"annee": annee, "couche": nom, "codes": nom.replace("parcelles_graphiques", "codes_cultures")}
    return [out[a] for a in sorted(out, reverse=True)]


@disk_cache("catalogue")
def rpg_millesimes() -> list[dict]:
    caps = get(GPF_WFS, params={"SERVICE": "WFS", "REQUEST": "GetCapabilities", "VERSION": "2.0.0"}, timeout=120).text
    mil = lire_rpg_wfs(caps)
    if not mil:
        raise DataSourceError("Aucun millésime RPG trouvé dans le catalogue WFS.")
    return mil


@memo(3600)
def _rpg_ou_defaut() -> list[dict]:
    try:
        return rpg_millesimes()
    except Exception:  # service indisponible : versions connues
        return [{"annee": int(k[:4]), "couche": v, "codes": v.replace("parcelles_graphiques", "codes_cultures")} for k, v in RPG_LAYERS.items()]


def rpg_couches() -> dict[str, str]:
    """{libellé : couche WFS}, du plus récent au plus ancien ; le premier est la dernière édition."""
    mil = _rpg_ou_defaut()
    return {(f"{m['annee']} (dernière édition)" if i == 0 else str(m["annee"])): m["couche"] for i, m in enumerate(mil)}


def annee_rpg_recente() -> int:
    return _rpg_ou_defaut()[0]["annee"]


def annee_de_couche(couche: str) -> str:
    """Année réelle d'une couche RPG (résout « LATEST ») : sert de clé de cache."""
    m = re.search(r"RPG\.(\d{4})", couche)
    if m:
        return m.group(1)
    for x in _rpg_ou_defaut():
        if x["couche"] == couche:
            return str(x["annee"])
    return ""


def couche_codes_cultures() -> str:
    return _rpg_ou_defaut()[0]["codes"]


# ---------------------------------------------------------------------------
# Couches WMS annuelles
# ---------------------------------------------------------------------------

MOTIFS_WMS = {
    "rpg_bio": r"IGNF_RPG_PARCELLES-BIO_(\d{4})",
    "rpg_pp": r"IGNF_RPG_PRAIRIES-PERMANENTES_(\d{4})",
    "clc": r"LANDCOVER\.CLC(\d{2})_FR",
}
DEFAUTS_WMS = {"rpg_pac": ("LANDUSE.AGRICULTURE.LATEST", 2025), "rpg_bio": ("IGNF_RPG_PARCELLES-BIO_2025", 2025), "rpg_pp": ("IGNF_RPG_PRAIRIES-PERMANENTES_2025", 2025),
               "clc": ("LANDCOVER.CLC18_FR", 2018)}


def lire_wms_annuelles(caps: str) -> dict[str, tuple[str, int]]:
    out = {}
    noms = set(re.findall(r"<Name>([^<]+)</Name>", caps))
    for cle, motif in MOTIFS_WMS.items():
        best = None
        for n in noms:
            m = re.fullmatch(motif, n)
            if m:
                a = int(m.group(1))
                a = a + (1900 if a >= 90 else 2000) if a < 100 else a
                if best is None or a > best[1]:
                    best = (n, a)
        if best:
            out[cle] = best
    # RPG PAC : couche « LATEST », dont le titre donne l'édition (« Registre parcellaire graphique (RPG) édition 2025 »)
    m = re.search(r"<Name>LANDUSE\.AGRICULTURE\.LATEST</Name>\s*<Title>[^<]*?((?:19|20)\d{2})[^<]*</Title>", caps)
    if m:
        out["rpg_pac"] = ("LANDUSE.AGRICULTURE.LATEST", int(m.group(1)))
    return out


@disk_cache("catalogue")
def wms_annuelles() -> dict[str, tuple[str, int]]:
    caps = get(GPF_WMS_RASTER, params={"SERVICE": "WMS", "REQUEST": "GetCapabilities", "VERSION": "1.3.0"}, timeout=120).text
    return lire_wms_annuelles(caps)


@memo(3600)
def couche_annuelle(cle: str) -> tuple[str, int]:
    """(nom de couche, année) le plus récent publié, ou la version connue si le catalogue ne répond pas."""
    try:
        return wms_annuelles().get(cle) or DEFAUTS_WMS[cle]
    except Exception:
        return DEFAUTS_WMS[cle]


# Noms d'affichage stables (l'année réelle est donnée par couches_wms / couche_annuelle)
NOM_RPG_PAC = "RPG – parcelles PAC (dernière édition)"
NOM_RPG_BIO = "RPG – parcelles bio (dernière édition)"
NOM_RPG_PP = "RPG – prairies permanentes (dernière édition)"
NOM_CLC = "Corine Land Cover (dernier millésime)"


@memo(3600)
def couches_wms() -> dict[str, dict]:
    """Catalogue des couches de l'atlas, avec les couches annuelles mises à jour et leur année."""
    out = {}
    for nom, cfg in WMS_LAYERS.items():
        cfg = dict(cfg)
        if nom.startswith("RPG") and "parcelles PAC" in nom:
            (cfg["layer"], cfg["annee"]), nom = couche_annuelle("rpg_pac"), NOM_RPG_PAC
        elif nom.startswith("RPG") and "bio" in nom:
            (cfg["layer"], cfg["annee"]), nom = couche_annuelle("rpg_bio"), NOM_RPG_BIO
        elif nom.startswith("RPG") and "prairies" in nom:
            (cfg["layer"], cfg["annee"]), nom = couche_annuelle("rpg_pp"), NOM_RPG_PP
        elif nom.startswith("Corine Land Cover"):
            (cfg["layer"], cfg["annee"]), nom = couche_annuelle("clc"), NOM_CLC
        out[nom] = cfg
    return out


# ---------------------------------------------------------------------------
# data.gouv.fr
# ---------------------------------------------------------------------------

def choisir_ressource(meta: dict, nom: str = "") -> tuple[str, str] | None:
    """Ressource CSV la plus récemment modifiée d'un jeu de données data.gouv.fr dont le titre ou l'URL contient `nom`
    (expression régulière) : (url, date)."""
    res = [r for r in meta.get("resources", [])
           if (re.search(r"\.csv$", r.get("url", ""), re.I) or (r.get("format") or "").lower() == "csv")
           and re.search(nom, f"{r.get('title') or ''} {r.get('url', '')}", re.I)]
    if not res:
        return None
    r = max(res, key=lambda r: r.get("last_modified") or "")
    return r["url"], (r.get("last_modified") or "")[:10]


@disk_cache("catalogue")
def _meta_datagouv(slug: str) -> dict:
    return get_json(f"{DATAGOUV}/{slug}/")


@memo(3600)
def _derniere(cle: str) -> tuple[str, str]:
    slug, defaut, nom = JEUX[cle]
    try:
        r = choisir_ressource(_meta_datagouv(slug), nom)
        if r:
            return r
    except Exception:
        pass
    return defaut, ""


def ressource(cle: str) -> tuple[str, str]:
    """(url, date de mise à jour) de la dernière ressource ; URL connue (sans date) en secours."""
    return (JEUX[cle][1], "") if time.monotonic() - _REPLI.get(cle, -1e9) < 3600 else _derniere(cle)


def lire_avec_repli(cles: tuple[str, ...], lire):
    """Lit la dernière version des fichiers `cles` avec `lire(*urls)` ; si elle est illisible (structure changée par le
    producteur), relit la version connue et le signale à la bibliographie (la date de version n'est alors plus citée)."""
    urls = tuple(ressource(c)[0] for c in cles)
    connues = tuple(JEUX[c][1] for c in cles)
    try:
        return lire(*urls)
    except Exception:
        if urls == connues:
            raise
        out = lire(*connues)  # lève si la version connue est elle aussi illisible
        _REPLI.update({c: time.monotonic() for c in cles})
        return out
