"""Chiffres clés RA 2020 comparés : périmètre d'étude / département / France (somme des départements)."""
from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd

from . import agreste

LIGNE_FRANCE = "France (somme des départements)"
ECHELLES = ("Périmètre", "Département", "Région", "France")


def departement_reference(communes: gpd.GeoDataFrame, code_site: str | None = None) -> str:
    """Département de la commune du site si connue, sinon celui qui couvre la plus grande surface du périmètre."""
    c = communes.copy()
    c["code"] = c["code"].astype(str)
    if code_site and (c["code"] == str(code_site)).any():
        return str(c.loc[c["code"] == str(code_site), "codeDepartement"].iloc[0])
    surf = c["surface_ha"] if "surface_ha" in c else c.to_crs(2154).area
    return str(c.assign(_s=surf).groupby("codeDepartement")["_s"].sum().idxmax())


def comparaison(df_com: pd.DataFrame, df_dep: pd.DataFrame, codes_communes: list[str], code_dep: str,
                label_perimetre: str = "Périmètre d'étude", df_reg: pd.DataFrame | None = None,
                code_reg: str | None = None) -> pd.DataFrame:
    """Quatre échelles : périmètre (agrégat des communes), département, région (si fournie), France = somme des départements.

    Les communes sans donnée (secret statistique) sont exclues des sommes et comptées dans une colonne dédiée.
    """
    sel = df_com[df_com["codgeo"].astype(str).isin([str(c) for c in codes_communes])]
    lignes = [
        agreste.synthese(sel, label_perimetre),
        agreste.ligne_reference(df_dep, code_dep, f"Département ({code_dep})"),
    ]
    if df_reg is not None and code_reg:
        lignes.append(agreste.ligne_reference(df_reg, code_reg, f"Région ({code_reg})"))
    fr = agreste.synthese(df_dep, LIGNE_FRANCE)
    fr["Communes sans donnée (secret ou absence)"] = None
    lignes.append(fr)
    out = pd.DataFrame(lignes)
    return out.replace({np.inf: np.nan, -np.inf: np.nan})
