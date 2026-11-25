# EPA Studio v2 – plan d'implémentation

> Exécution native (superpowers:executing-plans), commit après chaque tâche, tests existants toujours verts.

**Spec :** `docs/superpowers/specs/2026-11-25-epa-studio-v2-design.md`

## Contraintes globales
- Aucune donnée inventée ; source + millésime partout ; manquant explicite.
- Python 3.13, Streamlit 1.67 ; nouvelles dépendances : python-pptx.
- Aucune mention de projet client dans le code, les données livrées ou la documentation courante.

## Points de vigilance (tests dédiés)
1. Clic hors de France (mer, étranger) → message clair, pas d'exception (`test_point_hors_france`).
2. Commune sans intercommunalité (îles) → périmètre = la commune seule (`test_point_sans_epci`).
3. Région absente du fichier ODT → tuile « non disponible » (`test_comparaison_region_absente`).
4. Projet partagé dont l'identifiant n'existe pas → message, pas de plantage (`test_projet_inconnu`).
5. Agrivoltaïque sans démonstration L. 314-36 → l'utilisateur choisit ; défaut : surfaces soustraites seules
   compensées, avertissement si la poursuite agricole n'est pas documentée (`test_compensation_loi_2026`).

## Tâches
1. **Confidentialité et démo par clic** – `epa/demo.py` (`perimetre_depuis_point(lat, lon) -> dict`,
   `emprise_fictive(lat, lon, surface_ha=20) -> GeoDataFrame`), suppression du cache de démo et des mentions de projet
   client, carte de France cliquable sur l'accueil.
2. **Quatre échelles** – `chiffres_cles.comparaison(..., df_reg, code_reg)` ajoute la région ;
   `gabarits.phrase_evolution` accepte `v_reg`.
3. **OTEX automatique** – `epa/otex.py` (`otex_communes() -> DataFrame[codgeo, otex]`), branché sur la carte OTEX.
4. **Périmètre proposé et justification** – `epa/perimetre.py` (`proposer(emprise) -> dict`,
   `texte_justification(...) -> str`), recalcul en direct des chiffres clés sur la page Territoire.
5. **Design v2** – `epa/theme.py` (CSS variante B / sobre, en-tête photo, gravure générée depuis l'ortho du
   territoire, cercles des 4 échelles en SVG), `.streamlit/config.toml`, accueil et chiffres clés refaits.
6. **Bibliothèque partagée et projets par lien** – `epa/bibliotheque.py` (`analyse(nature, code, calcul)`,
   `inventaire()`), `epa/projets.py` (`enregistrer(state) -> id`, `charger(id, state)`), page Bibliothèque.
7. **Compensation loi 2026 et préréglages** – `compensation.Parametres.regime` (`"L112-1-3 IV"`), préréglages
   documentés (`PRESETS`), référentiel mis à jour avec l'article L. 112-1-3 (Légifrance).
8. **Foncier : barème valeur vénale** – si la correspondance commune → PRA est trouvée en source ouverte.
9. **Export PowerPoint** – `epa/diapos.py` (`build_pptx(ctx, branding) -> bytes`).
10. **Marque blanche complète** – logo, police, gabarits Word/PowerPoint déposés (page Réglages).
11. **Réserve utile Gis Sol** – intégration si un service est joignable ; sinon libellé « non intégrée à ce stade ».
12. **Vérification** – captures de chaque page, tests, revue de code, push.
