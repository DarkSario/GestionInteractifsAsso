"""Gestion du thème des exports PDF — Phase 21.

Les paramètres sont stockés dans la table parametres.
"""

from __future__ import annotations

import re

from utils.logger import get_logger

logger = get_logger(__name__)

# Valeurs par défaut
_DEFAUTS = {
    "export_couleur_principale": "#1f6aa5",
    "export_couleur_secondaire": "#144870",
    "export_police_titres": "Helvetica",
    "export_police_corps": "Helvetica",
    "export_style_tableaux": "moderne",
}

_STYLES_VALIDES = {"moderne", "classique", "minimaliste"}
_REGEX_COULEUR = re.compile(r"^#[0-9A-Fa-f]{6}$")


def _valider_couleur(couleur: str) -> bool:
    """Vérifie que la couleur est au format #RRGGBB."""
    return bool(_REGEX_COULEUR.match(couleur or ""))


def get_theme_export() -> dict:
    """Retourne le thème actuel des exports.

    Returns:
        Dictionnaire avec les clés : couleur_principale, couleur_secondaire,
        police_titres, police_corps, style_tableaux.
    """
    try:
        from db.models.parametres_globaux import get_parametre

        return {
            "couleur_principale": get_parametre(
                "export_couleur_principale", _DEFAUTS["export_couleur_principale"]
            ) or _DEFAUTS["export_couleur_principale"],
            "couleur_secondaire": get_parametre(
                "export_couleur_secondaire", _DEFAUTS["export_couleur_secondaire"]
            ) or _DEFAUTS["export_couleur_secondaire"],
            "police_titres": get_parametre(
                "export_police_titres", _DEFAUTS["export_police_titres"]
            ) or _DEFAUTS["export_police_titres"],
            "police_corps": get_parametre(
                "export_police_corps", _DEFAUTS["export_police_corps"]
            ) or _DEFAUTS["export_police_corps"],
            "style_tableaux": get_parametre(
                "export_style_tableaux", _DEFAUTS["export_style_tableaux"]
            ) or _DEFAUTS["export_style_tableaux"],
        }
    except Exception as exc:
        logger.error("get_theme_export: %s", exc)
        return {k.replace("export_", ""): v for k, v in _DEFAUTS.items()}


def set_theme_export(**kwargs) -> None:
    """Met à jour les paramètres de thème dans la base de données.

    Kwargs acceptés : couleur_principale, couleur_secondaire,
    police_titres, police_corps, style_tableaux.
    """
    try:
        from db.models.parametres_globaux import set_parametre

        mapping = {
            "couleur_principale": "export_couleur_principale",
            "couleur_secondaire": "export_couleur_secondaire",
            "police_titres": "export_police_titres",
            "police_corps": "export_police_corps",
            "style_tableaux": "export_style_tableaux",
        }

        for cle_theme, cle_param in mapping.items():
            if cle_theme in kwargs:
                valeur = str(kwargs[cle_theme]).strip()
                if cle_theme in ("couleur_principale", "couleur_secondaire"):
                    if not _valider_couleur(valeur):
                        logger.warning("set_theme_export: couleur invalide '%s' ignorée", valeur)
                        continue
                elif cle_theme == "style_tableaux":
                    if valeur not in _STYLES_VALIDES:
                        logger.warning("set_theme_export: style invalide '%s' ignoré", valeur)
                        continue
                set_parametre(cle_param, valeur)
    except Exception as exc:
        logger.error("set_theme_export: %s", exc)


def get_couleur_principale() -> str:
    """Retourne la couleur principale hex."""
    try:
        from db.models.parametres_globaux import get_parametre

        couleur = get_parametre("export_couleur_principale", _DEFAUTS["export_couleur_principale"])
        return couleur if _valider_couleur(couleur) else _DEFAUTS["export_couleur_principale"]
    except Exception:
        return _DEFAUTS["export_couleur_principale"]


def get_couleur_secondaire() -> str:
    """Retourne la couleur secondaire hex."""
    try:
        from db.models.parametres_globaux import get_parametre

        couleur = get_parametre("export_couleur_secondaire", _DEFAUTS["export_couleur_secondaire"])
        return couleur if _valider_couleur(couleur) else _DEFAUTS["export_couleur_secondaire"]
    except Exception:
        return _DEFAUTS["export_couleur_secondaire"]
