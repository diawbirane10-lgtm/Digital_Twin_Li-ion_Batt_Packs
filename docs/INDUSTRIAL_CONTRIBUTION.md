# État de l’art industriel et zones de contribution

Recherche documentaire : 9 octobre 2026. Positionnement exploratoire, pas une
revue systématique ni une preuve de nouveauté scientifique.

## Ce qui existe déjà

| Domaine | Pratiques / capacités publiées | Sources primaires |
|---|---|---|
| BMS embarqué | Surveillance multicellule, SOC/SOH, équilibrage, architectures câblées et sans fil | Analog Devices : https://www.analog.com/en/solutions/automotive/electrification-and-powertrain/battery-management-systems-bms.html |
| Simulation et développement BMS | Identification ECM, modèles électriques et thermiques, estimation SOC/SOH, équilibrage, tests de défauts et génération de code | MathWorks : https://www.mathworks.com/help/simscape-battery/index.html ; https://www.mathworks.com/products/simscape-battery.html |
| Jumeau numérique de conception | Simulation du comportement batterie, conception du refroidissement, intégration cellule/module/pack | Siemens : https://www.siemens.com/en-gb/digital-thread/product-development/battery-engineering/ ; https://blogs.sw.siemens.com/en-US/simcenter/simcenter-battery-design-studio/ |
| Supervision de flottes | Télémétrie, suivi de santé, anomalies et prévision de vieillissement | Bosch : https://www.bosch-mobility.com/en/solutions/software/battery-in-the-cloud/lifetime-monitoring-and-anomaly-detection/ ; https://www.bosch-mobility.com/en/solutions/software/battery-in-the-cloud/aging-prediction/ |
| Ferroviaire à batteries | Stockage modulaire, gestion énergétique et thermique pour lignes non ou partiellement électrifiées | DLR/Stadler MOSENAS : https://www.dlr.de/en/fk/research-and-transfer/projects/vehicle-systems-and-technology-assessment/mosenas-modular-scalable-energy-storage-for-sustainable-local-rail-passenger-transport |

**Conséquence :** afficher SOC, SOH et une carte thermique constitue une interface
utile, mais pas une nouveauté industrielle en soi. Le projet peut apporter une
valeur démontrable par son accessibilité, sa reproductibilité et une question
technique traitée avec des comparaisons mesurées.

## État réel du dépôt

Atouts : ECM 2RC, EKF, modèle thermique simplifié, topologie configurable, données
NASA, API Python et notebooks. La nouvelle IHM relie réellement ces éléments.

Limites : paramètres d’une cellule de référence, pas de vieillissement couplé au
modèle cellule, pas d’équilibrage piloté, pas de profil mission industriel validé,
pas de diagnostic évalué, pas de validation thermique indépendante. Le serveur
n’est pas un contrôleur BMS de sûreté.

La tension attendue par `BatteryDigitalTwin.update` est la tension PACK malgré
certains commentaires cellule et la limite 6 V de l’ancienne API. La nouvelle
API de simulation utilise les grandeurs pack directement; l’ancienne API reste
à corriger séparément avant son usage avec un équipement réel.

## Zones de contribution proposées

| Priorité | Question | Ajout programme | Ajout dashboard | Preuve attendue |
|---|---|---|---|---|
| 1 — fondation | L’estimation SOC reste-t-elle fiable hors du cycle d’identification ? | Séparation calibration/test par cycles et cellules; comparaison comptage coulombique/EKF; erreurs et biais capteurs | Vérité de référence, estimation, erreur, intervalle du filtre, protocole et provenance | RMSE/MAE/max en points de SOC, erreur tension en mV, résultats sur cycles non utilisés pour identifier les paramètres |
| 2 — contribution principale | Peut-on repérer une cellule faible avant une alerte de seuil ? | Défauts injectables : capacité réduite, résistance augmentée, biais tension, défaut de refroidissement; diagnostic par résidus et persistance | Cellule suspecte, score, cause plausible, délai, historique des événements | Comparaison aux seuils simples : délai, faux positifs et défauts manqués sur scénarios et graines non utilisés pour régler les seuils |
| 3 — décision | L’équilibrage réduit-il le déséquilibre et augmente-t-il l’énergie exploitable ? | Équilibrage passif avec courant, puissance dissipée et limites thermiques; scénario identique sans/avec stratégie | Comparaison A/B, énergie Wh, delta SOC, pertes et température | Gain en Wh, pertes en Wh, température max et durée d’équilibrage; conservation d’énergie |
| 4 — usage | Quel est l’effet d’une mission à courant variable ? | Import CSV horodaté, validation unités, rejeu profils variables et freinage régénératif borné | Timeline mission, puissance, énergie, limites atteintes | Reproductibilité du profil et bilan énergétique; validation de la dynamique sur mesures indépendantes |
| 5 — extension | Comment adapter le fonctionnement en ambiance chaude ? | Paramètres dépendant de SOC/T et modèle de refroidissement calibré | Scénarios climatiques et comparaison de stratégies | Mesures ou dataset multi-température; ne pas extrapoler des paramètres à 25 °C comme vérité industrielle |

Les pistes 2 à 5 sont des propositions, **pas des fonctions déjà livrées**.
Leur nouveauté éventuelle exige une revue des publications et projets open source
sur la méthode retenue. Un détecteur de cellule faible ou un équilibrage passif
existe déjà dans l’industrie; la contribution doit porter sur un protocole,
une performance, une robustesse ou un outil ouvert clairement défini.

## Application recommandée

**Banc virtuel ouvert de diagnostic et d’évaluation BMS pour petits packs de
mobilité électrique et modules de stockage stationnaire.** Première démonstration
sur une topologie compatible avec les limites du prototype, sans prétendre
représenter une batterie automobile entière.

Exemple de question démontrable : « Sur un pack 12S×4P simulé, comment une baisse
de capacité d’une cellule affecte-t-elle l’énergie délivrée et à quel moment
un diagnostic par résidus la détecte-t-il, comparé à des seuils de tension ? »

Automobile : domaines pertinents, mais données, topologies, refroidissement,
communications et exigences supplémentaires nécessaires. Ferroviaire : pertinent
pour véhicules à batteries, hybrides et auxiliaires, mais un train électrique
alimenté par caténaire n’implique pas automatiquement une batterie de traction.

## Validation et publication réseaux

1. Réexécuter la validation ECM/EKF après correction du terme ohmique.
2. Utiliser des cycles NASA distincts pour l’identification et le test.
3. Ajouter un défaut reproductible et une référence simple.
4. Publier le protocole, les métriques, un scénario nominal et un cas d’échec.
5. Présenter une vidéo courte montrant le problème, le défaut, sa détection et
   l’utilité pratique; lien du code et limites affichées.

Titre de travail : « Battery Twin — banc virtuel ouvert pour analyser les
performances et diagnostiquer les déséquilibres d’un pack lithium-ion ».

Dataset officiel : https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/

Aucun résultat de gain, de détection ou de précision n’est inventé dans ce cadrage.
