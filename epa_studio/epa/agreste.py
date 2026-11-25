"""Recensement agricole 2020 (Agreste) – via les téléchargements open data de l'Observatoire des territoires.

Les fichiers sont ceux proposés par le bouton « Télécharger » des fiches indicateurs
de l'Observatoire des territoires (ANCT), source Agreste – RA 2020. Les données sont
localisées au siège / lieu principal de production de l'exploitation : elles
doivent être interprétées avec prudence à l'échelle communale.

Les indicateurs plus détaillés (OTEX, PBS, UGB, UTA, âge des chefs…) sont
consultables sur Cartostat (stats.agriculture.gouv.fr/cartostat) et DISAR ; leurs
exports peuvent être importés dans l'application via `lire_fichier_utilisateur`.
"""
from __future__ import annotations

import html
import io
import re

import numpy as np
import pandas as pd

from .config import ODT_BASE, ODT_RA2020_INDICATEURS
from .http import DataSourceError, disk_cache, get, get_bytes, memo

NIVEAUX = {"commune": r"Communes \(\d{4}\)", "epci": r"EPCI \( ?\d{4}\)", "departement": r"Départements", "region": r"Régions \(2016\)"}


@disk_cache("odt")
def liens_telechargement(page: str) -> dict[str, str]:
    """Liens « Télécharger » publiés sur une fiche indicateur de l'Observatoire des territoires."""
    r = get(f"{ODT_BASE}/{page}", timeout=60)
    opts = re.findall(r'<option value="([^"]+GC_API_download[^"]+)"[^>]*>([^<]+)</option>', r.text)
    liens: dict[str, str] = {}
    for url, label in opts:
        label = html.unescape(label).strip()
        url = html.unescape(url)
        for niveau, pat in NIVEAUX.items():
            if niveau not in liens and re.search(pat, label) and "par communes" not in label:
                liens[niveau] = url
    if not liens:
        raise DataSourceError(f"Aucun lien de téléchargement trouvé sur {ODT_BASE}/{page}")
    return liens


def lire_export_geoclip(content: bytes) -> pd.DataFrame:
    """Lit un export xlsx Geoclip (Observatoire des territoires, Cartostat…)."""
    raw = pd.read_excel(io.BytesIO(content), sheet_name=0, header=None, dtype=str)
    header_row = None
    for i in range(min(30, len(raw))):
        vals = [str(v).strip().lower() for v in raw.iloc[i].tolist()]
        if "codgeo" in vals:
            header_row = i
            break
    if header_row is None:
        raise DataSourceError("Format d'export non reconnu (colonne 'codgeo' absente).")
    df = raw.iloc[header_row + 1 :].copy()
    df.columns = [str(c).strip() for c in raw.iloc[header_row].tolist()]
    df = df.dropna(subset=["codgeo"])
    return df.reset_index(drop=True)


@disk_cache("odt")
def indicateur_odt(code: str, niveau: str) -> pd.DataFrame:
    meta = ODT_RA2020_INDICATEURS[code]
    liens = liens_telechargement(meta["page"])
    if niveau not in liens:
        raise DataSourceError(f"Niveau {niveau} indisponible pour {code}")
    df = lire_export_geoclip(get_bytes(liens[niveau], timeout=240))
    col = code if code in df.columns else df.columns[-1]
    out = df[["codgeo", "libgeo", col]].rename(columns={col: code})
    out[code] = pd.to_numeric(out[code], errors="coerce")
    return out


@memo(3600)
def ra2020(niveau: str) -> pd.DataFrame:
    """Table des 4 indicateurs RA 2020 de l'Observatoire des territoires pour un niveau géographique."""
    base = None
    for code in ODT_RA2020_INDICATEURS:
        d = indicateur_odt(code, niveau)
        base = d if base is None else base.merge(d.drop(columns=["libgeo"]), on="codgeo", how="outer")
    return base


