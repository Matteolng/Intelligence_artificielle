# EPA Studio 🌾

Application **Streamlit** d'aide à la réalisation de l'**état initial de l'économie agricole** des
**études préalables agricoles (EPA)** – articles L. 112-1-3 et D. 112-1-18 et suivants du code rural et de la
pêche maritime – pour les bureaux d'études agricoles, avec un volet dédié aux **projets agrivoltaïques**.

On choisit la région, le ou les départements, une ou plusieurs intercommunalités (EPCI), on ajuste les communes,
on importe (ou dessine) l'emprise du projet : l'application télécharge les données publiques, produit cartes,
tableaux, indicateurs et synthèses rédigées, calcule la compensation collective selon des paramètres
départementaux, et génère un **rapport Word** structuré selon l'article D. 112-1-19 ainsi qu'un **export Excel**.

---

## Sommaire

1. [Fonctionnalités](#fonctionnalités)
2. [Données mobilisées](#données-mobilisées)
3. [Lancer l'application sur Onyxia (SSP Cloud) avec VS Code](#lancer-lapplication-sur-onyxia-ssp-cloud-avec-vs-code)
4. [Lancer l'application en local](#lancer-lapplication-en-local)
5. [Structure du code](#structure-du-code)
6. [Méthodes, limites et précautions](#méthodes-limites-et-précautions)
7. [Personnaliser l'outil](#personnaliser-loutil)
8. [Tests](#tests)

---

## Fonctionnalités

| Étape | Page | Contenu | Correspondance D. 112-1-19 |
|---|---|---|---|
| 1 · Cadrage | **Territoire d'étude** | Région → départements → EPCI (multi-EPCI, multi-départements possible), ajout / retrait de communes, carte, population, surfaces | 1° délimitation du territoire |
| | **Projet et emprise** | Fiche projet (puissance, taux de couverture, services agrivoltaïques, zone témoin…), import GeoJSON / KML / GPKG / shapefile zippé ou dessin de l'emprise, **test d'assujettissement** (3 conditions de l'art. D. 112-1-18), **points de contrôle agrivoltaïques** | 1° description du projet |
| 2 · État initial | **Occupation agricole (RPG)** | Assolement par groupe et par culture (RPG 2015 → 2025), familles de cultures, prairies permanentes, bio, cartes par commune ou à la parcelle, **évolution entre millésimes** | 2° production primaire |
| | **Exploitations (RA 2020)** | Exploitations, SAU, SAU moyenne, évolutions 2010-2020, comparaison territoire / département / région, cartes ; **import des exports Cartostat / DISAR** (OTEX, PBS, UGB, ETP, âges…) ; orientations par code NAF (SIRENE) | 2° production primaire |
| | **Filières amont / aval** | Établissements actifs (services, ETA/CUMA, abattoirs, laiteries, meuneries, vinification, collecte et négoce, coopératives), tranches d'effectifs, carte, liste exportable | 2° première transformation et commercialisation |
| | **Qualité et bio** | Aires AOC/AOP et IGP/IG par commune (INAO) et produits ; opérateurs bio (Agence Bio) | 2° commercialisation, valorisation |
| | **Foncier agricole (DVF)** | Ventes de terres et prés, vignes, vergers depuis 2014 : prix médian, quartiles, prix pondéré, évolution annuelle, filtres paramétrables | 2° contexte foncier |
| | **Atlas cartographique** | 27 couches WMS de la Géoplateforme : RPG, bio, prairies, AOC viticoles, ZAP, sols INRAE, CLC, OCS GE, cadastre, PLU/GPU, SUP, Natura 2000, ZNIEFF, PNR, APB, ZRE, BCAE, potentiel solaire au sol, friches, ZAER, capacités S3REnR, pentes… | 2° contexte |
| 3 · Impacts | **Effets du projet et ERC** | Cultures et surfaces RPG dans l'emprise, part dans le territoire, grille des effets, mesures d'évitement et de réduction | 3° et 4° |
| | **Compensation collective** | Produit brut par culture, surfaces soustraites, baisse de rendement ou changement de production (agrivoltaïsme), coefficient aval, durée de reconstitution, ratio d'investissement, analyse de sensibilité | 3° évaluation financière, 5° compensation |
| 4 · Livrables | **Rapport et exports** | Rapport **Word** pré-rédigé (cartes IGN, graphiques, tableaux, sources, référentiel réglementaire, limites), export **Excel** de toutes les tables, **sauvegarde / reprise** du projet (.json) | — |
| | **Cadre réglementaire et sources** | Textes et doctrines avec **statut de vérification** (texte officiel / source administrative / source secondaire à vérifier) et liens | — |

Chaque page affiche ses **sources** ; les **synthèses rédigées automatiquement** ne contiennent que des valeurs
calculées par l'application et sont signalées comme « à relire ».

## Données mobilisées

Toutes les données sont **publiques et ouvertes** ; elles sont téléchargées à la demande puis mises en cache sur
disque.

| Donnée | Producteur / accès | Échelle |
|---|---|---|
| Limites communales et intercommunales, population | API Découpage administratif – <https://geo.api.gouv.fr> | Commune, EPCI |
| Registre parcellaire graphique 2015 → 2025 | IGN / ASP – Géoplateforme, WFS `RPG.LATEST:parcelles_graphiques` et millésimes – <https://data.geopf.fr> | Parcelle |
| Recensement agricole 2020 (exploitations, SAU, évolutions 2010-2020) | Agreste, via les téléchargements open data de l'Observatoire des territoires (ANCT) | Commune → région |
| Indicateurs RA 2020 détaillés | Cartostat / DISAR (Agreste), **par import des fichiers exportés** | Commune |
| Établissements amont/aval, coopératives, CUMA, orientations NAF | INSEE SIRENE / INPI RNE via l'API Recherche d'entreprises – <https://recherche-entreprises.api.gouv.fr> | Établissement |
| Opérateurs bio | Agence Bio – <https://opendata.agencebio.org> | Opérateur |
| Aires AOC/AOP, IGP/IG et produits | INAO – data.gouv.fr | Commune |
| Mutations foncières | DGFiP DVF via l'API Données foncières du Cerema – <https://apidf-preprod.cerema.fr> | Mutation |
| Nomenclature NAF rév. 2 | INSEE (fichier `epa/data/naf2008_n5.csv`) | — |
| Couches cartographiques | Géoplateforme IGN (WMS raster et vecteur, WMTS) | — |

> Les cartes interactives (Folium / Leaflet) chargent la bibliothèque Leaflet depuis des CDN publics
> (cdn.jsdelivr.net, cdnjs.cloudflare.com, code.jquery.com) : le navigateur doit pouvoir y accéder.

## Lancer l'application sur Onyxia (SSP Cloud) avec VS Code

1. **Créer le service** : dans le catalogue Onyxia, choisir **VSCode-python**. Avant de cliquer sur *Lancer*,
   ouvrir la configuration du service et, dans l'onglet **Networking**, activer l'option de **port personnalisé**
   (« custom service port » / port utilisateur), en laissant le port proposé (5000 par défaut dans les charts Onyxia
   d'InseeFrLab ; vérifiez la valeur affichée sur votre instance).
   *Facultatif* : dans l'onglet Git, renseigner l'URL de ce dépôt pour qu'il soit cloné automatiquement.
2. **Récupérer le code** dans le terminal de VS Code (si le dépôt n'a pas été cloné automatiquement) :
   ```bash
   git clone https://github.com/Matteolng/Intelligence_artificielle.git
   cd Intelligence_artificielle/epa_studio
   ```
3. **Installer et lancer** :
   ```bash
   bash lancer.sh            # installe les dépendances puis lance Streamlit sur le port 5000
   # ou, manuellement :
   pip install -r requirements.txt
   streamlit run app.py --server.port 5000 --server.address 0.0.0.0
   ```
   Si votre service utilise un autre port personnalisé : `PORT=8000 bash lancer.sh`.
4. **Ouvrir l'application** : l'adresse publique associée au port personnalisé est indiquée dans la page du service
   sur Onyxia (README du service / informations de connexion). Ne pas utiliser l'adresse `localhost` affichée dans le
   terminal.
   *Alternative* : VS Code détecte souvent le port ouvert et propose de l'ouvrir via son proxy (onglet **Ports**).
5. **Conserver le cache entre deux sessions** (recommandé) : placer le cache dans le dossier persistant du service
   (habituellement `/home/onyxia/work`) :
   ```bash
   export EPA_CACHE_DIR=/home/onyxia/work/.cache_epa
   bash lancer.sh
   ```

Le fichier `.streamlit/config.toml` désactive les protections CORS / XSRF de Streamlit, ce qui évite des refus
d'envoi de fichiers derrière le proxy d'Onyxia. Réactivez-les si l'application est exposée publiquement.

## Lancer l'application en local

Python ≥ 3.10 recommandé (testé avec Python 3.13, Streamlit 1.67, pandas 3.0, GeoPandas 1.2).

```bash
cd epa_studio
python -m venv .venv && source .venv/bin/activate      # Windows : .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Puis ouvrir <http://localhost:8501>.

## Structure du code

```
epa_studio/
├── app.py                  # point d'entrée : navigation entre les pages
├── lancer.sh               # installation + lancement (Onyxia)
├── requirements.txt
├── .streamlit/config.toml  # thème et paramètres serveur
├── app_pages/              # une page Streamlit par étape (p00 … p12)
├── epa/                    # logique métier, indépendante de l'interface
│   ├── config.py           # URL des services, couches WMS, codes NAF, nomenclatures, palettes
│   ├── http.py             # session HTTP avec reprises, limitation de débit, cache disque
│   ├── territoire.py       # régions, départements, EPCI, communes (geo.api.gouv.fr)
│   ├── rpg.py              # RPG : téléchargement WFS paginé, rattachement communal, statistiques, emprise
│   ├── agreste.py          # RA 2020 (Observatoire des territoires) + import Cartostat / DISAR
│   ├── filieres.py         # SIRENE : filières amont/aval, coopératives, orientations NAF
│   ├── bio_siqo.py         # Agence Bio, INAO (AOC/AOP, IGP/IG)
│   ├── foncier.py          # DVF (Cerema) : mutations agricoles et prix à l'hectare
│   ├── projet.py           # fiche projet, emprise (import / dessin), contrôles agrivoltaïques
│   ├── compensation.py     # évaluation financière et compensation collective
│   ├── reglementation.py   # référentiel réglementaire sourcé + test d'assujettissement
│   ├── analyse.py          # synthèses rédigées automatiquement (formats français)
│   ├── cartes.py           # cartes Folium interactives et cartes statiques pour le rapport
│   ├── rapport.py          # rapport Word (python-docx) et export Excel
│   ├── ui.py               # composants d'interface et état de session
│   └── data/               # nomenclature NAF (INSEE) et codes cultures du RPG
└── tests/                  # tests unitaires et parcours complet (AppTest)
```

## Méthodes, limites et précautions

- **RPG** : ne recense que les surfaces déclarées à la PAC ; il peut sous-estimer la SAU (maraîchage, petites
  exploitations, surfaces non primées). Les parcelles sont rattachées à la commune contenant leur point intérieur ;
  surfaces recalculées en Lambert-93.
- **RA 2020** : données localisées à la commune du siège ; secret statistique sur certaines communes. Les
  évolutions 2010-2020 du territoire sont recalculées à partir des valeurs 2010 reconstituées commune par commune.
- **SIRENE** : le code NAF est déclaratif ; les effectifs sont des tranches (l'application affiche une fourchette).
  La liste des établissements doit être vérifiée et complétée par des entretiens.
- **DVF** : hors Alsace, Moselle et Mayotte ; une mutation peut regrouper des biens hétérogènes ; filtres
  d'exploitabilité paramétrables et rappelés dans le rapport.
- **Compensation collective** : il n'existe pas de méthode nationale unique. L'outil applique une méthode générique
  (perte primaire + aval, × durée de reconstitution, ÷ ratio d'investissement) dont **tous les coefficients doivent
  être ceux de la doctrine départementale**. Tant que la case de validation n'est pas cochée, le rapport signale le
  calcul comme provisoire.
- **Réglementation** : le référentiel (page *Cadre réglementaire et sources*) indique pour chaque règle si elle a été
  vérifiée sur un texte officiel ou sur une source secondaire. Plusieurs points récents (seuil d'évaluation
  environnementale du photovoltaïque au sol relevé à 3 MWc en 2026 selon la presse spécialisée, décision du Conseil
  d'État du 17 novembre 2026 sur l'articulation étude d'impact / EPA, champ du plafond de 40 % de couverture) sont
  signalés **à vérifier sur Légifrance**.
- L'outil ne remplace ni les enquêtes de terrain, ni les entretiens avec les exploitants et les filières, ni
  l'expertise du chargé d'études et l'avis des services instructeurs.

## Personnaliser l'outil

- **Ajouter une couche cartographique** : compléter `WMS_LAYERS` dans `epa/config.py` (nom de couche relevé dans le
  GetCapabilities de `https://data.geopf.fr/wms-r/wms` ou `https://data.geopf.fr/wms-v/ows`).
- **Modifier les filières** : listes de codes NAF dans `FILIERES` (`epa/config.py`).
- **Changer les familles de cultures** : `RPG_FAMILLES` et `FAMILLE_COLORS`.
- **Adapter la compensation à une doctrine** : `epa/compensation.py` (formule) et `app_pages/p10_compensation.py`
  (paramètres, valeurs proposées).
- **Mettre à jour le référentiel** : `REFERENTIEL` dans `epa/reglementation.py` (contenu, statut, sources).
- **Cache** : `EPA_CACHE_DIR` (par défaut `~/.cache/epa_studio`) ; durées de validité dans `CACHE_TTL_DAYS`. Le cache
  peut être vidé depuis la page d'accueil.

## Tests

```bash
pip install pytest
pytest -q tests/test_calculs.py      # tests unitaires, hors ligne
pytest -q tests/test_pages.py        # parcours complet des 13 pages sur un territoire réel (accès Internet requis)
```
