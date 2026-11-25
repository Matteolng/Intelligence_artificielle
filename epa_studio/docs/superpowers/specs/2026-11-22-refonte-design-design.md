# Refonte du design d'EPA Studio – document de conception

Date : 2026-11-22 · Statut : direction et plan des pages approuvés par l'utilisateur (« c'est bien »),
avec la consigne : **l'EI l'utilisateur sert uniquement de référence de contenu, pas de modèle visuel ; viser classe et pro.**

## Intention
Présenter EPA Studio à des bureaux d'études agricoles . L'outil doit impressionner en démonstration et
servir au quotidien : il automatise les cartes, tableaux et chiffres récurrents d'une étude préalable agricole ; le
chargé d'études garde la rédaction de l'analyse.

## Objectifs
1. Identité SaaS sobre, inspirée des principes d'Apple (fiche « Design System Inspired by Apple », getdesign.md / VoltAgent, MIT) :
   neutres clairs, une seule couleur d'accent, typographie forte, beaucoup d'air.
2. Marque blanche : nom, couleur d'accent et logo du bureau d'études configurables (`.streamlit/secrets` non requis :
   fichier `epa_studio/branding.toml` + écran Réglages en session). Aucune marque en dur.
3. Navigation par étapes : Cadrage → État initial → Impacts → Livrables (sequence réelle, numérotation justifiée).
4. Accueil qui montre la valeur en 10 s : bouton « Ouvrir la démonstration », aperçu de ce qui est produit.
5. Mode démonstration : territoire d'exemple, données réelles pré-téléchargées et mises en cache dans le dépôt.
6. Figures types générées automatiquement, exportables en PNG haute définition (300 dpi) avec titre et source :
   RPG par année sur ortho ; localisation 3 échelles ; OTEX par commune ; CLC 2018 ; sols ; chiffres clés comparés.
7. Phrases de synthèse par gabarit (sans IA) + bibliographie construite à partir des sources réellement interrogées.

## Non-objectifs / anti-objectifs
- Pas de réécriture : calculs et tests existants conservés.
- Échec même si « ça marche » : toute valeur inventée, tout substitut silencieux à une donnée manquante, tout look
  générique (cartes arrondies identiques, dégradés décoratifs, émojis partout, libellés en capitales).
- Ne pas copier la charte de l'EI fournie (vert/jaune, bandeaux).

## Contraintes vérifiées
- Streamlit 1.67 ; thème via `.streamlit/config.toml` (primaryColor, font avec URL Google Fonts, fontFaces, sidebar) – Context7.
- Réseau : toutes les API utilisées répondent depuis l'environnement (pas de refus du proxy).
- Géoplateforme WMS : `LANDCOVER.CLC18_FR` et `INRAE_CARTE-SOLS` présents ; **aucune couche de réserve utile ni de
  profondeur de sol** trouvée dans les GetCapabilities wms-r. → Ces deux figures sont affichées « donnée non disponible
  automatiquement » avec import possible d'un fichier fourni par l'utilisateur ; jamais de substitut.
- OTEX communales : non fournies par l'Observatoire des territoires ; l'app accepte déjà un export Cartostat/DISAR.
  Sans fichier, la carte OTEX est signalée manquante.
- France entière : calculée comme somme des départements publiés par l'Observatoire des territoires (méthode affichée).

## Approches envisagées
- **A. Thème natif + CSS ciblé + composants Python (retenue).** `config.toml` pour couleurs/police, une feuille de style
  courte dans `epa/ui.py`, composants réutilisables (en-tête de page, tuile comparative, phrase, état manquant, carte
  figure avec export). Faible risque, garde `st.navigation`.
- B. Composants HTML/JS personnalisés (iframes) : rendu plus libre mais fragile, lent, casse les tests de pages.
- C. Changer de framework : exclu par la consigne.

## Système visuel
- Couleurs : fond `#F5F5F7`, surface `#FFFFFF`, texte `#1D1D1F`, secondaire `#6E6E73`, filets `#D2D2D7`,
  accent bureau (défaut `#2F6B3A`). Accent réservé aux actions, liens, étape active.
- États : manquant `#86868B` (gris, texte explicite), alerte `#B25000`, erreur `#C4302B`.
- Type : Inter (Google Fonts, repli sans-serif). Titres 600, chiffres clés 300 en grand, corps 15–16 px, phrases en
  casse normale, pas de capitales.
- Profondeur : pas d'ombres portées génériques ; séparation par fond gris/blanc et filets fins. Rayons : 12 px conteneurs,
  8 px contrôles.
- Graphiques/cartes : palette du skill dataviz (validée daltonisme), cohérente entre Plotly, matplotlib et folium.

## Pages
| Étape | Page | Contenu clé |
|---|---|---|
| — | Accueil | Démo en un clic, ce que l'outil produit, sources ouvertes |
| 1 Cadrage | Territoire ; Projet et emprise | Localisation 3 échelles |
| 2 État initial | Chiffres clés ; Occupation (RPG) ; Exploitations ; Filières ; Qualité/bio ; Foncier ; Atlas | Tuiles comparées + phrases, RPG par année, CLC, OTEX, sols |
| 3 Impacts | Effets et ERC ; Compensation | inchangé (restylé) |
| 4 Livrables | Figures ; Rapport et exports ; Sources et bibliographie | Galerie PNG HD, Word, Excel, biblio |
| — | Réglages | Nom, couleur, logo du bureau ; démo |

## Laissé au constructeur
Détail des gabarits de phrases, mise en page exacte des figures, structure du cache démo.


> Note (25/11/2026) : la démonstration ne repose plus sur un territoire fixe ; voir la conception v2.
