# eat healthy

[![CI](https://github.com/pamm-bot/eat-healthy/actions/workflows/ci.yml/badge.svg)](https://github.com/pamm-bot/eat-healthy/actions/workflows/ci.yml)

[English](README.md) · **Français**

On enregistre ce qu'on mange et on obtient une image simple de *comment* on a
mangé sur la semaine — pas d'objectifs caloriques. Quelle part de la semaine
était ultra-transformée, quelle variété de végétaux, et comment les fibres, le
sucre et le sel se comparent aux repères de santé publique.

**Démo en ligne :** _bientôt_ — connexion avec `demo` / `demo12345` pour deux
semaines déjà remplies.

## Captures d'écran

| Tableau de bord hebdo | Enregistrer un aliment |
|---|---|
| [![Tableau de bord : part d'ultra-transformés, variété végétale, graphique Nutri-Score, fibres/sucre/sel vs. repères](docs/screenshots/dashboard.png)](docs/screenshots/dashboard.png) | [![Recherche d'un aliment, avec NOVA et Nutri-Score, et ajout d'une portion](docs/screenshots/log.png)](docs/screenshots/log.png) |

## Ce que ça fait

1. **Enregistrer un aliment** — recherche par nom ou saisie d'un code-barres.
   Les produits, avec leur groupe de transformation NOVA et leur Nutri-Score,
   viennent d'[OpenFoodFacts](https://world.openfoodfacts.org/).
2. **Ajouter sa portion** — en grammes et quel repas. Quelques secondes par
   aliment.
3. **Lire sa semaine** — un tableau de bord qui transforme le journal en :
   - **part d'ultra-transformés** — % de tes calories enregistrées venant du
     groupe NOVA 4
   - **variété végétale** — combien de végétaux entiers différents tu as mangés,
     face à un objectif de 30 par semaine
   - distribution **Nutri-Score** de ce que tu as mangé
   - **fibres / sucres / sel** par jour vs. repères OMS / EFSA

C'est descriptif volontairement — pas d'objectif calorique, pas de poids, pas de
« mange moins ».

## Stack

- Django 6.1, PostgreSQL — templates rendus côté serveur, **htmx** pour la
  recherche et le journal sans rechargement complet
- Authentification par session intégrée à Django
- Bootstrap 5, Chart.js (pour le graphique Nutri-Score)
- WhiteNoise, gunicorn, déployé sur Heroku
- pytest, black, flake8, bandit ; CI sur GitHub Actions

## Choix techniques

- **Rendu serveur, pas une API.** Mon autre projet Django est une API DRF avec
  un client JS séparé ; celui-ci est l'autre forme courante — des templates
  Django avec htmx pour l'interactif. Moins de pièces mobiles pour une appli qui
  est surtout des formulaires et un tableau de bord.
- **Le rapport hebdo est de la logique pure.** Transformer un tas de portions
  enregistrées en « à quel point transformé, à quel point varié, combien de
  fibres / sucre / sel » est la seule vraie logique métier, donc elle vit dans
  [`tracker/reports.py`](tracker/reports.py) sous forme de fonctions sans
  requêtes ni écritures, testées unitairement sur des entrées synthétiques.
- **Les données OpenFoodFacts sont mises en cache localement.** L'API est
  désordonnée et limitée en débit, donc au premier enregistrement d'un produit
  il est normalisé dans une ligne `Food` et réutilisé ensuite — le client
  ([`tracker/openfoodfacts.py`](tracker/openfoodfacts.py)) renvoie des dicts
  simples, jamais des instances de modèle, et chaque appel a un timeout et
  avale les erreurs réseau au lieu de faire planter une vue.
- **Les moyennes portent sur les jours enregistrés**, pas sur la semaine
  calendaire, et le tableau de bord le dit — un jour vide ne doit pas tirer les
  fibres quotidiennes à zéro.
- **Honnête sur les données.** OpenFoodFacts donne les sucres *totaux*, pas les
  sucres ajoutés, et ses tags de catégories sont inégaux, donc la
  reconnaissance de « variété végétale » est au mieux. L'interface l'indique
  plutôt que de faire semblant d'être précise.
- **Pas un conseil médical.** Les valeurs de référence sont citées (OMS, EFSA)
  et le cadrage reste sur la *description*, ce qui l'éloigne aussi du terrain
  des troubles alimentaires.

## Installation

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env   # puis renseigner SECRET_KEY, DATABASE_URL
python manage.py migrate
python manage.py seed_demo   # optionnel : le compte de démo + deux semaines d'entrées
python manage.py runserver
```

`seed_demo` crée `demo` / `demo12345` avec deux semaines d'entrées codées en
dur (aucun réseau requis), pour que le tableau de bord ait quelque chose à
montrer. La commande peut être relancée sans risque.

## Tests

```bash
pytest
```

S'exécutent à chaque push et pull request via GitHub Actions, avec `black
--check`, `flake8` et `bandit`. Les tests couvrent les modèles, le client
OpenFoodFacts (contre du JSON figé), les vues, et le rapport hebdo en détail.

## Feuille de route

- **Phase 2 — planificateur de repas.** À partir des jours où tu cuisines, de
  tes règles alimentaires et d'un budget temps, générer une semaine de repas
  équilibrés plus une liste de courses consolidée — un problème de satisfaction
  de contraintes sur les mêmes données collectées ici.
- Scan de code-barres par la caméra (aujourd'hui un champ de saisie).
- Un résumé hebdomadaire par e-mail.
