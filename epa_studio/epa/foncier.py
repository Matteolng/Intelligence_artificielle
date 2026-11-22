"""Marché foncier agricole – DVF open data (DGFiP) via l'API Données foncières du Cerema.

Limites à rappeler dans l'étude :
- DVF ne couvre pas l'Alsace, la Moselle et Mayotte ;
- la typologie « terres et prés », « viticole »… est celle du Cerema (DV3F/DVF+) ;
- une mutation peut regrouper plusieurs parcelles et des biens de natures différentes :
  le prix à l'hectare est un indicateur, pas une valeur vénale d'expertise.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable

import numpy as np
import pandas as pd

from .config import DVF_CEREMA_API, DVF_DEPARTEMENTS_NON_COUVERTS, DVF_TYPES_AGRICOLES
from .http import disk_cache, get_json


@disk_cache("dvf")
def mutations_commune(code_insee: str, codes_typbien: tuple[str, ...], annee_min: int) -> list[dict]:
    rows: list[dict] = []
    params = {"code_insee": code_insee, "codtypbien": ",".join(codes_typbien), "anneemut_min": annee_min, "page_size": 500}
    url: str | None = DVF_CEREMA_API
    while url:
        d = get_json(url, params=params, limiter="cerema", timeout=120)
        rows.extend(d.get("results", []))
        nxt = d.get("next")
        url = nxt.replace("http://", "https://") if nxt else None
        params = None  # l'URL "next" contient déjà les paramètres
    return rows


def mutations_territoire(codes_communes: list[str], annee_min: int = 2014,
                         codes_typbien: tuple[str, ...] = tuple(DVF_TYPES_AGRICOLES),
                         progress: Callable[[float, str], None] | None = None) -> pd.DataFrame:
    out = []
    codes = [c for c in codes_communes if c[:2] not in DVF_DEPARTEMENTS_NON_COUVERTS and c[:3] not in DVF_DEPARTEMENTS_NON_COUVERTS]
    typ = tuple(sorted(codes_typbien))
    resultats: dict[str, list[dict]] = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {ex.submit(mutations_commune, c, typ, annee_min): c for c in codes}
        for i, fut in enumerate(as_completed(futures), start=1):
            resultats[futures[fut]] = fut.result()
            if progress:
                progress(i / max(1, len(codes)), f"DVF – {i}/{len(codes)} communes traitées")
    for c in codes:
        for m in resultats.get(c, []):
            out.append({
                "idmutation": m.get("idmutation"),
                "date": m.get("datemut"),
                "annee": m.get("anneemut"),
                "nature": m.get("libnatmut"),
                "code_commune": c,
                "codtypbien": m.get("codtypbien"),
                "type_bien": DVF_TYPES_AGRICOLES.get(str(m.get("codtypbien")), m.get("libtypbien")),
                "valeur_fonciere": pd.to_numeric(m.get("valeurfonc"), errors="coerce"),
                "surface_terrain_m2": pd.to_numeric(m.get("sterr"), errors="coerce"),
                "nb_parcelles": m.get("nbpar"),
                "nb_communes": m.get("nbcomm"),
            })
    if progress:
        progress(1.0, "Terminé")
    df = pd.DataFrame(out)
    if df.empty:
        return df
    df = df.drop_duplicates(subset="idmutation")
    df["surface_ha"] = df["surface_terrain_m2"] / 1e4
    df["prix_eur_ha"] = df["valeur_fonciere"] / df["surface_ha"]
    return df


def filtrer(df: pd.DataFrame, surface_min_ha: float = 0.5, prix_min: float = 100, prix_max: float = 100_000,
            ventes_seulement: bool = True) -> pd.DataFrame:
    """Filtre les mutations exploitables pour une analyse de prix (paramètres affichés dans l'étude)."""
    if df.empty:
        return df
    d = df.copy()
    if ventes_seulement:
        d = d[d["nature"].astype(str).str.startswith("Vente")]
    d = d[(d["surface_ha"] >= surface_min_ha) & d["prix_eur_ha"].between(prix_min, prix_max)]
    d = d[d["nb_communes"].fillna(1) <= 1]
    return d


def stats_prix(df: pd.DataFrame, by: list[str] | None = None) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    def agg(g: pd.DataFrame) -> pd.Series:
        w = g["surface_ha"].sum()
        return pd.Series({
            "mutations": len(g),
            "surface_ha": w,
            "prix_median_eur_ha": g["prix_eur_ha"].median(),
            "prix_q1_eur_ha": g["prix_eur_ha"].quantile(0.25),
            "prix_q3_eur_ha": g["prix_eur_ha"].quantile(0.75),
            "prix_moyen_pondere_eur_ha": g["valeur_fonciere"].sum() / w if w else np.nan,
        })

    if by:
        return df.groupby(by).apply(agg, include_groups=False).reset_index()
    return agg(df).to_frame().T
