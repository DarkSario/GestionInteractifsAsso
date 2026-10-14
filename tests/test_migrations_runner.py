"""Tests du système d'initialisation et de migrations SQLite."""

from pathlib import Path
import sqlite3
import pytest

from db.connection import get_connection, set_db_file
from db.migrations.runner import (
    run_migrations,
    split_sql_script,
    _execute_migration,
)

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "db" / "migrations"


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
        evenement_caisses_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(evenement_caisses)").fetchall()
        }
        evenement_caisse_lignes_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(evenement_caisse_lignes)").fetchall()
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
        "evenement_tarifs",
        "evenement_ventes",
        "evenement_vente_lignes",
        "evenement_billets",
        "evenement_benevoles",
        "tombola_lots",
        "tombola_carnets",
        "evenement_stands",
        "evenement_stands_attente",
        "tableaux_perso",
        "tableaux_colonnes",
        "tableaux_lignes",
        "tableaux_cellules",
        "tableaux_templates",
        "parametres",
        "mouvements_stock",
        "evenement_caisses",
        "evenement_caisse_lignes",
        "caisse_designations",
        "retrocessions_ecoles",
        "unites",
        "fournisseurs",
        "articles_buvette",
        "inventaires_buvette",
        "approvisionnements_buvette",
        "caisses_buvette",
        "recettes_buvette",
        "comptes_bancaires",
        "tresorerie_categories",
        "tresorerie_operations",
        "remises_cheques",
        "remises_cheques_detail",
        "subventions",
        "exercices",
        "exercices_log",
        "polices_pdf",
        "sauvegardes",
        "stock_tags",
        "stock_article_tags",
        "stock_lots",
        "stock_lot_tags",
        "stock_inventaires",
        "stock_inventaire_lignes",
        "buvette_couts_evenement",
        "evenement_budget",
        "dons",
    }.issubset(tables)
    assert {
        "nom_asso",
        "exercice",
        "date_debut",
        "date_fin",
        "solde_ouverture",
    }.issubset(config_columns)
    assert {"nom", "nom_caisse", "statut", "created_at", "updated_at"}.issubset(
        evenement_caisses_columns
    )
    assert {"designation_id", "designation_text"}.issubset(
        evenement_caisse_lignes_columns
    )
    expected_migrations = sorted(
        p.name
        for p in MIGRATIONS_DIR.glob("*.sql")
    )
    assert [row["nom"] for row in migration_rows] == expected_migrations


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

    expected_count = len(list(MIGRATIONS_DIR.glob("*.sql")))
    assert count == expected_count


def test_run_migrations_reconstruit_tables_caisses_si_absentes(tmp_db) -> None:
    set_db_file(str(tmp_db))
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS _migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT NOT NULL UNIQUE,
                appliquee_le TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS evenements (
                id INTEGER PRIMARY KEY AUTOINCREMENT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tresorerie_operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                statut TEXT,
                source_module TEXT,
                source_id INTEGER
            )
            """
        )
        legacy_migrations = sorted(
            migration.name
            for migration in MIGRATIONS_DIR.glob("*.sql")
            if migration.name < "0021_evenement_caisses_detail.sql"
        )
        conn.executemany(
            "INSERT INTO _migrations (nom) VALUES (?)",
            [(name,) for name in legacy_migrations],
        )
        conn.commit()
    finally:
        conn.close()

    run_migrations()

    conn = get_connection()
    try:
        tables = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        cols_caisses = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(evenement_caisses)").fetchall()
        }
        cols_lignes = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(evenement_caisse_lignes)").fetchall()
        }
        migrations = {
            row["nom"]
            for row in conn.execute("SELECT nom FROM _migrations").fetchall()
        }
    finally:
        conn.close()
        set_db_file("")

    assert {"evenement_caisses", "evenement_caisse_lignes", "caisse_designations"}.issubset(
        tables
    )
    assert {"nom", "nom_caisse", "statut", "created_at", "updated_at"}.issubset(cols_caisses)
    assert {"designation_id", "designation_text"}.issubset(cols_lignes)
    assert {
        "0021_evenement_caisses_detail.sql",
        "0022_caisse_designations.sql",
        "0023_ecritures_auto_unique.sql",
        "0025_subventions_auto_unique.sql",
    }.issubset(migrations)


def test_run_migrations_met_a_jour_evenement_caisses_historique(tmp_db) -> None:
    set_db_file(str(tmp_db))
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS _migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT NOT NULL UNIQUE,
                appliquee_le TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS evenements (
                id INTEGER PRIMARY KEY AUTOINCREMENT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS evenement_caisses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                evenement_id INTEGER NOT NULL,
                nom_caisse TEXT NOT NULL,
                commentaire TEXT,
                FOREIGN KEY (evenement_id) REFERENCES evenements(id)
            )
            """
        )
        conn.execute("INSERT INTO evenements DEFAULT VALUES")
        conn.execute(
            """
            INSERT INTO evenement_caisses (evenement_id, nom_caisse, commentaire)
            VALUES (1, 'Caisse historique', 'legacy')
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tresorerie_operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                statut TEXT,
                source_module TEXT,
                source_id INTEGER
            )
            """
        )
        legacy_migrations = sorted(
            migration.name
            for migration in MIGRATIONS_DIR.glob("*.sql")
            if migration.name < "0021_evenement_caisses_detail.sql"
        )
        conn.executemany(
            "INSERT INTO _migrations (nom) VALUES (?)",
            [(name,) for name in legacy_migrations],
        )
        conn.commit()
    finally:
        conn.close()

    run_migrations()

    conn = get_connection()
    try:
        cols_caisses = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(evenement_caisses)").fetchall()
        }
        row = conn.execute(
            "SELECT nom, nom_caisse, statut FROM evenement_caisses WHERE id = 1"
        ).fetchone()
    finally:
        conn.close()
        set_db_file("")

    assert {"nom", "nom_caisse", "statut", "created_at", "updated_at"}.issubset(cols_caisses)
    assert row is not None
    assert row["nom"] == "Caisse historique"
    assert row["nom_caisse"] == "Caisse historique"
    assert row["statut"] == "ouvert"


