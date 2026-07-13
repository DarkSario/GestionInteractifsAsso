"""Exécuteur de migrations SQLite."""

import re
from pathlib import Path

from db.connection import get_connection
from utils.logger import get_logger

logger = get_logger(__name__)

MIGRATIONS_DIR = Path(__file__).parent

_ALTER_ADD_COLUMN_RE = re.compile(
    r"ALTER\s+TABLE\s+(?P<table>\S+)\s+ADD\s+COLUMN\s+(?P<column>\S+)",
    re.IGNORECASE,
)


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
                _execute_migration(conn, sql_file.read_text(encoding="utf-8"))
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


def _execute_migration(conn, sql: str) -> None:
    """Exécute un script de migration en gérant les cas SQLite particuliers.

    Les instructions ``ALTER TABLE ... ADD COLUMN`` dont la colonne existe déjà
    sont ignorées silencieusement (SQLite ne supporte pas ``IF NOT EXISTS``).
    Les autres instructions sont exécutées via ``executescript``.
    """
    statements = [s.strip() for s in sql.split(";") if s.strip()]

    for stmt in statements:
        if match := _ALTER_ADD_COLUMN_RE.search(stmt):
            table = match.group('table').strip('`\"')
            column = match.group('column').strip('`\"')
            colonnes = {row['name'] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
            if column in colonnes:
                logger.debug("Colonne déjà existante détectée via pragma_table_info : %s.%s", table, column)
                continue
            try:
                conn.execute(stmt)
            except Exception as exc:
                if "duplicate column name" in str(exc).lower():
                    logger.debug("Colonne déjà existante, ignoré : %s", stmt[:80])
                else:
                    raise
        else:
            conn.executescript(stmt + ";")
