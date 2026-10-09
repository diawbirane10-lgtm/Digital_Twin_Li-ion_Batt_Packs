# Boucle de vérification et résultats

Méthode issue de la lecture de [ECC verification-loop](https://github.com/affaan-m/ECC/blob/main/skills/verification-loop/SKILL.md), licence MIT : construire, vérifier les types, tester, inspecter les erreurs et le diff, corriger, rejouer. Aucun hook, serveur MCP, système de mémoire ou script ECC installé automatiquement. Sa méthode de vérification est adaptée au projet ; les métriques de fiabilité d'agents ne mesurent pas la précision d'une batterie.

## Benchmark reproductible sur mesures

`python -m validation.benchmark` produit `validation/nasa_results.json` : empreinte du parquet et résultats agrégés par cellule. Installer les dépendances requirements.txt. Adaptateur explicite dans diagnostics/nasa.py : une cellule de laboratoire 1S1P, convention courant négatif en décharge, aucune mise à l'échelle en pack fictif.

636 cycles de décharge / 4 cellules / 185 721 mesures. Écart absolu moyen charge intégrée versus label NASA : 0,01303 Ah ; maximum : 0,02802 Ah. Écart maximal versus référence NumPy (positivité aux points de mesure) : 0,0000621 Ah ; la méthode du diagnostic sépare les changements de signe entre points, ce qui explique un petit écart avec cette référence.

Critères : résultats finis et non négatifs ; invariance charge/décharge au changement de signe ; bruit courant gaussien sigma 0,2 A sur profil 10 A/400 V/1 h, erreur énergie < 0,2 % sur 20 graines ; lacunes signalées ; horodatages et CSV incohérents rejetés. Les résultats détaillés mesurent une cohérence numérique, pas une précision instrumentale indépendante. Aucun SOC vrai ni défaut annoté n'est disponible dans ce benchmark. Les labels de capacité ne justifient pas un diagnostic constructeur.

## Vérifications

37 tests Python réussis. Build TypeScript/Vite réussi. Parcours navigateur diagnostic, détection de dispersion synthétique, export JSON, rejet CSV invalide, desktop et mobile sans débordement ni erreur JavaScript.
Pas de lint ni couverture complète configurés : ces contrôles ne sont pas déclarés réussis. La relecture du diff et `git diff --check` complètent les contrôles actuels.

## Prochaine barrière scientifique

Importer des profils dynamiques de cellules automobiles avec licence et provenance, évaluer les paramètres ECM hors calibration, traiter les biais de capteur et les données hors domaine. Séparer cellules/calibration et cellules/test. Évaluer SOC uniquement avec une référence indépendante documentée. Une validation de terrain et des défauts annotés restent nécessaires avant de promettre une localisation de défaut ou un SOH multimarque fiable.
