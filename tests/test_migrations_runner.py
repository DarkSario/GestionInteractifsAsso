"""Tests du système d'initialisation et de migrations SQLite."""

from pathlib import Path

from db.connection import get_connection, set_db_file
from db.migrations.runner import run_migrations

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
