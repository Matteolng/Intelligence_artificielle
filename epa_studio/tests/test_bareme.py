"""Lecture du barème de la valeur vénale. Extrait réel : décision du 10 août 2026 (barème 2025), Légifrance
JORFTEXT000054708553, tableau des terres labourables et prairies naturelles louées, Puy-de-Dôme et Territoire de Belfort."""
import pandas as pd

from epa import bareme as B

EXTRAIT = """
| TERRES LABOURABLES ET PRAIRIES NATURELLES (louées) |
|  | 84 AUVERGNE-RHÔNE-ALPES |  |  |  |
| 63-Puy-de-Dôme |  |  |  |
|  | DOMES ET PERIPHERIE, CEZALLIER, ARTENSE | 4 050 | 1 690 | 7 150 |
|  | LIMAGNE AGRICOLE | 7 970 | 2 500 | 12 650 |
| 51-Marne |  |  |  |
|  | VIGNOBLE | ND | ND | ND |
| 90-Territoire de Belfort | 3 670 | 2 490 | 5 000 |
"""


def test_lire_bareme_extrait_reel():
    b = B.lire_bareme(EXTRAIT)
    lim = b[b["region_agricole"] == "LIMAGNE AGRICOLE"].iloc[0]
    assert (lim["departement"], lim["dominante"], lim["minimum"], lim["maximum"]) == ("63", 7970.0, 2500.0, 12650.0)
    assert "louées" in lim["tableau"]
    assert pd.isna(b[b["region_agricole"] == "VIGNOBLE"].iloc[0]["dominante"])  # « ND » : non diffusé
    assert b[b["departement"] == "90"].iloc[0]["dominante"] == 3670.0


def test_correspondance_par_nom():
    b = B.lire_bareme(EXTRAIT)
    pra = pd.DataFrame({"code_pra": ["63999", "63998"], "nom": ["Limagne agricole", "Périphérie des Dômes"], "departement": ["63", "63"],
                        "part_pct": [70.0, 30.0]})
    c = B.correspondances(pra, b)
    assert c.loc[c["PRA"] == "Limagne agricole", "Dominante (€/ha)"].iloc[0] == 7970.0
    assert c.loc[c["PRA"] == "Périphérie des Dômes", "Ligne du barème"].iloc[0] == "DOMES ET PERIPHERIE, CEZALLIER, ARTENSE"
