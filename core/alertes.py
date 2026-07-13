"""Alertes tableau de bord (Phase 16).

Ce module agrège les alertes de tous les sous-systèmes et expose
la fonction `get_alertes()` utilisable depuis le tableau de bord.
"""

from __future__ import annotations

from utils.logger import get_logger

logger = get_logger(__name__)


def get_alertes() -> list[dict]:
    """Retourne toutes les alertes actives pour le tableau de bord.

    Délègue à `db.models.dashboard.get_toutes_alertes` qui centralise
    déjà les alertes stock, trésorerie, événements et sauvegarde.
    Les alertes de cotisations (Phase 16) sont ajoutées ici.

    Niveaux possibles : 'rouge', 'orange', 'bleu'.
    Chaque alerte est un dict :
        {niveau, message, module, lien_action}

    Returns:
        Liste d'alertes (vide si tout va bien).
    """
    alertes: list[dict] = []

    try:
        from db.models.dashboard import get_toutes_alertes

        alertes.extend(get_toutes_alertes())
    except Exception as exc:  # noqa: BLE001
        logger.warning("get_alertes – get_toutes_alertes: %s", exc)

    try:
        from core.cotisations import get_alertes_cotisations

        alertes.extend(get_alertes_cotisations())
    except Exception as exc:  # noqa: BLE001
        logger.warning("get_alertes – get_alertes_cotisations: %s", exc)

    return alertes
