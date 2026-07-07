"""Helpers purs pour la création et l'ouverture de bases SQLite."""

import sqlite3
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path


def validate_create_database_data(
    *,
    nom_asso: str,
    exercice: str,
    date_debut: date,
    date_fin: date,
    solde_ouverture: str,
    db_path: str,
) -> list[str]:
    """Valide les champs du formulaire de création."""
    errors: list[str] = []

    if not nom_asso.strip():
        errors.append("Le nom de l'association est obligatoire.")
    if not exercice.strip():
        errors.append("L'exercice est obligatoire.")
    if date_fin <= date_debut:
        errors.append("La date de fin doit être postérieure à la date de début.")

    try:
        amount = Decimal(solde_ouverture.replace(",", ".").strip())
    except (InvalidOperation, AttributeError):
        errors.append("Le solde d'ouverture bancaire doit être un nombre valide.")
    else:
        if amount < 0:
            errors.append("Le solde d'ouverture bancaire doit être supérieur ou égal à 0.")

    if not db_path:
        errors.append("L'emplacement du fichier .db est obligatoire.")
    else:
        path = Path(db_path)
        if path.suffix.lower() != ".db":
            errors.append("Le fichier de base de données doit avoir l'extension .db.")
        if not path.parent.exists():
            errors.append("Le dossier choisi pour la base de données n'existe pas.")
        if path.exists():
            errors.append("Le fichier de base de données existe déjà.")

    return errors


def check_database_compatibility(path: str | Path) -> tuple[bool, str | None]:
    """Vérifie que le fichier correspond à une base compatible."""
    db_path = Path(path)
    if not db_path.exists():
        return False, "Le fichier sélectionné est introuvable."
    if db_path.suffix.lower() != ".db":
        return False, "Le fichier sélectionné doit avoir l'extension .db."

    try:
        conn = sqlite3.connect(db_path)
        try:
            row = conn.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table' AND name = 'config'
                """
            ).fetchone()
        finally:
            conn.close()
    except sqlite3.Error:
        return False, "Le fichier sélectionné n'est pas une base SQLite valide."

    if not row:
        return False, "La base sélectionnée n'est pas compatible : table config introuvable."

    return True, None
