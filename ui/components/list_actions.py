"""Actions réutilisables pour les listes."""

from typing import Any, Callable


def bind_double_click_to_open(tree: Any, callback: Callable[..., Any]) -> None:
    """Associe l'ouverture de l'élément sélectionné au double-clic."""
    tree.bind("<Double-1>", callback)
