# Battery Twin — IHM V2

Interface React/TypeScript/Vite, moteur Python conservé. Navigation, indicateurs,
carte de cellules interactive, quatre courbes, export CSV, configuration du pack,
charge/décharge, pause, réinitialisation et thèmes clair/sombre.

## Lancer

Depuis la racine du dépôt, terminal 1 :

```bash
pip install -r requirements.txt
python -m uvicorn digital_twin.api.dashboard:app --host 127.0.0.1 --port 8000
```

Terminal 2 :

```bash
cd web
npm ci
npm run dev -- --host 127.0.0.1
```

Ouvrir http://127.0.0.1:5173. La connexion au moteur est réelle : aucune donnée
fictive ne remplace une API indisponible. La simulation avance seulement lorsque
le navigateur envoie une commande. Fermer l’onglet arrête les commandes.

## Déploiement

Vercel : sélectionner `web` comme Root Directory, build `npm run build`, sortie
`dist`. Définir `VITE_API_URL` avec l’URL HTTPS du service Python.
Le serveur Python doit exécuter `digital_twin.api.dashboard:app` avec **un seul
worker**. Définir `DASHBOARD_ORIGINS` avec les origines exactes du frontend,
séparées par des virgules. L’API doit être accessible en HTTPS.

Ce backend garde les sessions en mémoire : UUID par simulation, expiration après
une heure d’inactivité, maximum 32 sessions, topologie maximale 24S×8P, maximum
120 secondes simulées par requête. Un redémarrage perd les sessions. Prévoir
rate limiting et authentification à la passerelle avant un accès public à grande
échelle; ne pas exposer l’ancienne API globale en parallèle.

Chaque session a son moteur, mais un verrou global sérialise les requêtes dans
cette première version. Aucune prétention au temps réel déterministe. Pour de
nombreux utilisateurs, déplacer les jobs vers des workers et un stockage partagé.

## Données et limites

- Les résultats proviennent du modèle de pack, pas de capteurs.
- Le SOC est estimé par EKF. L’incertitude est celle du filtre, pas une garantie
  d’exactitude expérimentale.
- Le SOH ne diminue pas artificiellement à chaque cycle : le modèle actuel ne
  simule pas la perte de capacité avec le vieillissement. Sa valeur initiale 100 %
  est une hypothèse, pas un certificat de santé.
- La RUL n’est pas calculée sans données de cycles suffisantes.
- Historique en mémoire limité aux 20 000 derniers points; réponse et CSV
  échantillonnés à environ 600 points. Le temps simulé est indiqué distinctement.
- Charge à la moitié du C-rate choisi, comme dans l’ancienne interface.
- Arrêt aux limites de charge simulée (5 % décharge / 95 % charge) ou alertes BMS.
- La carte est une vue logique des cellules, pas une géométrie mécanique.

## Corrections scientifiques

La correction de tension EKF inclut maintenant `R0 × I`, précédemment omise.
La covariance utilise la forme de Joseph pour préserver sa stabilité numérique.
Ces changements demandent de réexécuter les notebooks de validation avant de
réutiliser leurs anciens graphiques ou performances.

## Ressources UI étudiées

- https://github.com/satnaing/shadcn-admin (MIT)
- https://github.com/Kiranism/next-shadcn-dashboard-starter (MIT)
- https://github.com/tabler/tabler (MIT)
- https://github.com/tremorlabs/tremor

La V2 est une implémentation spécifique au domaine batterie, inspirée par les
structures sobres de Shadcn Admin; aucun code de template n’est recopié.
Lucide React fournit les icônes (licence ISC).

## Diagnostic EV sur télémétrie importée

Le nouveau menu Diagnostic est indépendant du simulateur NASA. Il permet
l’analyse CSV et l’export d’un rapport traçable. Voir [périmètre, données et
sources multi-marques](EV_DIAGNOSTIC.md). Le catalogue référence les sources;
il ne prétend pas qu’elles sont téléchargées ou que leurs véhicules sont calibrés.
