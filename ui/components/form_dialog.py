"""Composant de base pour les fenêtres de formulaire popup standardisées."""

from __future__ import annotations

from typing import Any, Callable

try:
    import customtkinter as ctk
except ModuleNotFoundError:  # pragma: no cover - environnement sans Tk
    class _DummyWidget:
        def __init__(self, *_args, **_kwargs):
            pass

        def pack(self, *_args, **_kwargs):
            pass

        def bind(self, *_args, **_kwargs):
            pass

        def update_idletasks(self):
            pass

        def title(self, *_args, **_kwargs):
            pass

        def geometry(self, *_args, **_kwargs):
            pass

        def minsize(self, *_args, **_kwargs):
            pass

        def resizable(self, *_args, **_kwargs):
            pass

        def transient(self, *_args, **_kwargs):
            pass

        def grab_set(self):
            pass

        def focus(self):
            pass

        def destroy(self):
            pass

        def winfo_width(self):
            return 0

        def winfo_height(self):
            return 0

    class _DummyCTk:
        CTkToplevel = _DummyWidget
        CTkFrame = _DummyWidget
        CTkScrollableFrame = _DummyWidget
        CTkButton = _DummyWidget
        CTkLabel = _DummyWidget

    ctk = _DummyCTk()


class FormDialog(ctk.CTkToplevel):
    """Fenêtre popup formulaire standardisée."""

    def __init__(self, parent: Any, titre: str = "Formulaire", largeur: int = 600, hauteur: int = 500):
        super().__init__(parent)
        self.result: dict[str, Any] | None = None
        self.title(titre)
        self.geometry(f"{largeur}x{hauteur}")
        self.minsize(largeur, hauteur)
        self.resizable(True, True)
        self._centrer_sur_parent(parent)
        self.transient(parent)
        self.grab_set()

        self.frame_content = ctk.CTkScrollableFrame(self)
        self.frame_content.pack(fill="both", expand=True, padx=16, pady=(16, 0))

        self._frame_buttons = ctk.CTkFrame(self, fg_color="transparent")
        self._frame_buttons.pack(fill="x", padx=16, pady=12)

        self._btn_annuler = ctk.CTkButton(
            self._frame_buttons,
            text="❌ Annuler",
            fg_color="#6c757d",
            hover_color="#5a6268",
            command=self.destroy,
        )
        self._btn_annuler.pack(side="right", padx=(8, 0))

        self._btn_valider = ctk.CTkButton(
            self._frame_buttons,
            text="💾 Enregistrer",
            command=self._on_valider,
        )
        self._btn_valider.pack(side="right")

        self.bind("<Escape>", lambda _e: self.destroy())
        self.bind("<Return>", self._on_return_pressed)
        self.focus()

    def _on_return_pressed(self, _event: Any) -> None:
        """Valide avec Entrée sauf si le focus est sur un champ texte multiligne."""
        try:
            focus_widget = self.focus_get()
            widget_name = focus_widget.winfo_class().lower() if focus_widget else ""
        except Exception:
            widget_name = ""
        if "text" in widget_name:
            return
        self._on_valider()

    def _centrer_sur_parent(self, parent: Any) -> None:
        """Centre la fenêtre sur la fenêtre parent."""
        self.update_idletasks()
        try:
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            w = self.winfo_width()
            h = self.winfo_height()
            x = px + (pw - w) // 2
            y = py + (ph - h) // 2
            self.geometry(f"+{x}+{y}")
        except Exception:
            pass

    def _on_valider(self) -> None:
        """À surcharger dans les sous-classes.

        Les sous-classes doivent renseigner ``self.result`` puis fermer la fenêtre.
        L'implémentation de base ferme simplement le dialogue.
        """
        self.destroy()

    def ajouter_champ(self, label: str, widget_factory: Callable[..., Any], **kwargs: Any) -> Any:
        """Ajoute un champ label + widget.

        Args:
            label: Libellé du champ affiché au-dessus du widget.
            widget_factory: Classe/factory de widget à instancier.
            **kwargs: Paramètres transmis au widget.

        Returns:
            Le widget créé et ajouté dans ``frame_content``.
        """
        ctk.CTkLabel(self.frame_content, text=label, anchor="w").pack(fill="x", pady=(8, 2))
        widget = widget_factory(self.frame_content, **kwargs)
        widget.pack(fill="x", pady=(0, 4))
        return widget
