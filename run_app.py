"""Wrapper de lancement de l'application avec gestion des erreurs globales."""

import sys
import traceback

from utils.logger import get_logger
from ui.theme import load_theme
from ui.app import MainApp

logger = get_logger(__name__)


def main() -> None:
    """Lance l'application principale."""
    logger.info("=== Démarrage de l'application ===")
    try:
        load_theme()
        app = MainApp()
        app.mainloop()
    except Exception:
        logger.critical("Erreur non gérée au démarrage :\n%s", traceback.format_exc())
        sys.exit(1)
    finally:
        logger.info("=== Fermeture de l'application ===")


if __name__ == "__main__":
    main()
