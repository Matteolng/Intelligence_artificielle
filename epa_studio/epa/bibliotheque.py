"""Bibliothèque partagée : analyses par intercommunalité, département ou région calculées une fois, puis réutilisées
par tous les projets du même secteur ; projets sauvegardés et ouverts par lien.

Le stockage est un dossier de l'instance (variable EPA_LIBRARY_DIR) : tous les utilisateurs d'une même instance le
partagent. Chaque analyse garde la date de calcul et la source, affichées dans l'inventaire.
"""
from __future__ import annotations

import json
import os
import pickle
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, MutableMapping

import geopandas as gpd
import pandas as pd

LIB = Path(os.environ.get("EPA_LIBRARY_DIR", Path.home() / ".local" / "share" / "epa_studio"))
_SAFE = re.compile(r"[^A-Za-z0-9_.-]+")


def _nom(x: str) -> str:
    return _SAFE.sub("-", str(x))[:80]


def _chemin(nature: str, code: str, millesime: str) -> Path:
    return LIB / "analyses" / _nom(nature) / f"{_nom(code)}__{_nom(millesime)}.pkl"


def analyse(nature: str, code: str, millesime: str, libelle: str, source: str, calcul: Callable[[], Any]) -> Any:
    """Renvoie l'analyse stockée, ou la calcule, la stocke et la renvoie. Une erreur de calcul n'est jamais stockée."""
    f = _chemin(nature, code, millesime)
    if f.exists():
        try:
            with open(f, "rb") as h:
                return pickle.load(h)["valeur"]
        except Exception:  # fichier abîmé : on recalcule
            f.unlink(missing_ok=True)
    val = calcul()
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(".tmp")
    with open(tmp, "wb") as h:
        pickle.dump({"valeur": val, "meta": {"nature": nature, "code": code, "millesime": millesime, "libelle": libelle,
                                             "source": source, "calcule_le": datetime.now().isoformat(timespec="seconds")}},
                    h, protocol=pickle.HIGHEST_PROTOCOL)
    tmp.replace(f)
    return val


def inventaire() -> pd.DataFrame:
    rows = []
    for f in sorted((LIB / "analyses").rglob("*.pkl")) if (LIB / "analyses").exists() else []:
        try:
            with open(f, "rb") as h:
                m = pickle.load(h)["meta"]
        except Exception:
            continue
        rows.append({"Analyse": m["nature"], "Territoire": m["libelle"], "Code": m["code"], "Millésime": m["millesime"],
                     "Source": m["source"], "Calculée le": m["calcule_le"][:16].replace("T", " "),
                     "Taille (Mo)": round(f.stat().st_size / 1e6, 2)})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# RPG par intercommunalité (réutilisé par tous les projets qui touchent la même intercommunalité)
# ---------------------------------------------------------------------------

def rpg_territoire(layer: str, annee: str, territoire, progress=None) -> gpd.GeoDataFrame:
    """RPG du territoire assemblé à partir des analyses par intercommunalité (et par commune ajoutée hors EPCI)."""
    from . import rpg
    from . import territoire as T

    zones = [("epci", e["code"], e["nom"], lambda e=e: T.communes_epci_geo(e["code"])) for e in territoire.epcis]
    hors = set(territoire.codes_communes) - set().union(*[set(T.communes_epci_geo(e["code"])["code"].astype(str)) for e in territoire.epcis])
    zones += [("commune", c, c, lambda c=c: T.commune_geo(c)) for c in sorted(hors)]
    parts = []
    for i, (nat, code, lib, geo) in enumerate(zones, start=1):
        if progress:
            progress((i - 1) / max(len(zones), 1), f"RPG {annee} – {lib} ({i}/{len(zones)})")
        parts.append(analyse(f"rpg-{nat}", code, annee, lib, f"IGN / ASP, RPG {annee}",
                             lambda geo=geo: rpg.rpg_territoire(layer, geo())))
    if progress:
        progress(1.0, "Assemblage")
    parts = [p for p in parts if p is not None and not p.empty]
    if not parts:
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
    g = gpd.GeoDataFrame(pd.concat(parts, ignore_index=True), geometry="geometry", crs=parts[0].crs)
    if "fid" in g:
        g = g.drop_duplicates(subset="fid")
    return g[g["code_commune"].astype(str).isin(territoire.codes_communes)].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Projets sauvegardés et ouverts par lien
