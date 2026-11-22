"""Filières amont et aval – API Recherche d'entreprises (données SIRENE / INSEE, RNE / INPI).

Les établissements sont filtrés par code NAF de l'activité principale et par
localisation (EPCI ou communes du territoire). Le code NAF déclaré ne reflète
pas toujours l'activité réelle : la liste doit être relue par le chargé d'études.
"""
from __future__ import annotations

from typing import Callable

import pandas as pd

from .config import DATA_DIR, FILIERES, NAF_PRODUCTION_AGRICOLE, NATURE_JURIDIQUE_AGRI, RECHERCHE_ENTREPRISES, TRANCHES_BORNES, TRANCHES_EFFECTIFS
from .http import disk_cache, get_json

PER_PAGE = 25
MAX_PAGES = 40  # garde-fou : 1 000 unités légales par requête


def naf_libelles() -> dict[str, str]:
    df = pd.read_csv(DATA_DIR / "naf2008_n5.csv", dtype=str)
    return dict(zip(df["code"], df["libelle"]))


def _zone_params(codes_epci: list[str] | None, codes_communes: list[str] | None) -> dict:
    if codes_epci:
        return {"epci": ",".join(codes_epci)}
    return {"code_commune": ",".join(codes_communes or [])}


def _search(params: dict) -> dict:
    return get_json(RECHERCHE_ENTREPRISES, params=params, limiter="recherche-entreprises", timeout=60)


@disk_cache("sirene")
def compter(naf: str, zone_key: tuple[tuple[str, ...], tuple[str, ...]]) -> int:
    codes_epci, codes_communes = list(zone_key[0]), list(zone_key[1])
    params = {"activite_principale": naf, "etat_administratif": "A", "per_page": 1, "page": 1}
    params.update(_zone_params(codes_epci, codes_communes))
    d = _search(params)
    return int(d.get("total_results") or 0)


@disk_cache("sirene")
def etablissements(naf_codes: tuple[str, ...], zone_key: tuple[tuple[str, ...], tuple[str, ...]],
                   nature_juridique: str | None = None) -> pd.DataFrame:
    """Établissements actifs (localisés dans la zone) pour une liste de codes NAF ou une catégorie juridique."""
    codes_epci, codes_communes = list(zone_key[0]), list(zone_key[1])
    zone_communes = set(codes_communes)
    params: dict = {"etat_administratif": "A", "per_page": PER_PAGE}
    if naf_codes:
        params["activite_principale"] = ",".join(naf_codes)
    if nature_juridique:
        params["nature_juridique"] = nature_juridique
    params.update(_zone_params(codes_epci, codes_communes))
    rows: list[dict] = []
    page, total_pages = 1, 1
    while page <= min(total_pages, MAX_PAGES):
        params["page"] = page
        d = _search(params)
        total_pages = int(d.get("total_pages") or 1)
        for ul in d.get("results", []):
            etabs = ul.get("matching_etablissements") or []
            if not etabs and ul.get("siege"):
                etabs = [ul["siege"]]
            for e in etabs:
                if e.get("etat_administratif") not in (None, "A"):
                    continue
                if zone_communes and str(e.get("commune")) not in zone_communes:
                    continue
                # l'API sélectionne l'unité légale ; on ne garde que les établissements exerçant l'activité visée
                if naf_codes and (e.get("activite_principale") or ul.get("activite_principale")) not in naf_codes:
                    continue
                rows.append({
                    "siret": e.get("siret"),
                    "siren": ul.get("siren"),
                    "nom": ul.get("nom_complet"),
                    "enseigne": ", ".join(e.get("liste_enseignes") or []) or None,
                    "naf": e.get("activite_principale") or ul.get("activite_principale"),
                    "nature_juridique": ul.get("nature_juridique"),
                    "tranche_effectif": e.get("tranche_effectif_salarie") or "NN",
                    "annee_effectif": e.get("annee_tranche_effectif_salarie"),
                    "est_siege": e.get("est_siege"),
                    "adresse": e.get("adresse"),
                    "code_commune": e.get("commune"),
                    "commune": e.get("libelle_commune"),
                    "latitude": pd.to_numeric(e.get("latitude"), errors="coerce"),
                    "longitude": pd.to_numeric(e.get("longitude"), errors="coerce"),
                    "date_creation": e.get("date_creation"),
                    "bio": bool(e.get("liste_id_bio")),
                })
        page += 1
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.drop_duplicates(subset="siret")
    return df


