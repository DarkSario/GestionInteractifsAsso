"""Constantes globales de l'application."""

from pathlib import Path

# Informations sur l'application
APP_NAME = "Gestion Interactifs Asso"
APP_VERSION = "0.1.0"
ASSOCIATION_NAME = "Les Interactifs des Écoles"

# Chemins relatifs à la racine du projet
ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT_DIR / "config"
LOGS_DIR = ROOT_DIR / "logs"
DB_DIR = ROOT_DIR

# Nom du fichier de base de données
DB_FILENAME = "association.db"
DB_PATH = DB_DIR / DB_FILENAME

# Fichier de thème
THEME_FILE = CONFIG_DIR / "theme.json"

# Migrations
MIGRATIONS_DIR = ROOT_DIR / "db" / "migrations"
