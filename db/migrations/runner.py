"""Exécuteur de migrations SQLite."""

from pathlib import Path

from db.connection import get_connection
from utils.logger import get_logger

logger = get_logger(__name__)

MIGRATIONS_DIR = Path(__file__).parent


def run_migrations() -> None:
    """Applique toutes les migrations SQL non encore exécutées."""
    conn = get_connection()
    try:
        _create_migrations_table(conn)

        already_applied = _get_applied_migrations(conn)
        sql_files = sorted(MIGRATIONS_DIR.glob("*.sql"))

        for sql_file in sql_files:
            migration_name = sql_file.name
            if migration_name in already_applied:
                logger.debug("Migration déjà appliquée : %s", migration_name)
                continue

            logger.info("Application de la migration : %s", migration_name)
            try:
                conn.executescript(sql_file.read_text(encoding="utf-8"))
                conn.execute(
                    """
                    INSERT INTO _migrations (nom)
                    VALUES (?)
                    """,
                    (migration_name,),
                )
                conn.commit()
                logger.info("Migration appliquée avec succès : %s", migration_name)
            except Exception:
                conn.rollback()
                logger.exception("Échec de la migration : %s", migration_name)
                raise
    finally:
        conn.close()


def _create_migrations_table(conn) -> None:
    """Crée la table de suivi des migrations si nécessaire."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS _migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL UNIQUE,
            appliquee_le TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.commit()


def _get_applied_migrations(conn) -> set[str]:
    """Retourne l'ensemble des migrations déjà appliquées."""
    rows = conn.execute("SELECT nom FROM _migrations").fetchall()
    return {row["nom"] for row in rows}
