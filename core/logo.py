"""Gestion du logo de l'association — Phase 21.

Le logo est copié dans data/logo_asso.png (chemin fixe).
La configuration (position, taille) est stockée dans la table parametres.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from utils.logger import get_logger

logger = get_logger(__name__)

_BASE_DIR = Path(__file__).parent.parent
_LOGO_PATH = _BASE_DIR / "data" / "logo_asso.png"

# Valeurs par défaut
_POSITION_DEFAUT = "gauche"
_TAILLE_DEFAUT = "moyenne"


def get_logo_path() -> str | None:
    """Retourne le chemin du logo s'il existe, sinon None."""
    if _LOGO_PATH.is_file():
        return str(_LOGO_PATH)
    return None


def get_logo_config() -> dict:
    """Retourne la configuration du logo (position et taille)."""
    try:
        from db.models.parametres_globaux import get_parametre

        return {
            "path": get_logo_path(),
            "position": get_parametre("logo_position", _POSITION_DEFAUT) or _POSITION_DEFAUT,
            "taille": get_parametre("logo_taille", _TAILLE_DEFAUT) or _TAILLE_DEFAUT,
        }
    except Exception as exc:
        logger.error("get_logo_config: %s", exc)
        return {
            "path": get_logo_path(),
            "position": _POSITION_DEFAUT,
            "taille": _TAILLE_DEFAUT,
        }


def set_logo(source_path: str) -> bool:
    """Copie le logo source vers data/logo_asso.png.

    Args:
        source_path: Chemin du fichier source (PNG, JPG, GIF).

    Returns:
        True si succès, False sinon.
    """
    if not source_path or not os.path.isfile(source_path):
        logger.error("set_logo: fichier source introuvable : %s", source_path)
        return False

    try:
        _LOGO_PATH.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, str(_LOGO_PATH))
        # Enregistre le chemin dans les paramètres
        from db.models.parametres_globaux import set_parametre

        set_parametre("logo_path", str(_LOGO_PATH))
        logger.info("Logo copié vers %s", _LOGO_PATH)
        return True
    except Exception as exc:
        logger.error("set_logo: %s", exc)
        return False


def supprimer_logo() -> bool:
    """Supprime le fichier logo data/logo_asso.png.

    Returns:
        True si supprimé ou inexistant, False en cas d'erreur.
    """
    try:
        if _LOGO_PATH.is_file():
            _LOGO_PATH.unlink()
        from db.models.parametres_globaux import set_parametre

        set_parametre("logo_path", "")
        logger.info("Logo supprimé")
        return True
    except Exception as exc:
        logger.error("supprimer_logo: %s", exc)
        return False


def set_logo_config(position: str | None = None, taille: str | None = None) -> bool:
    """Met à jour la configuration du logo dans les paramètres.

    Args:
        position: 'gauche', 'centre' ou 'droite'.
        taille: 'petite', 'moyenne' ou 'grande'.

    Returns:
        True si succès.
    """
    try:
        from db.models.parametres_globaux import set_parametre

        positions_valides = {"gauche", "centre", "droite"}
        tailles_valides = {"petite", "moyenne", "grande"}

        if position and position in positions_valides:
            set_parametre("logo_position", position)
        if taille and taille in tailles_valides:
            set_parametre("logo_taille", taille)
        return True
    except Exception as exc:
        logger.error("set_logo_config: %s", exc)
        return False
