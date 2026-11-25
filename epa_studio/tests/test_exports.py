import io
import zipfile

import pandas as pd

from epa.exports import build_xlsx, zip_figures


def test_xlsx_et_zip():
    x = build_xlsx({"Communes": pd.DataFrame({"a": [1]}), "Vide": None})
    assert x[:2] == b"PK"
    z = zipfile.ZipFile(io.BytesIO(zip_figures({"Localisation du projet": b"\x89PNG", "NDVI animé": b"GIF89a"}, ["Réf. 1"])))
    assert sorted(z.namelist()) == ["Localisation_du_projet.png", "NDVI_anim_.gif", "bibliographie.txt"]
