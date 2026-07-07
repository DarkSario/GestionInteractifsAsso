"""Gestion de la connexion SQLite."""

import sqlite3

from utils.logger import get_logger

logger = get_logger(__name__)

_db_file: str | None = None


def set_db_file(path: str) -> None:
    """Définit le fichier de base de données actif."""
    global _db_file
    _db_file = str(path)
    logger.info("Fichier DB actif : %s", _db_file)


def get_db_file() -> str | None:
    """Retourne le chemin du fichier de base de données actif."""
    return _db_file


def get_connection() -> sqlite3.Connection:
    """Retourne une connexion SQLite configurée pour l'application."""
    if not _db_file:
        raise RuntimeError(
            "Aucun fichier de base de données défini. Appelez set_db_file() d'abord."
        )

    conn = sqlite3.connect(
        _db_file,
        timeout=10,
        detect_types=sqlite3.PARSE_DECLTYPES,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    conn.execute("PRAGMA foreign_keys=ON;")
    logger.debug("Connexion ouverte sur %s", _db_file)
    return conn
