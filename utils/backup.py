"""Sauvegarde et restauration de la base de données SQLite."""

import shutil
from datetime import datetime
from pathlib import Path

from utils.logger import get_logger

logger = get_logger(__name__)


def backup_db(db_path: Path, backup_dir: Path | None = None) -> Path:
    """Crée une copie de sauvegarde de la base de données.

    Args:
        db_path: Chemin vers le fichier ``.db`` source.
        backup_dir: Dossier de destination. Par défaut, même dossier que la DB.

    Returns:
        Chemin du fichier de sauvegarde créé.

    Raises:
        FileNotFoundError: Si ``db_path`` n'existe pas.
    """
    if not db_path.exists():
        raise FileNotFoundError(f"Base de données introuvable : {db_path}")

    dest_dir = backup_dir or db_path.parent
    dest_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = dest_dir / f"{db_path.stem}.bak.{timestamp}{db_path.suffix}"

    shutil.copy2(db_path, backup_path)
    logger.info("Sauvegarde créée : %s", backup_path)
    return backup_path


def restore_db(backup_path: Path, db_path: Path) -> None:
    """Restaure la base de données depuis une sauvegarde.

    La base de données active est remplacée par le fichier de sauvegarde.
    Un backup de sécurité est créé avant l'écrasement.

    Args:
        backup_path: Fichier ``.bak.*`` à restaurer.
        db_path: Chemin vers la base de données active à remplacer.

    Raises:
        FileNotFoundError: Si ``backup_path`` n'existe pas.
    """
    if not backup_path.exists():
        raise FileNotFoundError(f"Fichier de sauvegarde introuvable : {backup_path}")

    # Sauvegarde de sécurité avant restauration
    if db_path.exists():
        safety = db_path.with_suffix(
            f".bak.avant_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        )
        shutil.copy2(db_path, safety)
        logger.info("Sauvegarde de sécurité avant restauration : %s", safety)

    shutil.copy2(backup_path, db_path)
    logger.info("Base de données restaurée depuis : %s", backup_path)


def list_backups(db_path: Path, backup_dir: Path | None = None) -> list[Path]:
    """Liste les sauvegardes disponibles pour une base de données.

    Args:
        db_path: Chemin de référence de la base de données.
        backup_dir: Dossier à inspecter. Par défaut, même dossier que la DB.

    Returns:
        Liste de chemins triée par date décroissante.
    """
    search_dir = backup_dir or db_path.parent
    pattern = f"{db_path.stem}.bak.*"
    backups = sorted(search_dir.glob(pattern), reverse=True)
    return backups
