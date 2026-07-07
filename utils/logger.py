"""Logger centralisé pour toute l'application."""

import logging
import logging.handlers
from pathlib import Path

from config.settings import LOGS_DIR

# Crée le dossier de logs si nécessaire
LOGS_DIR.mkdir(parents=True, exist_ok=True)

_LOG_FILE = LOGS_DIR / "app.log"
_MAX_BYTES = 5 * 1024 * 1024  # 5 Mo
_BACKUP_COUNT = 3

_formatter = logging.Formatter(
    fmt="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Handler fichier avec rotation
_file_handler = logging.handlers.RotatingFileHandler(
    _LOG_FILE,
    maxBytes=_MAX_BYTES,
    backupCount=_BACKUP_COUNT,
    encoding="utf-8",
)
_file_handler.setFormatter(_formatter)
_file_handler.setLevel(logging.DEBUG)

# Handler console
_console_handler = logging.StreamHandler()
_console_handler.setFormatter(_formatter)
_console_handler.setLevel(logging.INFO)

# Racine du logger applicatif
_root_logger = logging.getLogger("gia")
_root_logger.setLevel(logging.DEBUG)
if not _root_logger.handlers:
    _root_logger.addHandler(_file_handler)
    _root_logger.addHandler(_console_handler)


def get_logger(name: str) -> logging.Logger:
    """Retourne un logger nommé rattaché au logger racine de l'application.

    Args:
        name: Nom du module (utiliser ``__name__``).

    Returns:
        Instance de :class:`logging.Logger`.
    """
    if name.startswith("gia.") or name == "gia":
        return logging.getLogger(name)
    return logging.getLogger(f"gia.{name}")
