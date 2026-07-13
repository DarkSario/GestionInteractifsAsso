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

    try:
        from db.models.dons import get_all_dons
        from db.models.remboursements import get_remboursements_en_attente

        nb_remboursements = len(get_remboursements_en_attente())
        if nb_remboursements:
            alertes.append({
                "niveau": "orange",
                "message": f"{nb_remboursements} remboursements de frais en attente",
                "module": "remboursements",
                "lien_action": "remboursements",
            })

        nb_dons = len(get_all_dons({"statut_recu": "en_attente"}))
        if nb_dons:
            alertes.append({
                "niveau": "orange",
                "message": f"{nb_dons} dons sans reçu émis",
                "module": "dons",
                "lien_action": "dons",
            })
    except Exception as exc:  # noqa: BLE001
        logger.warning("get_alertes – phase17: %s", exc)

    return alertes
