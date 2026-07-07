"""Fixtures pytest pour la suite de tests de Gestion Interactifs Asso."""

from pathlib import Path

import pytest


@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    """Crée une base de données SQLite temporaire pour les tests.

    Yields:
        Chemin vers le fichier de base de données temporaire.
    """
    db_path = tmp_path / "test_association.db"
    return db_path


@pytest.fixture
def db_conn(tmp_db: Path):
    """Fournit une connexion SQLite ouverte sur une base temporaire.

    Applique les migrations avant de fournir la connexion.

    Yields:
        Instance de :class:`sqlite3.Connection`.
    """
    import db.connection as db_module
    from db.migrations.runner import run_migrations

    # Pointe vers la DB temporaire
    db_module.set_db_file(str(tmp_db))
    conn = db_module.get_connection()
    conn.close()
    run_migrations()
    conn = db_module.get_connection()
    yield conn
    conn.close()
    db_module.set_db_file("")
