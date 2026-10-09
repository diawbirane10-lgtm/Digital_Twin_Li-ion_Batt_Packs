# Battery Twin — diagnostic multi-marques sur fichiers

## Première version fonctionnelle

Le nouveau menu **Diagnostic** analyse une télémétrie sans appliquer les paramètres
NASA B0005 aux batteries Tesla, BMW ou autres. Il est indépendant du simulateur.

Fonctions : import CSV, provenance, nature mesurée/synthétique, convention du
courant, validation des données, intégration Ah/Wh, contrôle de température,
dispersion des tensions cellule, rapport JSON avec SHA-256, preuves et limites.

Les seuils sont choisis par l’analyste. Ce sont des seuils d’analyse, pas des
valeurs constructeur. Une dispersion de tensions est un signal à examiner,
ni une preuve de dégradation ni une localisation du défaut.

Le rapport refuse de produire un SOH, une RUL ou une cellule faible identifiée
avec des preuves insuffisantes. Il n’envoie aucune commande OBD/CAN au véhicule.
L’exemple intégré est explicitement SYNTHÉTIQUE et ne représente aucune marque.

## Format CSV

Virgules comme séparateur; point comme séparateur décimal; temps strictement
croissant en secondes. Courant en ampères; tension totale du pack en volts.

Obligatoires : `time_s,pack_voltage_v,pack_current_a`.
Optionnels : `temperature_c,soc_pct,cell_min_v,cell_max_v`.
Les tensions cellule min/max sont fournies ensemble. Le SOC est exprimé en %.
Maximum 5 Mo et 20 000 lignes. Aucun fichier n’est persisté par l’API.

L’import exige une conversion préalable vers ce schéma : **pas encore de lecteur
natif des formats Tesla CAN, BMW IEEE, MAT/HDF5 ou EVBattery**. La normalisation
par dataset doit être créée après inspection de ses fichiers et métadonnées.

## Sources identifiées, à ne pas confondre avec une compatibilité véhicule

| Source | Niveau réel | Utilité | Statut |
|---|---|---|---|
| McMaster, Tesla Model 3 21700 4,9 Ah, DOI 10.5683/SP3/ZVTR4B | Cellule extraite / laboratoire | Comparaison SOC multi-température et profils dynamiques | Page institutionnelle vérifiée; accès Borealis refusé dans cet environnement; archive non téléchargée |
| TUM, DOI 10.14459/2024mp1735471 | Véhicule Tesla Model 3 | Télémétrie de conduite et pack | Notice européenne identifiée; page TUM inaccessible durant la recherche; fichiers non inspectés |
| BMW i3, Battery and Heating Data in Real Driving Cycles | Véhicule BMW i3 60 Ah | Analyse de missions et charge thermique | Source IEEE identifiée, accès primaire bloqué; licence et schéma à vérifier |
| EVBattery, DOI 10.6084/m9.figshare.23301881 | Recharge de centaines de véhicules, trois constructeurs | Validation santé/capacité, données terrain | Notice auteurs Figshare vérifiée; CC BY 4.0; archive 1,31 Go non téléchargée |
| Gustave Eiffel, DOI 10.57745/ZXBSRF | Modules BMW i3 / Samsung SDI 94 Ah de seconde vie | Impédance, capacité et caractérisation | Notice identifiée; accès primaire non abouti; conditions spécifiques à vérifier |

Sources :
- https://battery.mcmaster.ca/research/datasets-and-algorithms/
- https://data.europa.eu/data/datasets/10-14459-2024mp1735471?locale=en
- https://ieee-dataport.org/open-access/battery-and-heating-data-real-driving-cycles
- https://figshare.com/articles/dataset/23301881
- https://entrepot.recherche.data.gouv.fr/dataset.xhtml?persistentId=doi:10.57745/ZXBSRF

Ne pas identifier les constructeurs anonymisés d’EVBattery comme BYD, NIO ou
XPeng sans preuve. Une source multi-constructeurs ne démontre pas la prise en
charge d’une marque chinoise nommée. La chimie LFP/NMC/NCA doit être documentée
pour chaque batterie, sans être déduite de la seule marque.

## Contribution industrielle proposée

Un **diagnostic traçable et conscient de la qualité des données** : chaque
constat expose la mesure, les unités, le seuil et la limite d’interprétation.
L’interface indique également les fonctions impossibles avec les signaux reçus.
Ce positionnement est une proposition de contribution, pas une preuve de
nouveauté : des solutions industrielles de diagnostic batterie existent déjà.

L’évaluation doit comparer la méthode à une référence simple, et publier :
- taux de faux positifs et de défauts manqués;
- délai de détection;
- robustesse aux températures, SOC et profils de charge;
- erreurs / biais de capteur, données manquantes et changement de véhicule;
- séparation des véhicules d’apprentissage, réglage et test.

## Prochaine tranche technique

1. Récupérer un extrait autorisé et inspecter les fichiers et licences de chaque
   source; ajouter manifeste, checksum et adaptateur testé.
2. Commencer par McMaster Tesla pour le SOC et BMW/TUM pour les missions; ne pas
   mélanger leurs niveaux cellule et pack.
3. Construire une référence de santé sur les tests de capacité disponibles;
   comparer SOH énergétique et capacitif sous protocole défini.
4. Ajouter diagnostic de défaut à partir des résidus normalisés, avec persistance,
   labels indépendants et jeu de test par véhicule.
5. Comparer les résultats par chimie et domaine d’utilisation; publier un tableau
   des domaines calibrés et non validés.

## Usage concret

Pré-analyse de données de batteries EV pour études, inspection d’un historique
avant seconde vie, comparaison de missions et préparation de tests complémentaires.
Ce prototype n’est pas un certificat de santé pour achat/revente et ne remplace
pas une qualification de diagnostic sur véhicule. L’accès à des données publiques
ne confère pas une homologation ou une relation avec le constructeur.

API : `GET /diagnostics/sources`, `POST /diagnostics/analyse`.
