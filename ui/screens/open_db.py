"""Ouverture d'une base de données existante."""

from tkinter import filedialog

from db.connection import set_db_file
from db.migrations.runner import run_migrations
from ui.components.dialogs import afficher_erreur
from ui.screens.db_helpers import check_database_compatibility


def open_existing_database(parent) -> str | None:
    """Ouvre un sélecteur de fichier et initialise la base choisie."""
    db_path = filedialog.askopenfilename(
        parent=parent,
        title="Ouvrir une base existante",
        filetypes=[("Bases SQLite", "*.db"), ("Tous les fichiers", "*.*")],
    )
    if not db_path:
        return None

    is_valid, error_message = check_database_compatibility(db_path)
    if not is_valid:
        afficher_erreur(parent, "Base incompatible", error_message or "Base invalide.")
        return None

    try:
        set_db_file(db_path)
        run_migrations()
    except Exception as exc:
        afficher_erreur(
            parent,
            "Ouverture impossible",
            f"Impossible d'ouvrir la base sélectionnée.\n\nDétail : {exc}",
        )
        return None

    return db_path
