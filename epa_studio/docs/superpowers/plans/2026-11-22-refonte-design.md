# Refonte du design d'EPA Studio – plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Habiller EPA Studio d'une identité SaaS sobre en marque blanche, ajouter mode démo, figures types exportables, phrases par gabarit et bibliographie, sans toucher aux calculs.

**Architecture:** Thème natif Streamlit (`.streamlit/config.toml`) + CSS court dans `epa/ui.py` + composants Python. Nouveaux modules purs (testables sans réseau) : `branding`, `gabarits`, `sources`, `chiffres_cles`, `figures`, `demo`. Pages existantes restylées, trois pages ajoutées.

**Tech Stack:** Python 3.13, Streamlit 1.67, folium/streamlit-folium, matplotlib, geopandas, pytest.

**Spec:** `docs/superpowers/specs/2026-11-22-refonte-design-design.md`

## Global Constraints
- Aucune valeur inventée ; donnée absente → composant « manquant » explicite (quoi, source, comment l'obtenir).
- Toute valeur affichée porte sa source (producteur, millésime).
- Couleurs : fond `#F5F5F7`, surface `#FFFFFF`, texte `#1D1D1F`, secondaire `#6E6E73`, filets `#D2D2D7`, accent défaut `#2F6B3A`.
- Police Inter (Google Fonts), repli `sans-serif`. Pas de libellés en capitales, pas d'émojis dans la navigation.
- Aucune marque de bureau d'études en dur.
- PNG exportés : 300 dpi, titre et ligne « Source : … » dans l'image.
- Tests existants (`tests/test_calculs.py`, `tests/test_pages.py`) restent verts.

## Review Focus
1. API publique indisponible pendant une démo hors cache → la page affiche « manquant » et continue (test : `test_tuile_valeur_manquante`, `test_phrase_valeurs_manquantes`).
2. Communes sous secret statistique (NaN) → exclues des agrégats et comptées, jamais traitées comme zéro (test : `test_comparaison_ignore_nan`).
3. Territoire à cheval sur deux départements → département de référence = celui de la commune du site, sinon le majoritaire en surface (test : `test_departement_reference`).
4. Pas d'emprise projet → vignettes RPG signalées manquantes, pas d'exception (test : `test_vignettes_sans_emprise`).
5. Couleur de marque invalide dans `branding.toml` → repli sur l'accent par défaut (test : `test_branding_couleur_invalide`).

---

### Task 1: Marque blanche et thème
**Files:** Create `epa/branding.py`, `branding.toml`, `.streamlit/config.toml`; Modify `epa/ui.py` (CSS, `setup_page`), `app.py`; Test `tests/test_design.py`.
**Interfaces:** Produces `Branding(nom: str, couleur: str, logo: Path | None)`, `charger_branding(path: Path | None = None) -> Branding`, `branding_courant() -> Branding` (session > fichier).
- [ ] Tests : `test_branding_defaut` (nom `"Votre bureau d'études"`, couleur `#2F6B3A`), `test_branding_fichier`, `test_branding_couleur_invalide` (`"vert"` → `#2F6B3A`).
- [ ] Implémenter ; `config.toml` : `primaryColor="#2F6B3A"`, `backgroundColor="#F5F5F7"`, `secondaryBackgroundColor="#FFFFFF"`, `textColor="#1D1D1F"`, `font` Inter via URL Google Fonts, `baseRadius="12px"`. L'accent session est injecté par CSS (`--accent`).
- [ ] Navigation `app.py` : icônes `:material/…:`, groupes « Démarrer », « 1. Cadrage », « 2. État initial », « 3. Impacts », « 4. Livrables ».
- [ ] `pytest -q tests/test_design.py` PASS ; commit `feat(ui): marque blanche et thème`.

### Task 2: Composants d'interface
**Files:** Modify `epa/ui.py`; Test `tests/test_design.py`.
**Interfaces:** Produces `entete(etape: str | None, titre: str, intro: str) -> None`, `tuile_comparee(libelle: str, valeurs: dict[str, float | None], unite: str, dec: int = 1, signe: bool = False) -> str` (HTML ; première clé = valeur principale), `manquant(quoi: str, source: str, comment: str) -> None`, `phrase(txt: str) -> None`, `bouton_png(png: bytes | None, nom: str) -> None`. `hero`, `kpi`, `kpis`, `card`, `texte_auto` gardés comme alias compatibles.
- [ ] Tests : `test_tuile_valeur_manquante` (None → « non disponible »), `test_tuile_format_francais` (`-13.1`, signe → `−13,1 %`).
- [ ] Implémenter ; commit `feat(ui): composants tuile, manquant, phrase, export`.

### Task 3: Sources et bibliographie
**Files:** Create `epa/sources.py`; Modify `epa/ui.py` (`source()` accepte une clé du catalogue et l'enregistre en session); Test `tests/test_sources.py`.
**Interfaces:** Produces `CATALOGUE: dict[str, Source]`, `Source(producteur, titre, millesime, url)`, `citer(cle: str) -> str`, `enregistrer(cle: str) -> None`, `bibliographie(cles: Iterable[str]) -> list[str]` (triée, format `Producteur (millésime). Titre. URL. Consulté le JJ/MM/AAAA.`).
- [ ] Tests : `test_citer_format`, `test_bibliographie_dedoublonne_et_trie`, `test_cle_inconnue_leve_keyerror`.
- [ ] Catalogue : geo.api, RPG (par millésime), RA 2020 ODT, SIRENE, Agence Bio, INAO, DVF Cerema, CLC 2018, carte des sols INRAE, ortho IGN, Plan IGN. Commit.

### Task 4: Phrases par gabarit
**Files:** Create `epa/gabarits.py`; Test `tests/test_gabarits.py`.
**Interfaces:** Produces `phrase_evolution(sujet: str, feminin: bool, v_perim: float | None, v_dep: float | None, v_fr: float | None) -> str`.
- [ ] Tests (valeurs exactes) : `phrase_evolution("Le nombre d'exploitations", False, -13.1, -14.5, -21.0)` == `"Le nombre d'exploitations recule de 13,1 % entre 2010 et 2020, contre 14,5 % dans le département et 21,0 % en France."` ; hausse → « progresse de » ; |v| < 0,05 → « est stable » ; `test_phrase_valeurs_manquantes` (dep None → « … ; la valeur départementale n'est pas disponible. »).
- [ ] Implémenter, commit.

### Task 5: Chiffres clés comparés
**Files:** Create `epa/chiffres_cles.py`; Test `tests/test_chiffres_cles.py`.
**Interfaces:** Consumes `agreste.synthese`, `agreste.ligne_reference`, `agreste.ra2020`. Produces `departement_reference(communes: gpd.GeoDataFrame, code_site: str | None) -> str`, `comparaison(df_com: pd.DataFrame, df_dep: pd.DataFrame, codes_communes: list[str], code_dep: str) -> pd.DataFrame` (lignes « Périmètre », « Département », « France (somme des départements) »).
- [ ] Tests sur DataFrames synthétiques : `test_comparaison_trois_lignes`, `test_comparaison_ignore_nan`, `test_departement_reference`.
- [ ] Implémenter, commit.

### Task 6: Figures types PNG HD
**Files:** Create `epa/figures.py`; Test `tests/test_figures.py` (WMS mocké par monkeypatch de `cartes._wms_image`).
**Interfaces:** Produces `vignettes_rpg(emprise, rpg_par_annee: dict[int, gpd.GeoDataFrame]) -> bytes | None`, `localisation_3_echelles(departement, perimetre, commune_site, emprise) -> bytes`, `carte_otex(communes, df_otex: pd.DataFrame | None) -> bytes | None`, `carte_wms_perimetre(perimetre, couche: str, titre: str, cle_source: str) -> bytes`. Toutes : 300 dpi, titre, source, échelle, flèche nord.
- [ ] Tests : `test_png_300_dpi` (PIL `info["dpi"]`), `test_vignettes_sans_emprise` (→ None), `test_otex_sans_fichier` (→ None).
- [ ] Implémenter (couleurs de cultures cohérentes entre années via palette fixe par groupe), commit.

### Task 7: Mode démonstration
**Files:** Create `epa/demo.py`, `scripts/precharger_demo.py`, `demo_cache/` ; Modify `epa/http.py` (`_cache_path` : lecture de repli dans `DEMO_CACHE_DIR`), `epa/config.py`; Test `tests/test_demo.py`.
**Interfaces:** Produces `DEMO_EPCIS: list[dict]` (EPCI d'exemple `000000000`, EPCI d'exemple), `DEMO_COMMUNE_SITE = "00000"`, `charger_demo(state: MutableMapping) -> None` (territoire, projet, emprise illustrative signalée comme fictive).
- [ ] Test `test_cache_repli_demo` (fichier présent seulement dans le répertoire démo → lu).
- [ ] Exécuter `python scripts/precharger_demo.py` ; vérifier la taille de `demo_cache/` (< 50 Mo, sinon réduire aux millésimes nécessaires). Commit.

### Task 8: Pages
**Files:** Modify `app.py`, toutes les pages `app_pages/*.py` (en-têtes, tuiles, sources) ; Create `app_pages/p04b_chiffres_cles.py`, `app_pages/p13_figures.py`, `app_pages/p14_reglages.py` ; Modify `tests/test_pages.py`.
- [ ] Accueil : bouton « Ouvrir la démonstration (Commune-exemple, Gers) », ce que l'outil produit, sources.
- [ ] Barre latérale : nom/logo du bureau, projet courant, progression.
- [ ] `pytest -q tests/test_pages.py` PASS ; commit par groupe de pages.

### Task 9: Revue visuelle
- [ ] Skill `run` : lancer l'app, captures Playwright de chaque page (1440×900, deviceScaleFactor 2 pour les captures montrées).
- [ ] `design-skills:design-critique` + `design-skills:accessibility-audit` sur les captures ; corriger ; recapturer.

### Task 10: Vérification finale
- [ ] `superpowers:verification-before-completion` : suite complète, captures finales.
- [ ] `code-review` sur la branche ; corriger ; pousser `claude/epa-agricultural-studies-app-v1rewy`.
