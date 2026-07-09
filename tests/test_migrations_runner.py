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
        "0003_stock.sql",
        "0004_buvette.sql",
        "0005_evenements.sql",
        "0006_evenements_5b.sql",
        "0007_export_config.sql",
        "0008_tresorerie.sql",
        "0009_cloture.sql",
        "0010_parametres_globaux.sql",
        "0011_exports.sql",
        "0012_sauvegardes.sql",
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

    assert count == 12