def _decorer(df: pd.DataFrame, categorie: str) -> pd.DataFrame:
    if df.empty:
        return df
    lib = naf_libelles()
    d = df.copy()
    d["categorie"] = categorie
    d["libelle_naf"] = d["naf"].map(lib)
    d["effectif"] = d["tranche_effectif"].map(TRANCHES_EFFECTIFS).fillna("Non renseigné")
    d["eff_min"] = d["tranche_effectif"].map(lambda t: TRANCHES_BORNES.get(t, (0, 0))[0])
    d["eff_max"] = d["tranche_effectif"].map(lambda t: TRANCHES_BORNES.get(t, (0, 0))[1])
    d["forme"] = d["nature_juridique"].map(NATURE_JURIDIQUE_AGRI)
    return d


def filieres_territoire(codes_epci: list[str] | None, codes_communes: list[str],
                        progress: Callable[[float, str], None] | None = None) -> pd.DataFrame:
    """Tous les établissements amont/aval du territoire + coopératives agricoles et CUMA."""
    zone_key = (tuple(sorted(codes_epci or [])), tuple(sorted(codes_communes)))
    parts = []
    cats = list(FILIERES.items())
    n = len(cats) + 3
    for i, (cat, meta) in enumerate(cats):
        if progress:
            progress(i / n, f"Recherche : {cat}")
        parts.append(_decorer(etablissements(tuple(meta["naf"]), zone_key), cat))
    for j, nj in enumerate(("6316", "6317", "6318")):
        if progress:
            progress((len(cats) + j) / n, f"Recherche : {NATURE_JURIDIQUE_AGRI[nj]}")
        parts.append(_decorer(etablissements(tuple(), zone_key, nature_juridique=nj), "Autres coopératives agricoles et CUMA"))
    if progress:
        progress(1.0, "Terminé")
    parts = [p for p in parts if not p.empty]
    if not parts:
        return pd.DataFrame()
    df = pd.concat(parts, ignore_index=True)
    # un établissement coopératif peut aussi apparaître dans une catégorie NAF : on garde la catégorie NAF
    df["_coop"] = df["categorie"].eq("Autres coopératives agricoles et CUMA")
    df = df.sort_values("_coop").drop_duplicates(subset="siret", keep="first").drop(columns="_coop")
    return df.reset_index(drop=True)


def production_par_naf(codes_epci: list[str] | None, codes_communes: list[str],
                       progress: Callable[[float, str], None] | None = None) -> pd.DataFrame:
    """Nombre d'unités légales actives par code NAF de production agricole (division 01) sur la zone."""
    zone_key = (tuple(sorted(codes_epci or [])), tuple(sorted(codes_communes)))
    lib = naf_libelles()
    rows = []
    for i, naf in enumerate(NAF_PRODUCTION_AGRICOLE):
        if progress:
            progress(i / len(NAF_PRODUCTION_AGRICOLE), f"Comptage NAF {naf}")
        rows.append({"naf": naf, "libelle": lib.get(naf, naf), "unites_legales_actives": compter(naf, zone_key)})
    if progress:
        progress(1.0, "Terminé")
    df = pd.DataFrame(rows)
    df = df[df["unites_legales_actives"] > 0].sort_values("unites_legales_actives", ascending=False)
    tot = df["unites_legales_actives"].sum()
    df["part_pct"] = 100 * df["unites_legales_actives"] / tot if tot else 0
    return df.reset_index(drop=True)


def synthese_filieres(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["categorie", "etablissements", "effectif_min", "effectif_max"])
    g = df.groupby("categorie", as_index=False).agg(
        etablissements=("siret", "count"), effectif_min=("eff_min", "sum"), effectif_max=("eff_max", "sum"),
        employeurs=("eff_max", lambda s: int((s > 0).sum())),
    )
    return g.sort_values("etablissements", ascending=False).reset_index(drop=True)
