"""Boîtes de dialogue communes : confirmation, information, erreur."""

from typing import Any

try:
    import customtkinter as ctk
except ModuleNotFoundError:  # pragma: no cover - environnement sans Tk
    class _DummyWidget:
        def __init__(self, *_args, **_kwargs):
            pass

        def pack(self, *_args, **_kwargs):
            pass

        def destroy(self):
            pass

        def grab_set(self):
            pass

        def wait_window(self):
            pass

        def title(self, *_args, **_kwargs):
            pass

        def resizable(self, *_args, **_kwargs):
            pass

        def transient(self, *_args, **_kwargs):
            pass

    class _DummyCTk:
        CTkToplevel = CTkLabel = CTkButton = CTkFrame = _DummyWidget

    ctk = _DummyCTk()

from ui import theme as app_theme


def afficher_succes(parent: Any, titre: str, message: str) -> None:
    """Affiche un message de succès bref (auto-fermant après 2 secondes).

    Args:
        parent: Widget parent (pour le positionnement).
        titre: Titre de la fenêtre.
        message: Corps du message de succès.
    """
    _SuccesDialog(parent, titre, message).show()


def afficher_info(parent: Any, titre: str, message: str) -> None:
    """Affiche une boîte de dialogue d'information.

    Args:
        parent: Widget parent (pour le positionnement).
        titre: Titre de la fenêtre.
        message: Corps du message.
    """
    _Dialog(parent, titre, message, dialog_type="info").show()


def afficher_erreur(parent: Any, titre: str, message: str) -> None:
    """Affiche une boîte de dialogue d'erreur.

    Args:
        parent: Widget parent.
        titre: Titre de la fenêtre.
        message: Corps du message d'erreur.
    """
    _Dialog(parent, titre, message, dialog_type="error").show()


def demander_confirmation(parent: Any, titre: str, message: str) -> bool:
    """Affiche une boîte de dialogue de confirmation (Oui / Non).

    Args:
        parent: Widget parent.
        titre: Titre de la fenêtre.
        message: Question posée à l'utilisateur.

    Returns:
        ``True`` si l'utilisateur a confirmé, ``False`` sinon.
    """
    dialog = _ConfirmDialog(parent, titre, message)
    return dialog.show()


# ── Classes internes ─────────────────────────────────────────────────────────


class _SuccesDialog(ctk.CTkToplevel):
    """Boîte de dialogue de succès auto-fermante (2 secondes)."""

    def __init__(self, parent: Any, titre: str, message: str) -> None:
        super().__init__(parent)
        self.title(titre)
        self.resizable(False, False)
        self.transient(parent)

        fonts = app_theme.FONTS

        ctk.CTkLabel(
            self,
            text=f"✅  {titre}",
            font=fonts.get("subtitle"),
        ).pack(padx=25, pady=(20, 5))

        ctk.CTkLabel(
            self,
            text=message,
            font=fonts.get("normal"),
            wraplength=380,
            justify="left",
        ).pack(padx=25, pady=(0, 15))

        ctk.CTkButton(self, text="Fermer", width=100, command=self.destroy).pack(
            pady=(0, 20)
        )

    def show(self) -> None:
        """Affiche le message de succès et le ferme automatiquement après 2 secondes."""
        self.grab_set()
        try:
            self.after(2000, self.destroy)
        except Exception:
            pass
        self.wait_window()


class _Dialog(ctk.CTkToplevel):
    """Boîte de dialogue générique (info / erreur)."""

    _ICONS = {"info": "ℹ️", "error": "❌"}

    def __init__(
        self,
        parent: Any,
        titre: str,
        message: str,
        dialog_type: str = "info",
    ) -> None:
        super().__init__(parent)
        self.title(titre)
        self.resizable(False, False)
        self.transient(parent)

        fonts = app_theme.FONTS
        icon = self._ICONS.get(dialog_type, "")

        ctk.CTkLabel(
            self,
            text=f"{icon}  {titre}",
            font=fonts.get("subtitle"),
        ).pack(padx=25, pady=(20, 5))

        ctk.CTkLabel(
            self,
            text=message,
            font=fonts.get("normal"),
            wraplength=380,
            justify="left",
        ).pack(padx=25, pady=(0, 15))

        ctk.CTkButton(self, text="Fermer", width=100, command=self.destroy).pack(
            pady=(0, 20)
        )

    def show(self) -> None:
        """Affiche la boîte de dialogue et attend qu'elle soit fermée."""
        self.grab_set()
        self.wait_window()


class _ConfirmDialog(ctk.CTkToplevel):
    """Boîte de dialogue de confirmation (Oui / Non)."""

    def __init__(self, parent: Any, titre: str, message: str) -> None:
        super().__init__(parent)
        self.title(titre)
        self.resizable(False, False)
        self.transient(parent)
        self._result = False

        fonts = app_theme.FONTS

        ctk.CTkLabel(
            self,
            text="⚠️  " + titre,
            font=fonts.get("subtitle"),
        ).pack(padx=25, pady=(20, 5))

        ctk.CTkLabel(
            self,
            text=message,
            font=fonts.get("normal"),
            wraplength=380,
            justify="left",
        ).pack(padx=25, pady=(0, 15))

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(0, 20))

        ctk.CTkButton(
            btn_frame,
            text="Oui",
            width=100,
            command=self._on_yes,
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            btn_frame,
            text="Non",
            width=100,
            fg_color="gray",
            hover_color="#555",
            command=self.destroy,
        ).pack(side="left", padx=10)

    def _on_yes(self) -> None:
        self._result = True
        self.destroy()

    def show(self) -> bool:
        """Affiche la boîte de dialogue et retourne le résultat."""
        self.grab_set()
        self.wait_window()
        return self._result