# ---------------------------------------------------------------------------

_CLES_SIMPLES = ("assuj_cfg", "mesures_choix", "mesures_autres", "couches_atlas", "source_pb", "site_commune",
                 "communes_emprise", "emprise_fictive", "mode_demo")


def serialiser(state: MutableMapping) -> dict:
    from dataclasses import asdict

    from . import projet as P
    from . import territoire as T
    from .config import APP_VERSION

    t0 = state["territoire"]
    return {
        "version": APP_VERSION, "date": datetime.now().isoformat(timespec="seconds"),
        "territoire": T.territoire_to_dict(t0), "territoire_cfg": state.get("territoire_cfg", {}),
        "projet": state["projet"].to_dict() if state.get("projet") else None,
        "emprise": P.emprise_to_geojson(state.get("emprise")),
        "comp_params": asdict(state["comp_params"]) if state.get("comp_params") else None,
        "pb_table": state["pb_table"].to_dict(orient="records") if state.get("pb_table") is not None else None,
        "effets": state["effets"].to_dict(orient="records") if state.get("effets") is not None else None,
        **{k: state.get(k) for k in _CLES_SIMPLES if state.get(k) is not None},
    }


def restaurer(data: dict, state: MutableMapping) -> None:
    from . import projet as P
    from . import territoire as T
    from .compensation import Parametres

    cfg = data.get("territoire_cfg", {})
    terr = data.get("territoire", {})
    state["territoire"] = T.build_territoire(terr.get("epcis", []), cfg.get("communes_ajoutees", []),
                                             cfg.get("communes_retirees", []), terr.get("nom"))
    state["territoire_cfg"] = cfg
    if data.get("projet"):
        state["projet"] = P.Projet(**data["projet"])
    state["emprise"] = P.emprise_from_geojson(data.get("emprise"))
    for k in _CLES_SIMPLES:
        if k in data:
            state[k] = data[k]
    if data.get("comp_params"):
        state["comp_params"] = Parametres(**data["comp_params"])
    if data.get("pb_table"):
        state["pb_table"] = pd.DataFrame(data["pb_table"])
    if data.get("effets"):
        state["effets"] = pd.DataFrame(data["effets"])


def _fichier_projet(pid: str) -> Path:
    if not re.fullmatch(r"[a-f0-9]{12}", pid or ""):
        raise KeyError(pid)
    return LIB / "projets" / f"{pid}.json"


def enregistrer(state: MutableMapping, pid: str | None = None) -> str:
    pid = pid or state.get("projet_id") or uuid.uuid4().hex[:12]
    f = _fichier_projet(pid)
    f.parent.mkdir(parents=True, exist_ok=True)
    data = serialiser(state)
    data["id"] = pid
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, default=str), encoding="utf-8")
    tmp.replace(f)
    state["projet_id"] = pid
    return pid


def charger(pid: str, state: MutableMapping) -> bool:
    """Charge le projet `pid` ; False s'il n'existe pas (identifiant inconnu ou mal formé)."""
    try:
        f = _fichier_projet(pid)
    except KeyError:
        return False
    if not f.exists():
        return False
    restaurer(json.loads(f.read_text(encoding="utf-8")), state)
    state["projet_id"] = pid
    return True


def projets() -> pd.DataFrame:
    rows = []
    for f in sorted((LIB / "projets").glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True) if (LIB / "projets").exists() else []:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        rows.append({"id": d.get("id", f.stem), "Projet": (d.get("projet") or {}).get("nom") or "Sans nom",
                     "Territoire": d.get("territoire", {}).get("nom", ""), "Enregistré le": d.get("date", "")[:16].replace("T", " ")})
    return pd.DataFrame(rows)
