"""Gestion sécurité mot de passe de déclôture (Phase 6b / Phase 14)."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets

from db.models.cloture import get_parametre, set_parametre
from utils.logger import get_logger

logger = get_logger(__name__)

_MDP_HASH_CLE = "mdp_decloture_hash"
_CODE_MASTER_CLE = "code_master_hash"


# ── Fonctions de hachage ──────────────────────────────────────────────────────


def _hasher_secret(secret: str) -> str:
    """Hash un secret avec scrypt + sel aléatoire.

    Retourne une chaîne au format ``sel_hex$hash_hex``.
    """
    sel = os.urandom(32)
    hash_ = hashlib.scrypt(
        secret.encode("utf-8"),
        salt=sel,
        n=16384,
        r=8,
        p=1,
        dklen=32,
    )
    return f"{sel.hex()}${hash_.hex()}"


def _verifier_secret(secret: str, stocke: str) -> bool:
    """Vérifie un secret contre un hash stocké.

    Gère deux formats :
    - Nouveau  : ``sel_hex$hash_hex`` (scrypt avec sel)
    - Héritage : hexdigest seul (SHA-256 sans sel, rétrocompatibilité)
    """
    if not stocke:
        return False
    if "$" in stocke:
        # Format scrypt
        try:
            sel_hex, hash_hex = stocke.split("$", 1)
            sel = bytes.fromhex(sel_hex)
            hash_attendu = bytes.fromhex(hash_hex)
            hash_calcule = hashlib.scrypt(
                secret.encode("utf-8"),
                salt=sel,
                n=16384,
                r=8,
                p=1,
                dklen=32,
            )
            return hmac.compare_digest(hash_calcule, hash_attendu)
        except Exception:
            return False
    else:
        # Format héritage SHA-256 (sans sel)
        try:
            return hmac.compare_digest(
                hashlib.sha256(secret.encode()).hexdigest(),  # noqa: S324
                stocke,
            )
        except Exception:
            return False


def hash_password(password: str) -> str:
    """Retourne le hash scrypt du mot de passe (format ``sel_hex$hash_hex``).

    Conservé pour la compatibilité avec le code appelant existant.
    """
    return _hasher_secret(password)


# ── Initialisation ────────────────────────────────────────────────────────────


def initialiser_secrets(
    mdp_initial: str | None = None,
    code_master_initial: str | None = None,
) -> None:
    """Initialise les secrets s'ils ne sont pas encore configurés.

    Si *mdp_initial* ou *code_master_initial* sont fournis (typiquement dans
    les tests), ils sont utilisés tels quels ; sinon des valeurs aléatoires
    sécurisées sont générées.

    Cette fonction est idempotente : elle ne modifie rien si les hashes sont
    déjà présents en base.
    """
    hash_mdp = get_parametre(_MDP_HASH_CLE)
    if not hash_mdp:
        mdp = mdp_initial or secrets.token_urlsafe(16)
        set_parametre(_MDP_HASH_CLE, _hasher_secret(mdp))
        if not mdp_initial:
            logger.warning(
                "Mot de passe de déclôture initialisé automatiquement. "
                "Utilisez Administration > Mot de passe déclôture pour le changer."
            )

    hash_master = get_parametre(_CODE_MASTER_CLE)
    if not hash_master:
        master = code_master_initial or secrets.token_urlsafe(24)
        set_parametre(_CODE_MASTER_CLE, _hasher_secret(master))
        if not code_master_initial:
            logger.warning(
                "Code master de récupération initialisé automatiquement. "
                "Conservez-le précieusement — il est nécessaire pour récupérer l'accès."
            )


def _get_hash_actuel() -> str:
    """Retourne le hash du mot de passe stocké.

    Initialise automatiquement avec un mot de passe aléatoire lors de la
    première utilisation (aucun hash configuré en base).
    """
    hash_stocke = get_parametre(_MDP_HASH_CLE)
    if hash_stocke:
        return hash_stocke
    # Première utilisation : générer et persister un mot de passe aléatoire
    initialiser_secrets()
    return get_parametre(_MDP_HASH_CLE) or ""


# ── Vérification et changement ────────────────────────────────────────────────


def verifier_mot_de_passe_decloture(mdp_saisi: str) -> bool:
    """Vérifie le mot de passe de déclôture saisi."""
    if not mdp_saisi:
        return False
    try:
        return _verifier_secret(mdp_saisi, _get_hash_actuel())
    except Exception:
        logger.exception("Erreur lors de la vérification du mot de passe de déclôture")
        return False


def verifier_code_master(code_saisi: str) -> bool:
    """Vérifie le code master de récupération."""
    if not code_saisi:
        return False
    try:
        hash_master = get_parametre(_CODE_MASTER_CLE) or ""
        return _verifier_secret(code_saisi, hash_master)
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
        set_parametre(_MDP_HASH_CLE, _hasher_secret(nouveau_mdp))
        return True, ""
    except Exception as exc:
        logger.exception("Erreur lors du changement de mot de passe")
        return False, str(exc)


def reset_mot_de_passe_via_master(code_master: str) -> tuple[bool, str]:
    """Réinitialise le mot de passe de déclôture via le code master.

    Génère un nouveau mot de passe aléatoire sécurisé.

    Retourne ``(True, nouveau_mdp_clair)`` en cas de succès,
    ``(False, message_erreur)`` en cas d'échec.
    """
    if not verifier_code_master(code_master):
        return False, "Code master incorrect."

    try:
        nouveau_mdp = secrets.token_urlsafe(12)
        set_parametre(_MDP_HASH_CLE, _hasher_secret(nouveau_mdp))
        logger.info("Mot de passe de déclôture réinitialisé via le code master.")
        return True, nouveau_mdp
    except Exception as exc:
        logger.exception("Erreur lors de la réinitialisation du mot de passe")
        return False, str(exc)
