"""Couche métier pour les paramètres globaux de l'application (Phase 7).

Ne doit pas importer tkinter ni customtkinter.
"""

from __future__ import annotations

import re

from db.models.parametres_globaux import (
    get_parametre,
    get_all_parametres,
    set_parametre,
)
from utils.logger import get_logger

logger = get_logger(__name__)

_NOM_MAX_LEN = 100
_NOM_RE = re.compile(r"^[a-zA-ZÀ-ÿ0-9 '\-.()]+$")


# ── Validation ────────────────────────────────────────────────────────────────


def valider_nom_liste(nom: str) -> list[str]:
    """Valide un nom pour les listes (classes, types, modes).

    Retourne une liste d'erreurs (vide si valide).
    """
    erreurs: list[str] = []
    nom = nom.strip()
    if not nom:
        erreurs.append("Le nom ne peut pas être vide.")
    elif len(nom) > _NOM_MAX_LEN:
        erreurs.append(f"Le nom ne doit pas dépasser {_NOM_MAX_LEN} caractères.")
    elif not _NOM_RE.match(nom):
        erreurs.append(
            "Le nom contient des caractères non autorisés "
            "(lettres, chiffres, espaces, tirets, apostrophes, points et parenthèses uniquement)."
        )
    return erreurs


# ── Informations de l'association ─────────────────────────────────────────────


def get_infos_asso() -> dict:
    """Retourne les informations de l'association depuis la DB.

    Clés retournées : nom, adresse, telephone, email, logo_path.
    """
    return {
        "nom": get_parametre("asso_nom", ""),
        "adresse": get_parametre("asso_adresse", ""),
        "telephone": get_parametre("asso_telephone", ""),
        "email": get_parametre("asso_email", ""),
        "logo_path": get_parametre("asso_logo_path", ""),
    }


def set_infos_asso(
    nom: str,
    adresse: str,
    telephone: str,
    email: str,
    logo_path: str,
) -> list[str]:
    """Valide et enregistre les informations de l'association.

    Retourne une liste d'erreurs (vide si tout est OK).
    """
    erreurs: list[str] = []

    nom = nom.strip()
    if not nom:
        erreurs.append("Le nom de l'association est obligatoire.")
    elif len(nom) > 200:
        erreurs.append("Le nom de l'association ne doit pas dépasser 200 caractères.")

    if erreurs:
        return erreurs

    set_parametre("asso_nom", nom)
    set_parametre("asso_adresse", adresse.strip())
    set_parametre("asso_telephone", telephone.strip())
    set_parametre("asso_email", email.strip())
    set_parametre("asso_logo_path", logo_path.strip())
    return []


# ── Configuration système ─────────────────────────────────────────────────────


def get_config_systeme() -> dict:
    """Retourne la configuration système.

    Clés retournées : sauvegarde_auto, sauvegarde_frequence,
    sauvegarde_dossier, export_dossier_defaut, theme_mode, derniere_sauvegarde.
    """
    return {
        "sauvegarde_auto": get_parametre("sauvegarde_auto", "0"),
        "sauvegarde_frequence": get_parametre("sauvegarde_frequence", "7"),
        "sauvegarde_dossier": get_parametre("sauvegarde_dossier", ""),
        "export_dossier_defaut": get_parametre("export_dossier_defaut", ""),
        "theme_mode": get_parametre("theme_mode", "dark"),
        "derniere_sauvegarde": get_parametre("derniere_sauvegarde", ""),
    }


def set_config_systeme(**kwargs) -> bool:
    """Enregistre un ou plusieurs paramètres système.

    Clés acceptées : sauvegarde_auto, sauvegarde_frequence,
    sauvegarde_dossier, export_dossier_defaut, theme_mode, derniere_sauvegarde.
    Retourne True si tous les paramètres ont été enregistrés sans erreur.
    """
    cles_autorisees = {
        "sauvegarde_auto",
        "sauvegarde_frequence",
        "sauvegarde_dossier",
        "export_dossier_defaut",
        "theme_mode",
        "derniere_sauvegarde",
    }
    ok = True
    for cle, valeur in kwargs.items():
        if cle in cles_autorisees:
            if not set_parametre(cle, str(valeur)):
                ok = False
        else:
            logger.warning("set_config_systeme: clé inconnue '%s'", cle)
    return ok


# ── Configuration financière ──────────────────────────────────────────────────


def get_config_financiere() -> dict:
    """Retourne la configuration financière.

    Clés retournées : taux_sumup, compte_principal_id, compte_caisse_id.
    """
    return {
        "taux_sumup": get_parametre("taux_sumup", "1.75"),
        "compte_principal_id": get_parametre("compte_principal_id", ""),
        "compte_caisse_id": get_parametre("compte_caisse_id", ""),
    }


def set_config_financiere(**kwargs) -> bool:
    """Enregistre un ou plusieurs paramètres financiers.

    Clés acceptées : taux_sumup, compte_principal_id, compte_caisse_id.
    Retourne True si tous les paramètres ont été enregistrés sans erreur.
    """
    cles_autorisees = {"taux_sumup", "compte_principal_id", "compte_caisse_id"}
    ok = True
    for cle, valeur in kwargs.items():
        if cle in cles_autorisees:
            if not set_parametre(cle, str(valeur)):
                ok = False
        else:
            logger.warning("set_config_financiere: clé inconnue '%s'", cle)
    return ok
