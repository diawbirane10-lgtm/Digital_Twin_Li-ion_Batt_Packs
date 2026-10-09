# Philosophie IHM — diagnostic batterie

Référence : ISA-101, séries et périmètre décrits par ISA : https://www.isa.org/standards-and-publications/isa-standards/isa-101-standards.
Application de principes de conception ; aucune conformité certifiée ni qualification d'un poste de conduite industriel. Le texte normatif complet n'a pas été audité.

## Hiérarchie et information

Vue d'ensemble : contexte du pack, grandeurs essentielles, état BMS simulé. Cellules : détail local et identification S/P. Analyse : tendances horodatées. Simulation : configuration et commandes. Diagnostic : import de mesures et preuves, distinct du simulateur.
Bandeau opérateur visible sur chaque page : mode, absence de données, erreur de connexion, arrêt ou alerte. Les dernières valeurs ne deviennent pas des mesures valides lorsqu'une connexion échoue.
Chaque grandeur porte une unité. Les hypothèses SOH et les incertitudes estimées restent explicites. Les données de laboratoire ne sont pas présentées comme un pack automobile.

## Couleurs et anomalies

Surfaces, cellules normales et tendances en palette neutre. Ambre réservé aux dépassements et états d'attention, associé à un texte/symbole. La sélection et les commandes utilisent une bordure/un état visuel distinct. Aucune animation d'alarme ni acquittement fictif : l'application ne constitue pas un système de gestion d'alarmes ISA-18.2.
Les limites 55 °C / 4,25 V / 2,45 V sont les paramètres de simulation existants, pas des limites universelles de sécurité ou constructeur. Les seuils du diagnostic sont choisis par l'analyste.

## Validation et travaux restants

Contrôles automatisés : compilation TypeScript, navigation/import/export, erreur d'import, absence de débordement mobile et erreurs JavaScript. Relecture visuelle desktop/mobile.
À compléter avec des utilisateurs : temps d'identification d'une anomalie, compréhension simulation/mesure, accessibilité clavier et contraste intégral des thèmes, scénarios d'alarmes multiples, philosophie d'alarme rationalisée avant tout usage opérationnel.
