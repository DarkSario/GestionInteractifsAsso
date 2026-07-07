"""Tests du système d'initialisation et de migrations SQLite."""

from db.connection import get_connection, set_db_file
from db.migrations.runner import run_migrations


def test_run_migrations_creates_expected_tables(tmp_db) -> None:
    set_db_file(str(tmp_db))
    run_migrations()

    conn = get_connection()
    try:
        tables = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        config_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(config)").fetchall()
        }
        migration_rows = conn.execute(
            "SELECT nom FROM _migrations ORDER BY id"
        ).fetchall()
    finally:
        conn.close()
        set_db_file("")

    assert {
        "_migrations",
        "config",
        "membres",
        "evenements",
        "mouvements_stock",
        "retrocessions_ecoles",
    }.issubset(tables)
    assert {
        "nom_asso",
        "exercice",
        "date_debut",
        "date_fin",
        "solde_ouverture",
    }.issubset(config_columns)
    assert [row["nom"] for row in migration_rows] == [
        "0001_init.sql",
        "0002_membres_remboursements.sql",
    ]


def test_run_migrations_is_idempotent(tmp_db) -> None:
    set_db_file(str(tmp_db))
    run_migrations()
    run_migrations()

    conn = get_connection()
    try:
        count = conn.execute("SELECT COUNT(*) AS total FROM _migrations").fetchone()[
            "total"
        ]
    finally:
        conn.close()
        set_db_file("")

    assert count == 2
