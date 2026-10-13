"""Exécuteur de migrations SQLite."""

import re
import sqlite3
from pathlib import Path

from db.connection import get_connection
from utils.logger import get_logger

logger = get_logger(__name__)

MIGRATIONS_DIR = Path(__file__).parent

_SQL_IDENTIFIER_PATTERN = r"`[^`]+`|\"[^\"]+\"|\[[^\]]+\]|\w+"
_ALTER_ADD_COLUMN_RE = re.compile(
    rf"ALTER\s+TABLE\s+(?P<table>{_SQL_IDENTIFIER_PATTERN})\s+ADD\s+COLUMN\s+"
    rf"(?P<column>{_SQL_IDENTIFIER_PATTERN})",
    re.IGNORECASE,
)


def split_sql_script(sql: str) -> list[str]:
    """Découpe un script SQL en instructions individuelles de manière robuste.

    Gère correctement les points-virgules présents :
    - dans des commentaires de ligne (-- ...) ou de bloc (/* ... */)
    - dans des chaînes littérales ('...') y compris avec échappement ('' ...)
    - dans des blocs BEGIN ... END de triggers (via sqlite3.complete_statement).
    """
    statements: list[str] = []
    current: list[str] = []
    in_single_quote = False
    in_double_quote = False
    in_line_comment = False
    in_block_comment = False
    i = 0
    n = len(sql)

    while i < n:
        c = sql[i]
        next_c = sql[i + 1] if i + 1 < n else ""

        if in_line_comment:
            current.append(c)
            if c == "\n":
                in_line_comment = False
        elif in_block_comment:
            current.append(c)
            if c == "*" and next_c == "/":
                current.append(next_c)
                i += 1
                in_block_comment = False
        elif in_single_quote:
            current.append(c)
            if c == "'":
                if next_c == "'":
                    current.append(next_c)
                    i += 1
                else:
                    in_single_quote = False
        elif in_double_quote:
            current.append(c)
            if c == '"':
                if next_c == '"':
                    current.append(next_c)
                    i += 1
                else:
                    in_double_quote = False
        else:
            if c == "-" and next_c == "-":
                current.append(c)
                current.append(next_c)
                i += 1
                in_line_comment = True
            elif c == "/" and next_c == "*":
                current.append(c)
                current.append(next_c)
                i += 1
                in_block_comment = True
            elif c == "'":
                current.append(c)
                in_single_quote = True
            elif c == '"':
                current.append(c)
                in_double_quote = True
            elif c == ";":
                current.append(c)
                candidate = "".join(current)
                if sqlite3.complete_statement(candidate):
                    trimmed = candidate.strip()
                    if trimmed and trimmed != ";":
                        statements.append(trimmed)
                    current = []
            else:
                current.append(c)
        i += 1

    remainder = "".join(current).strip()
    if remainder and remainder != ";":
        statements.append(remainder)

    return statements


def run_migrations() -> None:
    """Applique toutes les migrations SQL non encore exécutées."""
    logger.info("Démarrage de run_migrations()")
    try:
        conn = get_connection()
    except Exception:
        logger.exception("Impossible d'ouvrir la connexion DB pour les migrations")
        raise
    try:
        _create_migrations_table(conn)

        already_applied = _get_applied_migrations(conn)
        sql_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
        logger.info(
            "Migrations détectées: %s fichier(s), %s déjà appliquée(s)",
            len(sql_files),
            len(already_applied),
        )

        for sql_file in sql_files:
            migration_name = sql_file.name
            if migration_name in already_applied:
                logger.debug("Migration déjà appliquée : %s", migration_name)
                continue

            logger.info("Application de la migration : %s", migration_name)
            try:
                if not conn.in_transaction:
                    conn.execute("BEGIN IMMEDIATE")
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
                if conn.in_transaction:
                    conn.rollback()
                logger.exception("Échec de la migration : %s", migration_name)
                raise
        logger.info("Fin de run_migrations() sans erreur")
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
    Chaque instruction est exécutée de façon transactionnelle via ``conn.execute(stmt)``.
    """
    statements = split_sql_script(sql)

    for stmt in statements:
        if match := _ALTER_ADD_COLUMN_RE.search(stmt):
            table = match.group('table').strip('`"[]')
            column = match.group('column').strip('`"[]')
            colonnes = {
                row['name']
                for row in conn.execute(f'PRAGMA table_info("{table}")').fetchall()
            }
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
            conn.execute(stmt)

