"""Exports de données : classeur Excel de tous les tableaux calculés et archive ZIP des figures PNG."""
from __future__ import annotations

import io
import re
import zipfile

import pandas as pd


def build_xlsx(tables: dict[str, pd.DataFrame]) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        for name, df in tables.items():
            if df is None:
                continue
            d = df.copy()
            if "geometry" in d.columns:
                d = d.drop(columns="geometry")
            sheet = "".join(ch for ch in name if ch not in "[]:*?/\\")[:31]
            d.to_excel(xw, sheet_name=sheet, index=False)
    return buf.getvalue()


def zip_figures(figures: dict[str, bytes], bibliographie: list[str] | None = None) -> bytes:
    """Archive des figures (nom de fichier → PNG ou GIF), avec la bibliographie en texte si fournie."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for nom, data in figures.items():
            if data:
                ext = ".gif" if data[:3] == b"GIF" else ".png"
                z.writestr(re.sub(r"[^A-Za-z0-9_.-]+", "_", nom) + ext, data)
        if bibliographie:
            z.writestr("bibliographie.txt", "\n".join(bibliographie))
    return buf.getvalue()
