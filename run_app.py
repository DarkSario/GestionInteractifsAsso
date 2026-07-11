"""Wrapper de lancement de l'application avec gestion des erreurs globales."""

import sys
import traceback

try:
    import tkinter  # noqa: F401
except ImportError:
    print("ERREUR : tkinter n'est pas installé.")
    print("Sur Linux/Mac : sudo apt install python3-tk")
    print("Sur Windows   : réinstaller Python en cochant « tcl/tk and IDLE »")
    sys.exit(1)

from ui.app import MainApp
from ui.screens.welcome import WelcomeScreen
from utils.logger import get_logger

logger = get_logger(__name__)


def main() -> None:
    """Lance l'application principale."""
    logger.info("=== Démarrage de l'application ===")
    try:
        welcome = WelcomeScreen()
        db_path = welcome.run()
        if not db_path:
            logger.info("Aucune base sélectionnée, fermeture de l'application.")
            return

        app = MainApp(db_path)
        app.mainloop()
    except Exception:
        logger.critical("Erreur non gérée au démarrage :\n%s", traceback.format_exc())
        sys.exit(1)
    finally:
        logger.info("=== Fermeture de l'application ===")


if __name__ == "__main__":
    main()
