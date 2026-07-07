"""Fenêtre principale de l'application (CustomTkinter)."""

import customtkinter as ctk

from config.settings import APP_NAME, APP_VERSION, ASSOCIATION_NAME
from db.connection import get_db_file, get_connection
from db.migrations.runner import run_migrations
from ui import theme as app_theme
from utils.logger import get_logger

logger = get_logger(__name__)


class MainApp(ctk.CTk):
    """Fenêtre principale de l'application Gestion Interactifs Asso."""

    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("1100x700")
        self.minsize(900, 600)

        # Initialisation de la base de données
        self._init_db()

        # Construction de l'interface
        self._build_menu()
        self._build_home()
        self._build_status_bar()

        logger.info("Fenêtre principale initialisée")

    # ── Base de données ──────────────────────────────────────────────────────

    def _init_db(self) -> None:
        """Initialise la base de données et applique les migrations."""
        try:
            conn = get_connection()
            run_migrations(conn)
            conn.close()
        except Exception as exc:
            logger.error("Erreur d'initialisation de la base de données : %s", exc)

    # ── Menu ─────────────────────────────────────────────────────────────────

    def _build_menu(self) -> None:
        """Construit la barre de menu principale."""
        import tkinter as tk

        menubar = tk.Menu(self)

        # ── Modules ──────────────────────────────────────────────────────────
        menu_modules = tk.Menu(menubar, tearoff=0)
        menu_modules.add_command(label="Adhérents",   command=self._todo)
        menu_modules.add_command(label="Trésorerie",  command=self._todo)
        menu_modules.add_command(label="Événements",  command=self._todo)
        menu_modules.add_command(label="Buvette",     command=self._todo)
        menu_modules.add_command(label="Stock",       command=self._todo)
        menubar.add_cascade(label="Modules", menu=menu_modules)

        # ── Exports ──────────────────────────────────────────────────────────
        menubar.add_command(label="Exports", command=self._todo)

        # ── Tableau de bord ──────────────────────────────────────────────────
        menubar.add_command(label="Tableau de bord", command=self._todo)

        # ── Journal général ───────────────────────────────────────────────────
        menubar.add_command(label="Journal général", command=self._todo)

        # ── Administration ───────────────────────────────────────────────────
        menu_admin = tk.Menu(menubar, tearoff=0)
        menu_admin.add_command(label="Apparence",          command=self._ouvrir_theme_editor)
        menu_admin.add_separator()
        menu_admin.add_command(label="Sauvegarde",         command=self._todo)
        menu_admin.add_command(label="Restauration",       command=self._todo)
        menu_admin.add_separator()
        menu_admin.add_command(label="Clôture d'exercice", command=self._todo)
        menubar.add_cascade(label="Administration", menu=menu_admin)

        # ── Quitter ──────────────────────────────────────────────────────────
        menubar.add_command(label="Quitter", command=self.destroy)

        self.configure(menu=menubar)

    # ── Page d'accueil ───────────────────────────────────────────────────────

    def _build_home(self) -> None:
        """Construit la page d'accueil."""
        fonts = app_theme.FONTS
        colors = app_theme.COLORS

        # Conteneur principal
        self._frame_home = ctk.CTkFrame(self, fg_color="transparent")
        self._frame_home.pack(fill="both", expand=True, padx=30, pady=20)

        # En-tête
        ctk.CTkLabel(
            self._frame_home,
            text=ASSOCIATION_NAME,
            font=fonts.get("title"),
        ).pack(pady=(20, 5))

        ctk.CTkLabel(
            self._frame_home,
            text=f"Exercice en cours : —",
            font=fonts.get("subtitle"),
        ).pack(pady=(0, 30))

        # Grille de boutons modules
        frame_buttons = ctk.CTkFrame(self._frame_home, fg_color="transparent")
        frame_buttons.pack()

        modules = [
            ("👥 Adhérents",      self._todo),
            ("💰 Trésorerie",     self._todo),
            ("📅 Événements",     self._todo),
            ("🍺 Buvette",        self._todo),
            ("📦 Stock",          self._todo),
            ("📊 Tableau de bord", self._todo),
            ("📤 Exports",        self._todo),
            ("📋 Journal général", self._todo),
        ]

        for i, (label, cmd) in enumerate(modules):
            row, col = divmod(i, 4)
            ctk.CTkButton(
                frame_buttons,
                text=label,
                width=200,
                height=60,
                command=cmd,
                fg_color=colors.get("primary", "#1f6aa5"),
                hover_color=colors.get("secondary", "#144870"),
                font=fonts.get("bold"),
            ).grid(row=row, column=col, padx=10, pady=10)

    # ── Barre de statut ──────────────────────────────────────────────────────

    def _build_status_bar(self) -> None:
        """Construit la barre de statut en bas de la fenêtre."""
        self._status_bar = ctk.CTkFrame(self, height=28, corner_radius=0)
        self._status_bar.pack(fill="x", side="bottom")

        db_path = get_db_file()
        self._status_label = ctk.CTkLabel(
            self._status_bar,
            text=f"Base de données : {db_path}",
            font=app_theme.FONTS.get("small"),
            anchor="w",
        )
        self._status_label.pack(side="left", padx=10)

    # ── Actions ──────────────────────────────────────────────────────────────

    def _todo(self) -> None:
        """Placeholder pour les fonctionnalités non encore implémentées."""
        from ui.components.dialogs import afficher_info
        afficher_info(
            self,
            "En construction",
            "Ce module n'est pas encore disponible.\nIl sera implémenté prochainement.",
        )

    def _ouvrir_theme_editor(self) -> None:
        """Ouvre l'éditeur de thème visuel."""
        from ui.modules.administration.theme_editor import ThemeEditor
        editor = ThemeEditor(self)
        editor.grab_set()
        self.wait_window(editor)
        # Recharge le thème et rafraîchit l'interface
        app_theme.load_theme()
        self._refresh_ui()

    def _refresh_ui(self) -> None:
        """Rafraîchit les couleurs et polices de la page d'accueil."""
        # Destruction et reconstruction de la page d'accueil pour appliquer le thème
        self._frame_home.destroy()
        self._status_bar.destroy()
        self._build_home()
        self._build_status_bar()
