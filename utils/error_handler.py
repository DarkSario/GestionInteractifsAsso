"""Décorateur handle_errors pour les méthodes de l'interface graphique."""

import functools
import traceback
from typing import Any, Callable, TypeVar

from utils.logger import get_logger

logger = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def handle_errors(func: F) -> F:
    """Décorateur qui capture toute exception levée dans une méthode UI.

    En cas d'erreur :
    - L'exception est loguée avec sa traceback complète.
    - Une boîte de dialogue d'erreur CustomTkinter est affichée à l'utilisateur.

    Usage::

        class MonModule:
            @handle_errors
            def ouvrir(self):
                ...  # peut lever une exception
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            class_name = args[0].__class__.__name__ if args else "?"
            logger.error(
                "Erreur dans %s.%s : %s\n%s",
                class_name,
                func.__name__,
                exc,
                traceback.format_exc(),
            )
            _show_error_dialog(func.__name__, exc)
            return None

    return wrapper  # type: ignore[return-value]


def _show_error_dialog(func_name: str, exc: Exception) -> None:
    """Affiche une boîte de dialogue d'erreur CustomTkinter.

    Importe customtkinter ici (couche UI) pour ne pas polluer les imports
    des couches core/db qui peuvent être testées sans affichage graphique.
    """
    try:
        import customtkinter as ctk

        dialog = ctk.CTkToplevel()
        dialog.title("Erreur")
        dialog.grab_set()
        dialog.resizable(False, False)

        ctk.CTkLabel(
            dialog,
            text=f"Une erreur est survenue dans « {func_name} » :",
            font=ctk.CTkFont(weight="bold"),
        ).pack(padx=20, pady=(20, 5))

        ctk.CTkLabel(
            dialog,
            text=str(exc),
            wraplength=400,
        ).pack(padx=20, pady=(0, 10))

        ctk.CTkButton(dialog, text="Fermer", command=dialog.destroy).pack(
            pady=(0, 20)
        )
        dialog.wait_window()
    except Exception:
        # Si l'UI n'est pas disponible (tests, CLI), on se contente du log.
        pass
