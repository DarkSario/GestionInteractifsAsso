"""Point d'entrée principal de l'application."""

from utils.logger import get_logger
from ui.theme import load_theme
from ui.app import MainApp

logger = get_logger(__name__)

if __name__ == "__main__":
    logger.info("Démarrage de l'application")
    load_theme()
    app = MainApp()
    app.mainloop()
