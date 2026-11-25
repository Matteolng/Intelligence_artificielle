"""Agriculture biologique (Agence Bio) et signes officiels de qualité (INAO)."""
from __future__ import annotations

import io

import pandas as pd

from .config import AGENCE_BIO_API, INAO_AIRES_PRODUITS_CSV, INAO_COMMUNES_AO_CSV, INAO_COMMUNES_IG_CSV
from .http import disk_cache, get_bytes, get_json

# ---------------------------------------------------------------------------
# Agence Bio – annuaire des opérateurs (open data)
# ---------------------------------------------------------------------------


@disk_cache("bio")
def operateurs_departement(code_dep: str) -> list[dict]:
    items: list[dict] = []
    debut, nb = 0, 1000
    while True:
        d = get_json(AGENCE_BIO_API, params={"departements": code_dep, "nb": nb, "debut": debut}, limiter="agencebio", timeout=120)
        page = d.get("items", [])
        items.extend(page)
        total = int(d.get("nbTotal") or 0)
        debut += nb
        if not page or debut >= total:
            break
    return items


def operateurs_bio(codes_departements: list[str], codes_communes: list[str]) -> pd.DataFrame:
    """Opérateurs bio dont une adresse active est située dans le territoire."""
    communes = set(codes_communes)
    rows = []
    for dep in codes_departements:
        for op in operateurs_departement(dep):
            certs = op.get("certificats") or []
            etat = certs[0].get("etatCertification") if certs else None
            for adr in op.get("adressesOperateurs") or []:
                if str(adr.get("codeCommune")) not in communes or adr.get("active") is False:
                    continue
                rows.append({
                    "id": op.get("id"),
                    "nom": op.get("denominationcourante") or op.get("raisonSociale"),
                    "siret": op.get("siret"),
                    "naf": op.get("codeNAF"),
                    "activites": ", ".join(sorted({a.get("nom") for a in op.get("activites") or [] if a.get("nom")})),
                    "productions": "; ".join(sorted({p.get("nom") for p in op.get("productions") or [] if p.get("nom")}))[:400],
                    "etat_certification": etat,
                    "organisme": certs[0].get("organisme") if certs else None,
                    "date_engagement": certs[0].get("dateEngagement") if certs else None,
                    "code_commune": str(adr.get("codeCommune")),
                    "commune": adr.get("ville"),
                    "latitude": adr.get("lat"),
                    "longitude": adr.get("long"),
                    "types_adresse": ", ".join(adr.get("typeAdresseOperateurs") or []),
                })
                break  # une ligne par opérateur
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.drop_duplicates(subset="id")
    return df


def synthese_bio(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["activite", "operateurs_engages"])
    d = df[df["etat_certification"].eq("ENGAGEE")]
    acts = d["activites"].str.split(", ").explode()
    t = acts.value_counts().rename_axis("activite").reset_index(name="operateurs_engages")
    return t


# ---------------------------------------------------------------------------
# INAO – aires géographiques des SIQO par commune
# ---------------------------------------------------------------------------


def _read_inao(url: str) -> pd.DataFrame:
    raw = get_bytes(url, timeout=600)
    return pd.read_csv(io.BytesIO(raw), sep=";", encoding="latin-1", dtype=str)


def table_inao() -> pd.DataFrame:
    """Table commune (CI) × aire géographique (IDA) × signe, toutes AOC/AOP/IGP/IG (dernières versions data.gouv.fr)."""
    from .catalogue import ressource

    return _table_inao(ressource("inao_ao")[0], ressource("inao_ig")[0], ressource("inao_produits")[0])


@disk_cache("inao")
def _table_inao(url_ao: str, url_ig: str, url_prod: str) -> pd.DataFrame:
    ao = _read_inao(url_ao)
    ig = _read_inao(url_ig)
    prod = _read_inao(url_prod)
    ao = ao.rename(columns={"Aire géographique": "aire"})[["CI", "IDA", "aire"]]
    ig = ig.rename(columns={"Aire géographique": "aire"})
    if "Actual" in ig:
        ig = ig[ig["Actual"].astype(str).str.strip().isin(["1", "True", "true"])]
    ig = ig[["CI", "IDA", "aire", "Signe UE"]]
    prod = prod.rename(columns={"Signe FR": "signe_fr", "Signe UE": "signe_ue", "Produit": "produit"})

    def _join(s: pd.Series, sep: str = ", ") -> str:
        vals = {str(x).strip() for x in s if pd.notna(x) and str(x).strip() not in ("", "nan")}
        return sep.join(sorted(vals))

    prod_g = prod.groupby("IDA").agg(
        signes=("signe_ue", _join),
        signes_fr=("signe_fr", _join),
        produits=("produit", lambda s: _join(s, "; ")),
        nb_produits=("produit", "nunique"),
    ).reset_index()
    ao["famille"] = "AOC / AOP"
    ig["famille"] = "IGP / IG"
    tab = pd.concat([ao, ig.drop(columns=["Signe UE"])], ignore_index=True)
    tab["CI"] = tab["CI"].astype(str).str.zfill(5)
    tab = tab.merge(prod_g, on="IDA", how="left")
    return tab


def siqo_territoire(codes_communes: list[str]) -> pd.DataFrame:
    tab = table_inao()
    t = tab[tab["CI"].isin(codes_communes)]
    if t.empty:
        return pd.DataFrame()
    n = len(set(codes_communes))
    g = t.groupby(["IDA", "aire", "famille"], as_index=False).agg(
        communes_concernees=("CI", "nunique"),
        signes=("signes", "first"),
        produits=("produits", "first"),
        nb_produits=("nb_produits", "first"),
    )
    g["part_communes_pct"] = 100 * g["communes_concernees"] / n
    return g.sort_values(["famille", "communes_concernees"], ascending=[True, False]).reset_index(drop=True)


def siqo_par_commune(codes_communes: list[str]) -> pd.DataFrame:
    tab = table_inao()
    t = tab[tab["CI"].isin(codes_communes)]
    return t.groupby("CI", as_index=False).agg(nb_siqo=("IDA", "nunique"), aires=("aire", lambda s: "; ".join(sorted(set(s)))))
