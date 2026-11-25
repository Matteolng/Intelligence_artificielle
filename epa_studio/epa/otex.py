"""Orientation technico-économique (OTEX) dominante par commune, recensement agricole 2020.

Source : Agreste – SSP, RA 2020, « Spécialisation territoriale de la production agricole par commune en 2020
(OTEX en 12 postes) », fichier publié sur data.gouv.fr par TACCT (mis à jour le 09/07/2026).
"""
from __future__ import annotations

import io

import pandas as pd

from .config import OTEX_COMMUNES_CSV
from .http import DataSourceError, disk_cache, get_bytes


def lire_otex(contenu: bytes) -> pd.DataFrame:
    """Colonnes `codgeo` (code INSEE sur 5 caractères) et `otex` (libellé en 12 postes)."""
    d = pd.read_csv(io.BytesIO(contenu), sep=";", dtype=str)
    if not {"code_geographique", "otex_12_postes"} <= set(d.columns):
        raise DataSourceError("Fichier OTEX : colonnes attendues absentes (code_geographique, otex_12_postes).")
    out = d[["code_geographique", "otex_12_postes"]].rename(columns={"code_geographique": "codgeo", "otex_12_postes": "otex"})
    out["codgeo"] = out["codgeo"].str.strip().str.zfill(5)
    return out.drop_duplicates("codgeo")


@disk_cache("odt")
def _otex(url: str) -> pd.DataFrame:
    return lire_otex(get_bytes(url))


def otex_communes() -> pd.DataFrame:
    """Dernière version publiée sur data.gouv.fr (URL relue par le catalogue), mise en cache par URL."""
    from .catalogue import ressource

    return _otex(ressource("otex")[0])
