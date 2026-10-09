# Streamlit — application principale

L'application principale est `app.py`, qui conserve son rôle d'entrée Streamlit Cloud et charge `visualization/dashboard/app.py`. La version React/Vercel reste disponible à https://battery-twin-birane.vercel.app.

## Interface et moteur

Navigation : Vue d'ensemble, Cellules, Analyse, Simulation et Diagnostic. Palette claire, panneaux/champs/boutons carrés, bandeau permanent distinguant valeurs calculées et mesures importées. Carte de cellules neutre, avertissements textuels, inspection locale, courbes Plotly et exports CSV/JSON.
Le moteur de simulation et le diagnostic sont partagés avec la version web. Streamlit conserve le checkpoint et l'historique dans sa session utilisateur ; aucune API distante nécessaire. La simulation automatique utilise un fragment rafraîchi toutes les 0,5 s. Le mode Charge/Décharge respecte les limites et ne fabrique ni cycles de vieillissement, ni capacité mesurée, ni prédiction Arrhenius. L'ancien affichage trompeur de « dégradation réelle » est retiré.

## Installation

Installer requirements.txt (Streamlit >= 1.50), puis `python -m streamlit run app.py`. Le thème et la limite de téléchargement sont dans `.streamlit/config.toml`. Pour l'application Cloud existante : garder le dépôt et la branche main, avec app.py comme entrée. Une application connectée à main doit récupérer le nouveau code ; vérifier son redémarrage dans Manage app si nécessaire.

## Vérification

41 tests passent, incluant AppTest sur l'entrée Cloud : affichage initial, avancement 10 s, inspection cellule, réinitialisation, diagnostic synthétique et rejet de données invalides. La validation scientifique reste celle du moteur commun et du benchmark NASA ; les tests IHM ne démontrent pas une précision constructeur.

L'adresse exacte et l'état de reconstruction de l'application Streamlit Cloud ne sont pas connus de cette session. Le dépôt mis à jour ne constitue pas à lui seul une preuve que l'application hébergée a été redéployée.