def test_split_sql_script_handles_semicolons_comments_and_triggers() -> None:
    sql = """
    -- Commentaire avec point-virgule ; ici
    CREATE TABLE test_items (
        id INTEGER PRIMARY KEY,
        label TEXT NOT NULL
    );

    /* Commentaire bloc
       avec ; dedans */
    INSERT INTO test_items (label) VALUES ('Valeur ; avec point virgule ;');

    CREATE TRIGGER trg_test_items_after_insert
    AFTER INSERT ON test_items
    BEGIN
        UPDATE test_items SET label = label || ' [notifié]' WHERE id = NEW.id;
    END;

    INSERT INTO test_items (label) VALUES ('Deuxième item');

    CREATE TABLE `back;tick` (label TEXT);
    INSERT INTO `back;tick` (label) VALUES ('identifiant entre accents graves');
    CREATE TABLE [square;name] (label TEXT);
    INSERT INTO [square;name] (label) VALUES ('identifiant entre crochets');
    """

    statements = split_sql_script(sql)
    assert len(statements) == 8

    conn = sqlite3.connect(":memory:")
    try:
        conn.row_factory = sqlite3.Row
        _execute_migration(conn, sql)
        conn.commit()

        rows = conn.execute("SELECT * FROM test_items ORDER BY id").fetchall()
        assert len(rows) == 2
        assert rows[0]["label"] == "Valeur ; avec point virgule ;"
        assert rows[1]["label"] == "Deuxième item [notifié]"
        assert conn.execute("SELECT label FROM `back;tick`").fetchone()["label"] == (
            "identifiant entre accents graves"
        )
        assert conn.execute("SELECT label FROM [square;name]").fetchone()["label"] == (
            "identifiant entre crochets"
        )
    finally:
        conn.close()


def test_migration_atomic_rollback_on_failure(tmp_db) -> None:
    set_db_file(str(tmp_db))
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS test_atomic (
                id INTEGER PRIMARY KEY,
                val TEXT UNIQUE
            )
            """
        )
        conn.commit()

        bad_sql = """
        INSERT INTO test_atomic (val) VALUES ('ok1');
        INSERT INTO test_atomic (val) VALUES ('ok1'); -- Duplication viole UNIQUE
        """

        conn.execute("BEGIN IMMEDIATE")
        with pytest.raises(sqlite3.IntegrityError):
            _execute_migration(conn, bad_sql)
            conn.commit()
        conn.rollback()

        count = conn.execute("SELECT COUNT(*) AS total FROM test_atomic").fetchone()["total"]
        assert count == 0
    finally:
        conn.close()
        set_db_file("")


def test_run_migrations_rolls_back_failed_migration_file(tmp_db, tmp_path, monkeypatch):
    from db.migrations import runner

    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    (migrations_dir / "0001_atomic.sql").write_text(
        """
        CREATE TABLE atomic_probe (value TEXT UNIQUE);
        INSERT INTO atomic_probe VALUES ('duplicate');
        INSERT INTO atomic_probe VALUES ('duplicate');
        """,
        encoding="utf-8",
    )
    monkeypatch.setattr(runner, "MIGRATIONS_DIR", migrations_dir)
    set_db_file(str(tmp_db))

    with pytest.raises(sqlite3.IntegrityError):
        run_migrations()

    conn = get_connection()
    try:
        table = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'atomic_probe'"
        ).fetchone()
        migration = conn.execute(
            "SELECT nom FROM _migrations WHERE nom = '0001_atomic.sql'"
        ).fetchone()
    finally:
        conn.close()
        set_db_file("")

    assert table is None
    assert migration is None


def test_migrations_with_0014_applied(tmp_db) -> None:
    set_db_file(str(tmp_db))
    run_migrations()

    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT nom FROM _migrations WHERE nom = '0014_gap_reconciliation.sql'"
        ).fetchone()
        assert row is not None
    finally:
        conn.close()
        set_db_file("")