def _reconstitue_2010(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["exp2010_estime"] = d["exp2020"] / (1 + d["evol_exp"] / 100)
    d["sau2010_estime"] = d["sau2020"] / (1 + d["evol_sau"] / 100)
    return d


def synthese(df_communes: pd.DataFrame, label: str) -> dict:
    """Agrège les communes (sommes) et recalcule les évolutions 2010-2020 à partir des valeurs reconstituées."""
    d = _reconstitue_2010(df_communes)
    exp20 = d["exp2020"].sum(min_count=1)
    sau20 = d["sau2020"].sum(min_count=1)
    ok_e = d[["exp2020", "evol_exp"]].notna().all(axis=1) & np.isfinite(d["exp2010_estime"])
    ok_s = d[["sau2020", "evol_sau"]].notna().all(axis=1) & np.isfinite(d["sau2010_estime"])
    exp10 = d.loc[ok_e, "exp2010_estime"].sum()
    sau10 = d.loc[ok_s, "sau2010_estime"].sum()
    evol_e = 100 * (d.loc[ok_e, "exp2020"].sum() - exp10) / exp10 if exp10 else np.nan
    evol_s = 100 * (d.loc[ok_s, "sau2020"].sum() - sau10) / sau10 if sau10 else np.nan
    return {
        "Territoire": label,
        "Exploitations 2020": exp20,
        "SAU 2020 (ha)": sau20,
        "SAU moyenne par exploitation (ha)": sau20 / exp20 if exp20 else np.nan,
        "Évolution exploitations 2010-2020 (%)": evol_e,
        "Évolution SAU 2010-2020 (%)": evol_s,
        "Communes sans donnée (secret ou absence)": int(d["exp2020"].isna().sum()),
    }


def ligne_reference(df: pd.DataFrame, code: str, label: str) -> dict:
    row = df[df["codgeo"].astype(str) == str(code)]
    if row.empty:
        return {"Territoire": label}
    r = row.iloc[0]
    return {
        "Territoire": label,
        "Exploitations 2020": r["exp2020"],
        "SAU 2020 (ha)": r["sau2020"],
        "SAU moyenne par exploitation (ha)": r["sau2020"] / r["exp2020"] if r["exp2020"] else np.nan,
        "Évolution exploitations 2010-2020 (%)": r["evol_exp"],
        "Évolution SAU 2010-2020 (%)": r["evol_sau"],
        "Communes sans donnée (secret ou absence)": None,
    }


# ---------------------------------------------------------------------------
# Import de fichiers utilisateur (exports Cartostat, DISAR, tableurs maison)
# ---------------------------------------------------------------------------

_CODE_COLS = ("codgeo", "code_insee", "insee", "code commune", "codecommune", "com", "depcom", "code", "ci")


def lire_fichier_utilisateur(name: str, content: bytes) -> pd.DataFrame:
    """Lit un fichier xlsx/csv contenant une colonne de code commune INSEE."""
    name = name.lower()
    if name.endswith((".xlsx", ".xls")):
        try:
            df = lire_export_geoclip(content)
        except DataSourceError:
            df = pd.read_excel(io.BytesIO(content), dtype=str)
    else:
        txt = content.decode("utf-8", errors="ignore")
        if txt.count(";") < txt.count(",") / 2:
            sep = ","
        else:
            sep = ";"
        try:
            df = pd.read_csv(io.StringIO(txt), sep=sep, dtype=str)
        except Exception:
            df = pd.read_csv(io.BytesIO(content), sep=sep, dtype=str, encoding="latin-1")
    cols = {c: str(c).strip() for c in df.columns}
    df = df.rename(columns=cols)
    code_col = next((c for c in df.columns if c.strip().lower() in _CODE_COLS), None)
    if code_col is None:
        raise DataSourceError("Aucune colonne de code commune trouvée (attendu : codgeo, code_insee, insee, depcom…).")
    df = df.rename(columns={code_col: "codgeo"})
    df["codgeo"] = df["codgeo"].astype(str).str.strip().str.zfill(5)
    for c in df.columns:
        if c in ("codgeo", "libgeo"):
            continue
        conv = pd.to_numeric(df[c].astype(str).str.replace(",", ".").str.replace(" ", "").str.replace(" ", ""), errors="coerce")
        if conv.notna().sum() >= max(1, 0.5 * df[c].notna().sum()):
            df[c] = conv
    return df
