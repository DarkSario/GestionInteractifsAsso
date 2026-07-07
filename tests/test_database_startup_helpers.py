"""Tests des helpers de création et d'ouverture de base."""

from datetime import date

from db.connection import set_db_file
from db.migrations.runner import run_migrations
from ui.screens.db_helpers import (
    check_database_compatibility,
    validate_create_database_data,
)


def test_validate_create_database_data_reports_french_errors(tmp_path) -> None:
    missing_dir_db = tmp_path / "inexistant" / "association.txt"

    errors = validate_create_database_data(
        nom_asso="",
        exercice="",
        date_debut=date(2025, 9, 1),
        date_fin=date(2025, 9, 1),
        solde_ouverture="-1",
        db_path=str(missing_dir_db),
    )

    assert "Le nom de l'association est obligatoire." in errors
    assert "L'exercice est obligatoire." in errors
    assert "La date de fin doit être postérieure à la date de début." in errors
    assert "Le solde d'ouverture bancaire doit être supérieur ou égal à 0." in errors
    assert "Le fichier de base de données doit avoir l'extension .db." in errors
    assert "Le dossier choisi pour la base de données n'existe pas." in errors


def test_check_database_compatibility_accepts_initialized_db(tmp_db) -> None:
    set_db_file(str(tmp_db))
    run_migrations()

    is_valid, error_message = check_database_compatibility(tmp_db)
    set_db_file("")

    assert is_valid is True
    assert error_message is None


def test_check_database_compatibility_rejects_non_sqlite_file(tmp_path) -> None:
    invalid_db = tmp_path / "not_a_database.db"
    invalid_db.write_text("contenu invalide", encoding="utf-8")

    is_valid, error_message = check_database_compatibility(invalid_db)

    assert is_valid is False
    assert error_message == "Le fichier sélectionné n'est pas une base SQLite valide."
