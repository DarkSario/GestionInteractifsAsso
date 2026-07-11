# Gestion Interactifs Asso

Logiciel de gestion pour l'association **Les Interactifs des Écoles**.

---

## Description

Application desktop en Python permettant de gérer :
- Les **adhérents** et cotisations
- La **trésorerie** (recettes, dépenses, dépôts, journal)
- Les **événements** et modules de vente associés
- La **buvette** (articles, achats, inventaires, recettes)
- Le **stock** général
- Les **exports** PDF et Excel
- Le **tableau de bord** financier

---

## Prérequis

- **Python 3.10+**
- **tkinter** (inclus sur Windows ; sur Linux : `sudo apt install python3-tk`)
- Les dépendances listées dans `requirements.txt`

---

## Installation

```bash
# Cloner le dépôt
git clone https://github.com/DarkSario/GestionInteractifsAsso.git
cd GestionInteractifsAsso

# Créer et activer un environnement virtuel
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
# ou
.venv\Scripts\activate           # Windows

# Installer les dépendances
pip install -r requirements.txt
```

---

## Lancement

```bash
python run_app.py
```

---

## Structure du projet

```
GestionInteractifsAsso/
│
├── main.py                  # Point d'entrée minimal
├── run_app.py               # Wrapper lancement + logging
├── requirements.txt         # Dépendances runtime et dev
│
├── config/
│   ├── settings.py          # Constantes : version, chemins, nom appli
│   └── theme.json           # Thème par défaut (dark + couleurs bleues)
│
├── core/                    # Logique métier pure (pas de tkinter)
│
├── db/                      # Accès données uniquement
│   ├── connection.py        # Gestion connexion SQLite
│   ├── schema.py            # Définition du schéma complet
│   └── migrations/          # Scripts SQL numérotés
│       ├── runner.py        # Applique les migrations manquantes
│       └── 0001_init.sql    # Migration initiale
│
├── ui/                      # Interface graphique (CustomTkinter)
│   ├── app.py               # Fenêtre principale et menu
│   ├── theme.py             # Chargement et exposition du thème
│   ├── components/          # Widgets réutilisables
│   └── modules/             # Un sous-dossier par module UI
│       ├── administration/  # Éditeur de thème, sauvegarde, etc.
│       ├── membres/
│       ├── tresorerie/
│       ├── evenements/
│       ├── buvette/
│       ├── stock/
│       ├── exports/
│       └── dashboard/
│
├── utils/                   # Helpers transverses
│   ├── logger.py            # Logger centralisé
│   ├── error_handler.py     # Décorateur handle_errors
│   ├── backup.py            # Sauvegarde / restauration DB
│   ├── date_helpers.py      # Helpers dates
│   └── validation.py        # Validation de saisies
│
└── tests/                   # Tests unitaires (pytest)
```

---

## Ajouter un nouveau module

L'ajout d'un module se fait en **3 étapes** :

1. **`db/models/mon_module.py`** — fonctions CRUD (sans UI)
2. **`ui/modules/mon_module/`** — dossier avec `__init__.py` et la fenêtre UI
3. **`ui/app.py`** — ajouter une entrée dans le menu et/ou un bouton sur la page d'accueil

Le reste (DB, utils, thème) n'est pas modifié.

---

## Personnalisation du thème

Depuis l'application : **Administration → Apparence**

Paramètres disponibles :
- Mode Clair / Sombre
- Couleur principale et secondaire (color picker)
- Police et taille de police
- Logo de l'association

Les préférences sont sauvegardées dans `config/theme.json`.

---

## Licence

Usage interne — Association Les Interactifs des Écoles.
