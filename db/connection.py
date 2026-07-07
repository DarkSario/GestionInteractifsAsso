"""Gestion de la connexion SQLite."""

import sqlite3
from pathlib import Path

from config.settings import DB_PATH
from utils.logger import get_logger

logger = get_logger(__name__)

_db_file: Path = DB_PATH

# Délai d'attente en cas de base de données verrouillée (secondes)
_BUSY_TIMEOUT_MS = 5000
_CONNECT_TIMEOUT_S = _BUSY_TIMEOUT_MS / 1000  # 5.0


def set_db_file(path: Path | str) -> None:
    """Définit le fichier de base de données actif.

    Args:
        path: Chemin absolu ou relatif vers le fichier ``.db``.
    """
    global _db_file
    _db_file = Path(path)
    logger.info("Fichier DB actif : %s", _db_file)


def get_db_file() -> Path:
    """Retourne le chemin du fichier de base de données actif."""
    return _db_file


def get_connection() -> sqlite3.Connection:
    """Ouvre et retourne une connexion SQLite prête à l'emploi.

    Caractéristiques :
    - :attr:`sqlite3.Row` comme ``row_factory`` (accès aux colonnes par nom)
    - Mode WAL pour de meilleures performances concurrentes
    - ``busy_timeout`` à 5 secondes

    Returns:
        Instance de :class:`sqlite3.Connection`.
    """
    conn = sqlite3.connect(_db_file, timeout=_CONNECT_TIMEOUT_S)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute(f"PRAGMA busy_timeout={_BUSY_TIMEOUT_MS}")
    logger.debug("Connexion ouverte sur %s", _db_file)
    return conn
