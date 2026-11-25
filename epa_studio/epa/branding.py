"""Marque blanche : nom, couleur d'accent et logo du bureau d'études (aucune marque en dur)."""
from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, replace
from pathlib import Path

DEFAUT_NOM = "Votre bureau d'études"
DEFAUT_COULEUR = "#56653E"
FICHIER = Path(__file__).resolve().parents[1] / "branding.toml"
_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


POLICES_TITRES = ("Cormorant Garamond", "Playfair Display", "Libre Baskerville", "Fraunces", "Inter")
POLICES_TEXTE = ("Inter", "Source Sans 3", "Lato")


@dataclass(frozen=True)
class Branding:
    nom: str = DEFAUT_NOM
    couleur: str = DEFAUT_COULEUR
    logo: Path | None = None
    police_titres: str = POLICES_TITRES[0]
    police_texte: str = POLICES_TEXTE[0]


def dossier_marque() -> Path:
    """Fichiers de marque partagés par l'instance (logo, réglages) : dans la bibliothèque."""
    from .bibliotheque import LIB

    return LIB / "marque"


def enregistrer_marque(reglages: dict, fichiers: dict[str, tuple[str, bytes]] | None = None) -> None:
    """Enregistre les réglages (nom, couleur, polices) et le logo pour l'instance."""
    import json

    d = dossier_marque()
    d.mkdir(parents=True, exist_ok=True)
    data = {k: v for k, v in reglages.items() if k in ("nom", "couleur", "police_titres", "police_texte") and v}
    if "couleur" in data:
        data["couleur"] = couleur_valide(data["couleur"])
    for cle, (nom, contenu) in (fichiers or {}).items():
        ext = Path(nom).suffix.lower()
        if cle != "logo":
            raise ValueError(f"Fichier de marque inconnu : {cle}")
        if ext not in (".png", ".jpg", ".jpeg", ".svg"):
            raise ValueError("Logo : formats acceptés PNG, JPG ou SVG.")
        for ancien in d.glob(f"{cle}.*"):
            ancien.unlink()
        (d / f"{cle}{ext}").write_bytes(contenu)
    (d / "marque.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _marque_instance(b: "Branding") -> "Branding":
    import json

    d = dossier_marque()
    if not d.exists():
        return b
    try:
        data = json.loads((d / "marque.json").read_text(encoding="utf-8")) if (d / "marque.json").exists() else {}
    except (OSError, ValueError):
        data = {}
    fichier = lambda cle: next(iter(sorted(d.glob(f"{cle}.*"))), None)  # noqa: E731
    return replace(b, nom=data.get("nom") or b.nom, couleur=couleur_valide(data.get("couleur") or b.couleur),
                   police_titres=data.get("police_titres") if data.get("police_titres") in POLICES_TITRES else b.police_titres,
                   police_texte=data.get("police_texte") if data.get("police_texte") in POLICES_TEXTE else b.police_texte,
                   logo=fichier("logo") or b.logo)


def couleur_valide(c: str | None) -> str:
    return c.upper() if isinstance(c, str) and _HEX.match(c.strip()) else DEFAUT_COULEUR


def charger_branding(path: Path | None = None) -> Branding:
    """Lit `branding.toml` (clés : nom, couleur, logo). Fichier absent ou valeur invalide → valeurs par défaut."""
    path = path or FICHIER
    if not path.exists():
        return Branding()
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8")).get("bureau", {})
    except (tomllib.TOMLDecodeError, OSError):
        return Branding()
    logo = data.get("logo")
    logo_path = (path.parent / logo) if logo else None
    return Branding(
        nom=str(data.get("nom") or DEFAUT_NOM).strip(),
        couleur=couleur_valide(data.get("couleur")),
        logo=logo_path if logo_path and logo_path.exists() else None,
    )


def branding_courant(state=None) -> Branding:
    """Réglages de la session > réglages enregistrés pour l'instance > fichier branding.toml."""
    b = _marque_instance(charger_branding())
    if state is None:
        try:
            import streamlit as st

            state = st.session_state
        except Exception:  # hors contexte Streamlit
            return b
    s = state.get("branding") if hasattr(state, "get") else None
    if not s:
        return b
    return replace(b, nom=(s.get("nom") or b.nom).strip(), couleur=couleur_valide(s.get("couleur") or b.couleur))


def contraste_blanc(couleur: str) -> float:
    """Rapport de contraste WCAG 2 entre la couleur et le blanc (texte blanc sur bouton, liens sur fond clair)."""
    c = [int(couleur[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    lum = 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    return 1.05 / (lum + 0.05)
