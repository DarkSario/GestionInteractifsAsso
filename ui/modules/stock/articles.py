"""Point d'entrée historique vers la vue stock principale définie dans ``liste``.

Cette compatibilité évite de maintenir une seconde vue d'articles distincte.
"""

from ui.modules.stock.liste import ListeStock

__all__ = ["ListeStock"]
