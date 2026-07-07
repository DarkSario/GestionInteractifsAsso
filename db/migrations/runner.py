"""Exécuteur de migrations SQLite.

Principe :
- Une table ``_migrations`` est créée en DB pour suivre les migrations appliquées.
- Les fichiers ``.sql`` du dossier ``migrations/`` sont lus par ordre numérique.
- Seules les migrations non encore appliquées sont exécutées.
"""

import sqlite3
from pathlib import Path

from utils.logger import get_logger

logger = get_logger(__name__)

MIGRATIONS_DIR = Path(__file__).parent


def run_migrations(conn: sqlite3.Connection) -> None:
    """Applique toutes les migrations SQL non encore exécutées.

    Args:
        conn: Connexion SQLite active (doit rester ouverte pendant l'opération).
    """
    _create_migrations_table(conn)

    already_applied = _get_applied_migrations(conn)
    sql_files = sorted(MIGRATIONS_DIR.glob("*.sql"))

    for sql_file in sql_files:
        name = sql_file.name
        if name in already_applied:
            logger.debug("Migration déjà appliquée : %s", name)
            continue

        logger.info("Application de la migration : %s", name)
        sql = sql_file.read_text(encoding="utf-8")
        try:
            conn.executescript(sql)
            conn.execute(
                "INSERT INTO _migrations (name) VALUES (?)",
                (name,),
            )
            conn.commit()
            logger.info("Migration appliquée avec succès : %s", name)
        except sqlite3.Error as exc:
            logger.error("Échec de la migration %s : %s", name, exc)
            conn.rollback()
            raise


def _create_migrations_table(conn: sqlite3.Connection) -> None:
    """Crée la table de suivi des migrations si elle n'existe pas."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS _migrations (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            name      TEXT NOT NULL UNIQUE,
            applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.commit()


def _get_applied_migrations(conn: sqlite3.Connection) -> set[str]:
    """Retourne l'ensemble des noms de migrations déjà appliquées."""
    rows = conn.execute("SELECT name FROM _migrations").fetchall()
    return {row[0] for row in rows}
