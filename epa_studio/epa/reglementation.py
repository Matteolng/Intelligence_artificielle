"""Référentiel réglementaire et méthodologique (EPA, compensation collective, agrivoltaïsme).

Chaque élément porte un statut de vérification :
- "Texte officiel" : contenu lu sur une source officielle (Légifrance, ministère) ;
- "Source administrative" : guide ou page d'un service de l'État (DDT, DRAAF, préfecture) ;
- "Source secondaire – à vérifier" : article de presse, cabinet d'avocats, blog spécialisé.

Le texte consolidé sur Légifrance fait foi. Ce référentiel a été établi en novembre 2026.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .analyse import fnum

OFFICIEL = "Texte officiel"
ADMIN = "Source administrative"
SECONDAIRE = "Source secondaire – à vérifier"


@dataclass
class Item:
    theme: str
    titre: str
    contenu: str
    statut: str
    sources: list[tuple[str, str]] = field(default_factory=list)


REFERENTIEL: list[Item] = [
    # ------------------------------------------------------------------ EPA
    Item(
        "Étude préalable agricole",
        "Base légale",
        "L'étude préalable agricole et la compensation collective agricole sont prévues par l'article L. 112-1-3 du code rural "
        "et de la pêche maritime (CRPM). Leurs modalités d'application ont été fixées par le décret n° 2016-1190 du 31 août 2016, "
        "codifié aux articles D. 112-1-18 et suivants du CRPM.",
        OFFICIEL,
        [("Décret n° 2016-1190 du 31 août 2016 – Légifrance", "https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000033084702"),
         ("Instruction technique DGPE/SDPE/2016-761", "https://info.agriculture.gouv.fr/boagri/instruction-2016-761")],
    ),
    Item(
        "Étude préalable agricole",
        "Trois conditions cumulatives (art. D. 112-1-18 CRPM)",
        "• Nature : projet soumis, par sa nature, ses dimensions ou sa localisation, à une évaluation environnementale systématique.\n"
        "• Localisation : emprise située (i) en zone agricole, forestière ou naturelle d'un document d'urbanisme opposable, affectée "
        "à une activité agricole dans les 5 ans précédant le dépôt du dossier ; ou (ii) en zone à urbaniser, affectée à une activité "
        "agricole dans les 3 ans ; ou (iii) en l'absence de document d'urbanisme délimitant ces zones, sur toute surface affectée à "
        "une activité agricole dans les 5 ans.\n"
        "• Consistance : surface prélevée de manière définitive supérieure ou égale à un seuil fixé à 5 ha par défaut ; le préfet peut "
        "fixer par arrêté un ou plusieurs seuils départementaux compris entre 1 et 10 ha.",
        ADMIN,
        [("Préfecture des Deux-Sèvres – Seuil et conditions de l'étude préalable",
          "https://www.deux-sevres.gouv.fr/Actions-de-l-Etat/Agriculture-foret-et-developpement-rural/Foncier-agricole/Compensation-collective-agricole/Seuil-et-conditions-de-l-etude-prealable"),
         ("Préfecture du Finistère – Présentation du dispositif",
          "https://www.finistere.gouv.fr/Actions-de-l-Etat/Agriculture-foret-et-developpement-rural/Etude-prealable-et-compensations-agricoles-collectives/Presentation-du-dispositif-d-etude-prealable-et-de-compensation-collective-agricole"),
         ("Préfecture de Côte-d'Or – Contexte",
          "https://www.cote-dor.gouv.fr/Actions-de-l-Etat/Agriculture.-foret-et-developpement-rural/Agriculture/Exploitations-agricoles-foncier-controle-des-structures/Etude-prealable-agricole-et-compensations-collectives-agricoles/Contexte")],
    ),
    Item(
        "Étude préalable agricole",
        "Contenu de l'étude (art. D. 112-1-19 CRPM)",
        "1° Description du projet et délimitation du territoire concerné ;\n"
        "2° Analyse de l'état initial de l'économie agricole du territoire concerné (production agricole primaire, première "
        "transformation et commercialisation par les exploitants) ;\n"
        "3° Étude des effets positifs et négatifs du projet sur l'économie agricole, comprenant l'évaluation de l'impact sur "
        "l'emploi, l'évaluation financière globale des impacts et les effets cumulés avec d'autres projets connus ;\n"
        "4° Mesures envisagées et retenues pour éviter et réduire les effets négatifs notables du projet ;\n"
        "5° Le cas échéant, mesures de compensation collective envisagées pour consolider l'économie agricole du territoire, "
        "évaluation de leur coût et modalités de mise en œuvre.",
        ADMIN,
        [("Préfecture du Bas-Rhin – Note de cadrage étude préalable",
          "https://www.bas-rhin.gouv.fr/contenu/telechargement/38074/251162/file/Note+de+cadrage+%C3%A9tude+prealable.pdf"),
         ("DRAAF Nouvelle-Aquitaine – Guide méthodologique compensation collective agricole",
          "https://draaf.nouvelle-aquitaine.agriculture.gouv.fr/IMG/pdf/Guide_methodoV1_cle086471.pdf")],
    ),
    Item(
        "Étude préalable agricole",
        "Procédure",
        "Le maître d'ouvrage adresse l'étude au préfet, qui saisit la CDPENAF. La commission rend un avis motivé (délai de deux mois "
        "indiqué par les services de l'État). Le préfet émet ensuite un avis motivé sur la nécessité de mesures de compensation "
        "collective et sur leur importance. L'étude préalable n'est pas soumise à enquête publique.",
        ADMIN,
        [("Préfecture des Deux-Sèvres – Seuil et conditions de l'étude préalable",
          "https://www.deux-sevres.gouv.fr/Actions-de-l-Etat/Agriculture-foret-et-developpement-rural/Foncier-agricole/Compensation-collective-agricole/Seuil-et-conditions-de-l-etude-prealable")],
    ),
    Item(
        "Étude préalable agricole",
        "Articulation avec l'étude d'impact (jurisprudence récente)",
        "Selon le cabinet Gossement Avocats, le Conseil d'État (17 novembre 2026, n° 503389) a jugé que l'étude d'impact ne "
        "dispense pas de l'étude préalable agricole et a annulé partiellement l'instruction technique du 11 février 2025. "
        "Décision à consulter avant toute utilisation.",
        SECONDAIRE,
        [("Gossement Avocats – commentaire de CE 17 nov. 2026 n° 503389",
          "https://www.gossement-avocats.com/blog/evaluation-environnementale-letude-dimpact-ne-dispense-pas-de-letude-prealable-agricole-conseil-detat-17-novembre-2026-n503389-annulation-partielle-de-linstruction-technique-du/"),
         ("Instruction technique DGPE 2025-93 (Bulletin officiel du ministère)", "https://info.agriculture.gouv.fr/boagri/instruction-2025-93")],
    ),
    Item(
        "Étude préalable agricole",
        "Seuils d'évaluation environnementale des centrales photovoltaïques au sol",
        "La rubrique 30 de l'annexe à l'article R. 122-2 du code de l'environnement soumettait à évaluation environnementale "
        "systématique les installations au sol d'au moins 1 MWc (cas par cas entre 300 kWc et 1 MWc). D'après pv magazine "
        "(30 juillet 2026), le décret n° 2026-674 du 27 juillet 2026 a relevé ce seuil à 3 MWc. Les sources consultées ne "
        "concordent pas toutes : vérifier la version en vigueur de R. 122-2, car elle conditionne la « condition de nature » de l'EPA.",
        SECONDAIRE,
        [("pv magazine France – 30/07/2026", "https://www.pv-magazine.fr/2026/07/30/photovoltaique-le-seuil-devaluation-environnementale-systematique-releve-de-1-a-3-mwc/"),
         ("MRAe – exemple d'avis (seuil 1 MWc, 2023)", "https://www.mrae.developpement-durable.gouv.fr/IMG/pdf/a_2023-4781_installation-photovoltaique-sol_vernon_delibere.pdf")],
    ),
    # ------------------------------------------------------------------ Compensation
    Item(
        "Compensation collective",
        "Méthodes de calcul (doctrines départementales)",
        "Il n'existe pas de méthode nationale unique. Les guides départementaux convergent vers : (1) estimation de la perte annuelle "
        "de production agricole primaire (produit brut ou valeur ajoutée par hectare × surface) ; (2) ajout de la valeur ajoutée "
        "perdue par les filières aval (coefficient IAA) ; (3) multiplication par une durée de reconstitution du potentiel (environ "
        "7 ans dans la doctrine de l'Ardèche) ; (4) division par un ratio d'investissement (ex. 5,6 € dans le guide de la Haute-Saône ; "
        "6,69 € de production pour 1 € investi en PACA selon la Chambre d'agriculture 13). Les coefficients sont propres à chaque "
        "département : utiliser la doctrine locale.",
        ADMIN,
        [("DDT de la Haute-Saône – Guide études préalables (2020)",
          "https://www.haute-saone.gouv.fr/contenu/telechargement/34412/243949/file/2020_DDT70_guide%20etude%20prealable%20compensation%20agricole.pdf"),
         ("Chambre d'agriculture des Bouches-du-Rhône – Méthodologie",
          "https://www.bouches-du-rhone.gouv.fr/content/download/30691/179521/file/M%C3%A9thodologie%20CA13%20-%20Compensation%20collective%20agricole.pdf"),
         ("DDT de l'Ardèche – Doctrine compensation agricole collective",
          "https://ardeche.chambres-agriculture.fr/fileadmin/user_upload/237_chambre_d_agriculture_de_l_ardeche/Publications/Foncier/ddt_do_doctrine-compensation-agricole-collective-07_22-06.pdf"),
         ("Préfecture des Alpes-de-Haute-Provence – Guide compensation agricole",
          "https://www.alpes-de-haute-provence.gouv.fr/content/download/20741/120854/file/Guide%20compensation%20agricole%20V4.pdf"),
         ("Chambres d'agriculture – Outils et méthodes pour l'émergence de projets de compensation",
          "https://opera-connaissances.chambres-agriculture.fr/doc_num.php?explnum_id=196953")],
    ),
    Item(
        "Compensation collective",
        "Agrivoltaïsme : surfaces soumises à compensation (art. L. 112-1-3 IV, loi du 18 août 2026)",
        "Depuis le 20 août 2026, l'article L. 112-1-3 du code rural, modifié par l'article 30 de la loi n° 2026-796 du 18 août 2026 "
        "d'urgence pour la protection et la souveraineté agricoles, soumet expressément les installations agrivoltaïques à l'étude "
        "préalable (I). Son IV dispose que, pour ces installations, « les mesures de compensation collective [...] ne s'appliquent "
        "qu'à raison des surfaces soustraites à toute activité agricole de manière définitive ou réversible » et que « ne sont pas "
        "soumises à la compensation collective les surfaces situées sous les dispositifs de production d'énergie solaire sur "
        "lesquelles l'activité agricole se poursuit dans les conditions prévues à l'article L. 314-36 du code de l'énergie ». "
        "Le II prévoit, en cas de manquement, mise en demeure, consignation, exécution d'office, amende administrative jusqu'à "
        "30 000 € et astreinte journalière jusqu'à 1 500 €.",
        OFFICIEL,
        [("Code rural, art. L. 112-1-3 (version en vigueur depuis le 20/08/2026) – Légifrance",
          "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000054715854"),
         ("Loi n° 2026-796 du 18 août 2026 – Légifrance", "https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000054707007"),
         ("Kohen Avocats – analyse (26/08/2026)", "https://kohenavocats.fr/2026/08/26/agrivoltaisme-compensation-agricole-collective-loi-18-aout-2026/")],
    ),
    # ------------------------------------------------------------------ Agrivoltaïsme
    Item(
        "Agrivoltaïsme",
        "Définition légale (art. L. 314-36 code de l'énergie, loi APER)",
        "La loi n° 2023-175 du 10 mars 2023 (APER), article 54, a défini l'installation agrivoltaïque : installation dont les modules "
        "sont situés sur une parcelle agricole et qui contribue durablement à l'installation, au maintien ou au développement d'une "
        "production agricole, en apportant directement à la parcelle au moins un des services suivants : amélioration du potentiel "
        "et de l'impact agronomiques, adaptation au changement climatique, protection contre les aléas, amélioration du bien-être "
        "animal. La production agricole doit rester l'activité principale de la parcelle.",
        SECONDAIRE,
        [("Gossement Avocats – cadre juridique de l'agrivoltaïsme après le décret du 8 avril 2024", "https://www.gossement-avocats.com/blog/agrivoltaisme-1/"),
         ("DREAL Pays de la Loire / DDT 72 – formation agrivoltaïsme (avril 2025)",
          "https://www.pays-de-la-loire.developpement-durable.gouv.fr/IMG/pdf/20250401_formation_ce_dreal-ddt72_agrivoltaisme.pdf")],
    ),
    Item(
        "Agrivoltaïsme",
        "Critères du décret n° 2024-318 du 8 avril 2024 (art. R. 314-108 et s. code de l'énergie)",
        "• Rendement : hors élevage, rendement moyen par hectare de la parcelle équipée supérieur à 90 % de celui d'une zone témoin "
        "ou d'un référentiel en faisant office.\n"
        "• Zone témoin : obligatoire, avec des dérogations (notamment taux de couverture inférieur à 40 % et impossibilité technique, "
        "ou technologies éprouvées listées par arrêté).\n"
        "• Taux de couverture : plafond de 40 % ; selon plusieurs sources il s'applique aux installations de plus de 10 MWc ne "
        "relevant pas d'une technologie éprouvée (les sources divergent sur son champ d'application).\n"
        "Le Conseil d'État a rejeté les recours contre ce décret le 16 mars 2026 (n° 495025).",
        SECONDAIRE,
        [("Décret n° 2024-318 – Légifrance", "https://www.legifrance.gouv.fr/jorf/id/JORFSCTA000049386046"),
         ("Le Moniteur – Agrivoltaïsme : le cadre réglementaire est paru",
          "https://www.lemoniteur.fr/article/agrivoltaisme-le-cadre-reglementaire-qui-va-permettre-d-enclencher-la-machine-est-paru.2327076"),
         ("Banque des Territoires – Développement de l'agrivoltaïsme : le décret-cadre publié",
          "https://www.banquedesterritoires.fr/developpement-de-lagrivoltaisme-le-decret-cadre-publie"),
         ("Conseil d'État – décision du 16 mars 2026 n° 495025", "https://www.conseil-etat.fr/fr/arianeweb/CE/decision/2026-03-16/495025")],
    ),
    Item(
        "Agrivoltaïsme",
        "Autorisation d'urbanisme et CDPENAF (art. L. 111-27 et s. code de l'urbanisme)",
        "Les installations agrivoltaïques sont assimilées à des installations nécessaires à l'exploitation agricole. Leur autorisation "
        "en zone agricole, naturelle ou forestière est subordonnée à l'avis conforme de la CDPENAF (avis réputé favorable faute de "
        "réponse sous deux mois selon un commentaire du décret).",
        SECONDAIRE,
        [("Revue générale du droit – Développement de l'agrivoltaïsme (janv. 2025)",
          "https://www.revuegeneraledudroit.eu/blog/2025/01/15/developpement-de-lagrivoltaisme-entre-espoirs-et-desillusions"),
         ("Landot Avocats – Les nuages s'éloignent pour le droit de l'agrivoltaïsme (mars 2026)",
          "https://blog.landot-avocats.net/2026/03/23/les-nuages-seloignent-pour-le-droit-de-lagrivoltaisme/amp/")],
    ),
    Item(
        "Agrivoltaïsme",
        "Photovoltaïque au sol non agrivoltaïque – document-cadre (art. L. 111-29 code de l'urbanisme)",
        "« Aucun ouvrage de production d'électricité à partir de l'énergie solaire, hors installations agrivoltaïques au sens de "
        "l'article L. 314-36 du code de l'énergie, ne peut être implanté en dehors des surfaces identifiées dans un document-cadre. » "
        "Le document-cadre est proposé par la chambre départementale d'agriculture et arrêté par le préfet ; les installations "
        "doivent être compatibles avec une activité agricole, pastorale ou forestière.",
        OFFICIEL,
        [("Article L111-29 – Code de l'urbanisme (Légifrance)", "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000047298109"),
         ("CAUE Gironde – Le décret précise le cadre juridique des installations photovoltaïques",
          "https://www.cauegironde.com/Un-decret-precise-le-cadre-juridique-des-installations-photovoltaiques/")],
    ),
    # ------------------------------------------------------------------ Outils existants
    Item(
        "Outils existants",
        "Plateformes publiques complémentaires",
        "• Cartostat – Agreste (56 indicateurs communaux du RA 2020 : OTEX, PBS, UGB, emploi, âge des chefs…).\n"
        "• Territoires Fertiles (rapprochement de CRATer – Les Greniers d'Abondance – et PARCEL – Terre de Liens) : diagnostic de "
        "résilience alimentaire par territoire.\n"
        "• Géoportail / Géoplateforme IGN (RPG, ortho, zonages), Géoportail de l'urbanisme (PLU, SUP).\n"
        "• Observatoire des territoires (ANCT) : indicateurs RA 2020 téléchargeables.",
        ADMIN,
        [("Cartostat – Agreste", "https://stats.agriculture.gouv.fr/cartostat/"),
         ("Banque des Territoires – lancement de Territoires Fertiles",
          "https://www.banquedesterritoires.fr/territoires-fertiles-un-commun-numerique-daide-la-transition-alimentaire"),
         ("Observatoire des territoires – SAU 2020", "https://www.observatoire-des-territoires.gouv.fr/surface-agricole-utilisee-sau")],
    ),
]


SOURCES_DONNEES = [
    ("Découpage administratif (communes, EPCI, population)", "API Découpage administratif – geo.api.gouv.fr (DINUM)", "https://geo.api.gouv.fr", "Licence Ouverte 2.0"),
    ("Registre parcellaire graphique (RPG 2015 à 2025)", "IGN / ASP – Géoplateforme (WFS, WMS)", "https://data.geopf.fr", "Licence Ouverte 2.0"),
    ("Recensement agricole 2020 (exploitations, SAU, évolutions 2010-2020)", "Agreste – via l'Observatoire des territoires (ANCT)", "https://www.observatoire-des-territoires.gouv.fr", "Licence Ouverte"),
    ("Établissements amont/aval, coopératives, CUMA", "API Recherche d'entreprises (SIRENE INSEE, RNE INPI)", "https://recherche-entreprises.api.gouv.fr", "Licence Ouverte"),
    ("Opérateurs en agriculture biologique", "Agence Bio – annuaire open data", "https://opendata.agencebio.org", "Licence Ouverte"),
    ("Aires AOC/AOP, IGP/IG par commune et produits", "INAO – data.gouv.fr", "https://www.data.gouv.fr/organizations/institut-national-de-lorigine-et-de-la-qualite", "Licence Ouverte"),
    ("Transactions foncières (DVF)", "DGFiP – API Données foncières du Cerema", "https://apidf-preprod.cerema.fr", "Licence Ouverte"),
    ("Nomenclature NAF rév. 2", "INSEE", "https://www.insee.fr/fr/information/2120875", "Licence Ouverte"),
    ("Zonages environnementaux, urbanisme, occupation du sol, potentiel solaire", "Géoplateforme IGN (PatriNat, GPU, OCS GE, Cerema…)", "https://data.geopf.fr", "Selon producteur"),
]


# ---------------------------------------------------------------------------
# Test d'assujettissement (aide à la décision – ne remplace pas l'avis des services de l'État)
# ---------------------------------------------------------------------------

ZONES = {
    "A ou N d'un PLU / zone naturelle ou agricole d'un document d'urbanisme": 5,
    "AU d'un PLU (zone à urbaniser)": 3,
    "Absence de document d'urbanisme délimitant ces zones (RNU…)": 5,
    "Zone U / constructible": None,
}


def test_assujettissement(ee_systematique: str, zone: str, activite_agricole_annees: float | None,
                          surface_prelevee_ha: float, seuil_ha: float) -> tuple[str, list[str]]:
    """Retourne (verdict, explications) pour les trois conditions de l'art. D. 112-1-18."""
    notes = []
    ok_nature = {"Oui": True, "Non": False}.get(ee_systematique)
    if ok_nature is None:
        notes.append("Condition de nature : à déterminer (vérifier la rubrique applicable de l'annexe à l'article R. 122-2 du code de l'environnement).")
    else:
        notes.append(f"Condition de nature : {'remplie' if ok_nature else 'non remplie'} (évaluation environnementale systématique : {ee_systematique}).")
    delai = ZONES.get(zone)
    if delai is None:
        ok_loc = False
        notes.append("Condition de localisation : non remplie a priori (zone non visée par l'article D. 112-1-18).")
    elif activite_agricole_annees is None:
        ok_loc = None
        notes.append(f"Condition de localisation : à déterminer – activité agricole requise dans les {delai} ans précédant le dépôt.")
    else:
        ok_loc = activite_agricole_annees <= delai
        notes.append(
            f"Condition de localisation : {'remplie' if ok_loc else 'non remplie'} (dernière activité agricole il y a "
            f"{activite_agricole_annees:g} an(s) ; délai applicable : {delai} ans)."
        )
    ok_surf = surface_prelevee_ha >= seuil_ha
    notes.append(
        f"Condition de consistance : {'remplie' if ok_surf else 'non remplie'} (surface prélevée définitivement "
        f"{fnum(surface_prelevee_ha, 2)} ha ; seuil départemental {fnum(seuil_ha, 1)} ha)."
    )
    conds = [ok_nature, ok_loc, ok_surf]
    if all(c is True for c in conds):
        verdict = "Projet a priori soumis à étude préalable agricole"
    elif any(c is False for c in conds):
        verdict = "Projet a priori non soumis (au moins une condition non remplie)"
    else:
        verdict = "Assujettissement à confirmer (conditions à préciser)"
    notes.append("Résultat indicatif : à confirmer auprès de la DDT(M) / du service instructeur. Pour l'agrivoltaïsme, "
                 "les surfaces « prélevées » s'apprécient selon la doctrine locale (emprise totale, surfaces artificialisées…).")
    return verdict, notes
