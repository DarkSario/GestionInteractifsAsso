"""Écran d'accueil affiché au démarrage de l'application."""

import customtkinter as ctk

from config.settings import APP_NAME, APP_VERSION
from ui import theme as app_theme
from ui.theme import load_theme
from ui.screens.create_db import CreateDatabaseDialog
from ui.screens.open_db import open_existing_database


class WelcomeScreen(ctk.CTk):
    """Fenêtre d'accueil avant ouverture de la fenêtre principale."""

    def __init__(self) -> None:
        super().__init__()          # ← fenêtre racine créée ici
        load_theme()                # ← CTkFont maintenant OK
        self.result_path: str | None = None

        self.title(APP_NAME)
        self.geometry("520x360")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._quit_application)

        self._build()
        self._after_center_id = self.after(10, self._center_window)

    def _build(self) -> None:
        fonts = app_theme.FONTS     # ← FONTS est maintenant rempli

        container = ctk.CTkFrame(self, corner_radius=16)
        container.pack(fill="both", expand=True, padx=24, pady=24)

        ctk.CTkLabel(
            container,
            text=f"🏫 {APP_NAME}",
            font=fonts.get("title"),
        ).pack(pady=(28, 4))

        ctk.CTkLabel(
            container,
            text=f"v{APP_VERSION}",
            font=fonts.get("normal"),
        ).pack(pady=(0, 24))

        ctk.CTkButton(
            container,
            text="📂 Ouvrir une base existante",
            width=320,
            height=54,
            command=self._open_existing_database,
        ).pack(pady=10)

        ctk.CTkButton(
            container,
            text="✨ Créer une nouvelle base",
            width=320,
            height=54,
            command=self._create_database,
        ).pack(pady=10)

    def _open_existing_database(self) -> None:
        db_path = open_existing_database(self)
        if db_path:
            self.result_path = db_path
            self.destroy()

    def _create_database(self) -> None:
        dialog = CreateDatabaseDialog(self)
        dialog.grab_set()
        self.wait_window(dialog)
        if dialog.result_path:
            self.result_path = dialog.result_path
            self.destroy()

    def _quit_application(self) -> None:
        self.result_path = None
        self.destroy()

    def destroy(self) -> None:
        if getattr(self, "_after_center_id", None):
            try:
                self.after_cancel(self._after_center_id)
            except Exception:  # noqa: BLE001
                pass
            self._after_center_id = None
        super().destroy()

    @staticmethod
    def report_callback_exception(exc_type, exc_val, exc_tb) -> None:  # type: ignore[override]
        """Supprime les TclError sur widgets détruits lors de la transition WelcomeScreen → MainApp."""
        import tkinter
        if issubclass(exc_type, tkinter.TclError):
            import logging
            logging.getLogger(__name__).debug(
                "TclError supprimé (widget détruit) : %s", exc_val
            )
            return
        import traceback
        traceback.print_exception(exc_type, exc_val, exc_tb)

    def run(self) -> str | None:
        self.mainloop()
        return self.result_path

    def _center_window(self) -> None:
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = max((self.winfo_screenwidth() - width) // 2, 0)
        y = max((self.winfo_screenheight() - height) // 2, 0)
        self.geometry(f"{width}x{height}+{x}+{y}")
