# Graph Report - Intelligence_artificielle  (2026-11-22)

## Corpus Check
- Corpus is ~25,477 words - fits in a single context window. You may not need a graph.

## Summary
- 369 nodes · 1028 edges · 12 communities (10 shown, 2 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 46 edges (avg confidence: 0.9)
- Token cost: 88,978 input · 0 output

## Community Hubs (Navigation)
- Agreste RA 2020 & imports
- Analyse et rapport Word
- Pages Streamlit
- Cartographie Folium
- Foncier DVF & cache HTTP
- Filières SIRENE
- Projet, emprise & tests
- Registre parcellaire RPG
- Concepts EPA (README)
- Territoire d étude
- Compensation collective
- Script de lancement

## God Nodes (most connected - your core abstractions)
1. `disk_cache()` - 27 edges
2. `fnum()` - 24 edges
3. `DataSourceError` - 24 edges
4. `get_json()` - 23 edges
5. `build_docx()` - 17 edges
6. `hero()` - 15 edges
7. `resultat()` - 13 edges
8. `require_territoire()` - 13 edges
9. `EPA Studio requirements.txt` - 13 edges
10. `kpis()` - 12 edges

## Surprising Connections (you probably didn't know these)
- `streamlit>=1.50` --conceptually_related_to--> `EPA Studio (Streamlit application)`  [INFERRED]
  epa_studio/requirements.txt → epa_studio/README.md
- `build_ctx()` --calls--> `synthese_bio()`  [EXTRACTED]
  epa_studio/app_pages/p11_rapport.py → epa_studio/epa/bio_siqo.py
- `build_ctx()` --calls--> `synthese_filieres()`  [EXTRACTED]
  epa_studio/app_pages/p11_rapport.py → epa_studio/epa/filieres.py
- `build_ctx()` --calls--> `resultat()`  [EXTRACTED]
  epa_studio/app_pages/p11_rapport.py → epa_studio/epa/ui.py
- `graph_barres()` --calls--> `fnum()`  [EXTRACTED]
  epa_studio/epa/rapport.py → epa_studio/epa/analyse.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Public open data sources for the agricultural initial state** — epa_studio_readme_rpg, epa_studio_readme_recensement_agricole_2020, epa_studio_readme_sirene, epa_studio_readme_agence_bio, epa_studio_readme_inao, epa_studio_readme_dvf, epa_studio_readme_api_decoupage_administratif, epa_studio_readme_geoplateforme_ign [EXTRACTED 1.00]
- **Geospatial and mapping dependency stack** — epa_studio_requirements_geopandas, epa_studio_requirements_shapely, epa_studio_requirements_pyproj, epa_studio_requirements_folium, epa_studio_requirements_streamlit_folium [INFERRED 0.85]

## Communities (12 total, 2 thin omitted)

### Community 0 - "Agreste RA 2020 & imports"
Cohesion: 0.07
Nodes (41): indicateur_odt(), liens_telechargement(), ligne_reference(), lire_export_geoclip(), lire_fichier_utilisateur(), ra2020(), _reconstitue_2010(), synthese() (+33 more)

### Community 1 - "Analyse et rapport Word"
Cohesion: 0.09
Nodes (23): fnum(), fpct(), _minus(), texte_bio(), texte_compensation(), texte_emprise(), texte_filieres(), texte_foncier() (+15 more)

### Community 2 - "Pages Streamlit"
Cohesion: 0.18
Nodes (16): badge(), card(), hero(), kpi(), kpis(), progress_callback(), require_territoire(), resultat() (+8 more)

### Community 3 - "Cartographie Folium"
Cohesion: 0.14
Nodes (23): build_ctx(), add_emprise(), add_legend(), add_points(), add_territoire(), add_wms(), base_map(), carte_categories() (+15 more)

### Community 4 - "Foncier DVF & cache HTTP"
Cohesion: 0.06
Nodes (11): filtrer(), stats_prix(), bytes_io(), _cache_path(), cache_size_mb(), clear_cache(), deco(), wrapper() (+3 more)

### Community 5 - "Filières SIRENE"
Cohesion: 0.11
Nodes (20): zoom_pour_emprise(), compter(), _decorer(), etablissements(), filieres_territoire(), naf_libelles(), production_par_naf(), _search() (+12 more)

### Community 6 - "Projet, emprise & tests"
Cohesion: 0.10
Nodes (12): communes_concernees(), controle_agrivoltaique(), emprise_depuis_dessins(), emprise_from_geojson(), emprise_to_geojson(), lire_emprise(), Projet, surface_ha() (+4 more)

### Community 7 - "Registre parcellaire RPG"
Cohesion: 0.14
Nodes (15): assolement(), codes_cultures(), comparaison_emprise(), cultures_detail(), _features_to_rows(), fetch_rpg_bbox(), _page(), indicateurs() (+7 more)

### Community 8 - "Concepts EPA (README)"
Cohesion: 0.09
Nodes (24): EPA Studio README, Projets agrivoltaiques, Article D. 112-1-19 code rural (contenu de l'EPA), Cache disque (EPA_CACHE_DIR, CACHE_TTL_DAYS), EPA Studio (Streamlit application), Etude prealable agricole (EPA), Geoplateforme IGN (WMS/WFS/WMTS), Deploiement Onyxia (SSP Cloud) avec VS Code (+16 more)

### Community 10 - "Compensation collective"
Cohesion: 0.46
Nodes (3): calcul(), Parametres, sensibilite()

## Knowledge Gaps
- **13 isolated node(s):** `EPA Studio README`, `Sequence Eviter-Reduire-Compenser (ERC)`, `INSEE SIRENE / API Recherche d'entreprises`, `Agence Bio open data`, `INAO (AOC/AOP, IGP/IG)` (+8 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 110 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `disk_cache()` connect `Agreste RA 2020 & imports` to `Cartographie Folium`, `Foncier DVF & cache HTTP`, `Filières SIRENE`, `Registre parcellaire RPG`?**
  _High betweenness centrality (0.049) - this node is a cross-community bridge._
- **What connects `EPA Studio README`, `Sequence Eviter-Reduire-Compenser (ERC)`, `INSEE SIRENE / API Recherche d'entreprises` to the rest of the system?**
  _13 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Agreste RA 2020 & imports` be split into smaller, more focused modules?**
  _Cohesion score 0.06572769953051644 - nodes in this community are weakly interconnected._
- **Why does `DataSourceError` connect `Agreste RA 2020 & imports` to `Pages Streamlit`, `Cartographie Folium`, `Foncier DVF & cache HTTP`, `Registre parcellaire RPG`?**
  _High betweenness centrality (0.035) - this node is a cross-community bridge._
- **Should `Analyse et rapport Word` be split into smaller, more focused modules?**
  _Cohesion score 0.08888888888888889 - nodes in this community are weakly interconnected._
- **Should `Cartographie Folium` be split into smaller, more focused modules?**
  _Cohesion score 0.1422475106685633 - nodes in this community are weakly interconnected._
- **Should `Foncier DVF & cache HTTP` be split into smaller, more focused modules?**
  _Cohesion score 0.06439393939393939 - nodes in this community are weakly interconnected._