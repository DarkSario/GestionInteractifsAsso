"""Gestion sécurité mot de passe de déclôture (Phase 6b)."""

from __future__ import annotations

import hashlib

from db.models.cloture import get_parametre, set_parametre
from utils.logger import get_logger

logger = get_logger(__name__)

_MDP_HASH_CLE = "mdp_decloture_hash"
_MDP_DEFAUT_CLE = "mdp_decloture_defaut"
_CODE_MASTER_CLE = "code_master_hash"


def hash_password(password: str) -> str:
    """Retourne le hash SHA-256 hexadécimal du mot de passe."""
    return hashlib.sha256(password.encode()).hexdigest()


def _get_hash_actuel() -> str:
    """Retourne le hash stocké, ou celui du mot de passe par défaut si vide."""
    hash_stocke = get_parametre(_MDP_HASH_CLE)
    if hash_stocke:
        return hash_stocke
    # Aucun hash configuré → utiliser le mot de passe par défaut
    mdp_defaut = get_parametre(_MDP_DEFAUT_CLE) or "asso2024"
    return hash_password(mdp_defaut)


def verifier_mot_de_passe_decloture(mdp_saisi: str) -> bool:
    """Vérifie le mot de passe de déclôture saisi."""
    if not mdp_saisi:
        return False
    try:
        return hash_password(mdp_saisi) == _get_hash_actuel()
    except Exception:
        logger.exception("Erreur lors de la vérification du mot de passe de déclôture")
        return False


def verifier_code_master(code_saisi: str) -> bool:
    """Vérifie le code master de récupération."""
    if not code_saisi:
        return False
    try:
        hash_master = get_parametre(_CODE_MASTER_CLE) or ""
        return hash_password(code_saisi) == hash_master
    except Exception:
        logger.exception("Erreur lors de la vérification du code master")
        return False


def changer_mot_de_passe_decloture(
    ancien_mdp: str, nouveau_mdp: str
) -> tuple[bool, str]:
    """Change le mot de passe de déclôture.

    Valide l'ancien mot de passe OU le code master avant de changer.
    Retourne (succès, message_erreur).
    """
    if not nouveau_mdp or not nouveau_mdp.strip():
        return False, "Le nouveau mot de passe ne peut pas être vide."

    if not verifier_mot_de_passe_decloture(ancien_mdp) and not verifier_code_master(ancien_mdp):
        return False, "Mot de passe actuel ou code master incorrect."

    try:
        set_parametre(_MDP_HASH_CLE, hash_password(nouveau_mdp))
        return True, ""
    except Exception as exc:
        logger.exception("Erreur lors du changement de mot de passe")
        return False, str(exc)


def reset_mot_de_passe_via_master(code_master: str) -> tuple[bool, str]:
    """Réinitialise le mot de passe au défaut via le code master.

    Retourne (succès, message_erreur).
    """
    if not verifier_code_master(code_master):
        return False, "Code master incorrect."

    try:
        # Remettre le hash vide = retour au mot de passe par défaut
        set_parametre(_MDP_HASH_CLE, "")
        return True, ""
    except Exception as exc:
        logger.exception("Erreur lors de la réinitialisation du mot de passe")
        return False, str(exc)
