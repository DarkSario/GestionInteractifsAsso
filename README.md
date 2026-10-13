# 🎪 Gestion Interactifs Asso

Application de gestion complète pour associations, développée avec Python et CustomTkinter.

## Fonctionnalités

- 🏠 **Tableau de bord** avec indicateurs clés, alertes de trésorerie et accès direct aux fiches événements
- 🎪 **Gestion des événements** : billetterie, dépenses, gestion des bénévoles, tombolas, caisses avec ventilation espèces/CB/chèques et activation modulaire des onglets
- 💰 **Trésorerie** : comptes bancaires, journal des opérations, remises de chèques/espèces, subventions
- 💸 **Remboursements & 💝 Dons** : suivi des frais avancés par les membres et gestion des dons
- 📦 **Stock & Buvette** : catalogue d'articles, entrées de stock, alertes de péremption et inventaires
- 👥 **Adhérents & Cotisations** : gestion des membres, suivi annuel des cotisations et adhésions rapides
- 🏛️ **Configuration de l'association** : personnalisation du nom, de l'exercice comptable, des coordonnées et du solde d'ouverture
- 📄 **Exports & Bilan AG** : bilans financiers, synthèses PDF et exports CSV
- ⚙️ **Paramètres & Sauvegardes** : sauvegardes automatiques de la base SQLite et restauration intégrée

## Prérequis

- Python 3.10 ou supérieur
- tkinter (inclus sur Windows ; sur Linux : `sudo apt install python3-tk`)

## Installation

1. Cloner ou télécharger le projet
2. Installer les dépendances :
   ```bash
   pip install -r requirements.txt
   ```
3. Lancer l'application :
   ```bash
   python run_app.py
   ```

## Développement & Tests

1. Installer les dépendances de développement :
   ```bash
   pip install -r requirements-dev.txt
   ```
2. Lancer les tests unitaires :
   ```bash
   pytest
   ```
3. Vérifier le code avec ruff :
   ```bash
   ruff check --select F,E9 .
   ```

### Migrations de la base de données

Les migrations SQLite sont situées dans `db/migrations/` sous forme de fichiers numérotés (`0001_init.sql`, `0002_...sql`). Elles sont exécutées automatiquement au démarrage via `db.migrations.runner.run_migrations()` de manière ordonnée et atomique (avec support des déclencheurs et transactions sécurisées).

## Premier démarrage

Au premier lancement, l'application vous demande de créer ou sélectionner
une base de données. Consultez le Manuel d'utilisation (`docs/MANUEL_UTILISATION.md`)
pour une prise en main complète.

## Documentation

📖 Manuel d'utilisation complet : [docs/MANUEL_UTILISATION.md](docs/MANUEL_UTILISATION.md)
(également accessible dans l'application via le menu **Aide → 📖 Manuel d'utilisation**).

Les informations de l'association (nom, exercice, solde d'ouverture) se modifient via
**Administration → 🏛️ Informations de l'association**.
Les modules sont accessibles depuis **Modules** ; le tableau de bord propose aussi des accès directs
aux événements, à la trésorerie, à la buvette, aux adhérents, aux dons, à la configuration de l'association et au manuel.

## Licence

Usage interne — Association Interactifs
