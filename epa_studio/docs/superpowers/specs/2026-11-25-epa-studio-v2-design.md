# EPA Studio v2 – conception

Statut : approuvé par l'utilisateur le 25/11/2026 (maquette https://claude.ai/artifact/1DcWSDJyXTV9HDUXRedjjh, variante B retenue).

## Intention
EPA Studio prépare la partie répétitive d'une étude préalable agricole (cartes, tableaux, chiffres, sources) aux
4 échelles du territoire et aux couleurs du bureau d'études. L'analyse et la rédaction restent au chargé d'études.

## Périmètre de cette version
1. Démonstration sans site client : l'utilisateur clique n'importe où sur une carte de France ; la commune (API
   Découpage administratif, recherche par coordonnées) et son intercommunalité deviennent le périmètre. Option : une
   emprise de démonstration, toujours étiquetée « fictive ». Plus aucune référence à un projet client dans le code.
2. Cadrage : périmètre proposé = communes intersectant l'emprise et leurs intercommunalités (les communes des sièges
   d'exploitation ne sont pas publiques : ajout manuel), indicateurs recalculés en direct, paragraphe de justification.
3. Quatre échelles : périmètre, département, région, France dans les chiffres clés et les phrases générées.
4. Données : OTEX communale automatique (data.gouv.fr, « OTEX en 12 postes », Agreste RA 2020, publié par TACCT) ;
   réserve utile Gis Sol si un service est joignable, sinon « non intégrée à ce stade » ; année de la donnée sur chaque figure.
5. Foncier : barème indicatif de la valeur vénale (décision annuelle au JO, par petite région agricole) si la
   correspondance commune → petite région agricole est disponible en source ouverte ; sinon signalé manquant.
6. Compensation : article L. 112-1-3 IV du code rural (loi n° 2026-796 du 18 août 2026, en vigueur le 20/08/2026) –
   pour l'agrivoltaïsme, seules les surfaces soustraites à toute activité agricole (définitivement ou de manière
   réversible) sont compensées ; préréglages départementaux limités aux valeurs documentées par une source citée.
7. Bibliothèque partagée : analyses par département, intercommunalité et région calculées une fois et réutilisées ;
   projets sauvegardés et ouverts par lien (`?projet=<id>`). Partage effectif entre les utilisateurs d'une même instance.
8. Livrables : export PowerPoint (python-pptx) dans le style retenu, Word et Excel existants.
9. Marque blanche : logo, couleur, police (choix parmi des polices libres) et gabarits Word / PowerPoint déposés.

## Design (validé sur maquette)
- Palette : olive `#56653E`, crème `#F4ECDF`, vert nuit `#18211A`/`#1F2A22`, accent clair `#DCE5BC`.
- Type : Cormorant Garamond (titres, italique pour la seconde partie), Inter (texte, chiffres de tableaux).
- Variante B (nuit, verre dépoli, photo aérienne IGN du territoire, gravure du parcellaire, cercles emboîtés des
  4 échelles, animations sobres) : accueil, démonstration, en-têtes de page, chiffres clés.
- Pages denses et de conclusion : version sobre (gravure claire, feuilles translucides, peu d'animation).
- Animations désactivées si l'utilisateur demande moins de mouvement.
- Figures exportées : fond blanc, sobres, titre, source et année.

## Non-objectifs
Comptes multi-clients, hébergement, base des EPA (V2), module ETE (V3), pitch.

## Règles
Aucune donnée inventée ; toute valeur cite sa source et son millésime ; une donnée absente est affichée comme manquante.
