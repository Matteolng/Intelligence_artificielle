"""Découverte automatique des dernières versions (catalogues simulés, sans réseau)."""
from epa import catalogue as C

CAPS_WFS = """
<FeatureType><Name>RPG.2024:parcelles_graphiques</Name><Title>Registre parcellaire graphique (RPG) 2024 : Parcelles graphiques</Title></FeatureType>
<FeatureType><Name>RPG.LATEST:parcelles_graphiques</Name><Title>Registre parcellaire graphique (RPG) 2026 : Parcelles graphiques</Title></FeatureType>
<FeatureType><Name>RPG.2025:parcelles_graphiques</Name><Title>Registre parcellaire graphique (RPG) 2025 : Parcelles graphiques</Title></FeatureType>
<FeatureType><Name>RPG.2013:rpg_2013</Name><Title>Registre parcellaire graphique (RPG) 2013</Title></FeatureType>
"""


def test_nouveau_rpg_detecte():
    m = C.lire_rpg_wfs(CAPS_WFS)
    assert [x["annee"] for x in m] == [2026, 2025, 2024]
    assert m[0]["couche"] == "RPG.LATEST:parcelles_graphiques" and m[0]["codes"] == "RPG.LATEST:codes_cultures"


def test_couches_wms_annuelles():
    caps = "".join(f"<Name>{n}</Name>" for n in ["LANDCOVER.CLC18_FR", "LANDCOVER.CLC24_FR", "LANDCOVER.CLC90_FR",
                                                   "IGNF_RPG_PARCELLES-BIO_2025", "IGNF_RPG_PARCELLES-BIO_2026"])
    w = C.lire_wms_annuelles(caps)
    assert w["clc"] == ("LANDCOVER.CLC24_FR", 2024) and w["rpg_bio"] == ("IGNF_RPG_PARCELLES-BIO_2026", 2026)


def test_ressource_datagouv_la_plus_recente():
    meta = {"resources": [{"url": "https://x/ancien.csv", "format": "csv", "last_modified": "2025-01-01T00:00"},
                          {"url": "https://x/nouveau.csv", "format": "csv", "last_modified": "2026-07-09T09:11"},
                          {"url": "https://x/doc.pdf", "format": "pdf", "last_modified": "2027-01-01T00:00"}]}
    assert C.choisir_ressource(meta) == ("https://x/nouveau.csv", "2026-07-09")


def test_secours_si_catalogue_indisponible(monkeypatch):
    def panne():
        raise C.DataSourceError("hors service")
    monkeypatch.setattr(C, "rpg_millesimes", panne)
    C._rpg_ou_defaut.cache_clear()
    assert C.annee_rpg_recente() == int(next(iter(C.RPG_LAYERS))[:4])
    assert C.annee_de_couche("RPG.LATEST:parcelles_graphiques") == next(iter(C.RPG_LAYERS))[:4]

    C._rpg_ou_defaut.cache_clear()


def test_fichier_annexe_ignore():
    meta = {"resources": [{"url": "https://x/2025-10-09-communes-aires-ao.csv", "title": "COMAGRI-Communes_Aires_AO.csv",
                           "format": "csv", "last_modified": "2025-10-09"},
                          {"url": "https://x/dictionnaire.csv", "title": "Dictionnaire des variables", "format": "csv",
                           "last_modified": "2026-01-01"}]}
    assert C.choisir_ressource(meta, r"communes.?aires.?ao")[0].endswith("communes-aires-ao.csv")


def test_repli_si_nouvelle_version_illisible(monkeypatch):
    C._REPLI.clear()
    monkeypatch.setattr(C, "_derniere", lambda cle: ("https://x/nouveau.csv", "2027-01-05"))

    def lire(url):
        if url == "https://x/nouveau.csv":
            raise KeyError("colonne renommée")
        return "version connue"
    assert C.lire_avec_repli(("otex",), lire) == "version connue"
    assert C.ressource("otex") == (C.JEUX["otex"][1], "")  # plus de date de version citée
    C._REPLI.clear()
    assert C.ressource("otex") == ("https://x/nouveau.csv", "2027-01-05")


def test_annee_rpg_pac_wms_lue_dans_le_titre():
    caps = ("<Layer><Name>LANDUSE.AGRICULTURE.LATEST</Name><Title>Registre parcellaire graphique (RPG) édition 2026</Title>"
            "</Layer><Layer><Name>LANDUSE.AGRICULTURE2024</Name><Title>Registre parcellaire graphique (RPG) 2024</Title></Layer>")
    assert C.lire_wms_annuelles(caps)["rpg_pac"] == ("LANDUSE.AGRICULTURE.LATEST", 2026)
