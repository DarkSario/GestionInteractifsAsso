"""Chargement et application du thème visuel depuis config/theme.json."""

import json
from typing import Any

try:
    import customtkinter as ctk
except ModuleNotFoundError:  # pragma: no cover - environnement sans Tk
    class _DummyFont:
        def __init__(self, *_args, **_kwargs):
            pass

    class _DummyCTk:
        CTkFont = _DummyFont

        @staticmethod
        def set_appearance_mode(*_args, **_kwargs):
            return None

        @staticmethod
        def set_default_color_theme(*_args, **_kwargs):
            return None

    ctk = _DummyCTk()

from config.settings import THEME_FILE
from utils.logger import get_logger

logger = get_logger(__name__)

# Thème par défaut (utilisé si theme.json est absent ou corrompu)
_DEFAULT_THEME: dict[str, Any] = {
    "appearance_mode": "dark",
    "color_theme": "blue",
    "primary_color": "#1f6aa5",
    "secondary_color": "#144870",
    "font_family": "Arial",
    "font_size": "normal",
    "logo_path": None,
}

# Tailles de police selon le paramètre font_size
_FONT_SIZES: dict[str, dict[str, int]] = {
    "small":  {"normal": 11, "title": 14, "subtitle": 12, "small": 9},
    "normal": {"normal": 13, "title": 18, "subtitle": 14, "small": 11},
    "large":  {"normal": 15, "title": 22, "subtitle": 17, "small": 13},
}

# Données du thème actif (chargées lors de load_theme())
_current_theme: dict[str, Any] = dict(_DEFAULT_THEME)

# Polices exposées aux modules UI
FONTS: dict[str, ctk.CTkFont] = {}

# Couleurs exposées aux modules UI
COLORS: dict[str, str] = {}


def load_theme() -> None:
    """Charge le thème depuis ``config/theme.json`` et l'applique à CustomTkinter.

    Si le fichier est absent ou illisible, le thème par défaut est utilisé.
    """
    global _current_theme, FONTS, COLORS

    theme_data = _read_theme_file()
    _current_theme = {**_DEFAULT_THEME, **theme_data}

    # Application du mode (dark / light / system)
    ctk.set_appearance_mode(_current_theme.get("appearance_mode", "dark"))

    # Thème de couleur CustomTkinter (blue / green / dark-blue)
    color_theme = _current_theme.get("color_theme", "blue")
    ctk.set_default_color_theme(color_theme)

    # Construction des fonts
    family = _current_theme.get("font_family", "Arial")
    size_key = _current_theme.get("font_size", "normal")
    sizes = _FONT_SIZES.get(size_key, _FONT_SIZES["normal"])

    FONTS = {
        "normal":   ctk.CTkFont(family=family, size=sizes["normal"]),
        "title":    ctk.CTkFont(family=family, size=sizes["title"],    weight="bold"),
        "subtitle": ctk.CTkFont(family=family, size=sizes["subtitle"], weight="bold"),
        "small":    ctk.CTkFont(family=family, size=sizes["small"]),
        "bold":     ctk.CTkFont(family=family, size=sizes["normal"],   weight="bold"),
    }

    # Couleurs
    COLORS = {
        "primary":   _current_theme.get("primary_color",   "#1f6aa5"),
        "secondary": _current_theme.get("secondary_color", "#144870"),
    }

    logger.info(
        "Thème chargé : mode=%s, couleur=%s, police=%s (%s)",
        _current_theme["appearance_mode"],
        _current_theme["color_theme"],
        family,
        size_key,
    )


def get_theme() -> dict[str, Any]:
    """Retourne une copie du thème actif."""
    return dict(_current_theme)


def save_theme(data: dict[str, Any]) -> None:
    """Sauvegarde les données de thème dans ``config/theme.json``.

    Args:
        data: Dictionnaire de configuration du thème à persister.
    """
    THEME_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(THEME_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info("Thème sauvegardé dans %s", THEME_FILE)


def _read_theme_file() -> dict[str, Any]:
    """Lit le fichier theme.json et retourne son contenu.

    En cas d'erreur, retourne un dictionnaire vide (le thème par défaut sera utilisé).
    """
    if not THEME_FILE.exists():
        logger.warning("theme.json introuvable — utilisation des valeurs par défaut")
        return {}
    try:
        with open(THEME_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Erreur de lecture de theme.json : %s", exc)
        return {}
