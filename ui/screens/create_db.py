"""Formulaire de création d'une nouvelle base de données."""

from datetime import date
from decimal import Decimal
from pathlib import Path
from tkinter import filedialog, ttk

import customtkinter as ctk
from tkcalendar import DateEntry

from db.connection import get_connection, set_db_file
from db.migrations.runner import run_migrations
from ui import theme as app_theme
from ui.components.dialogs import afficher_erreur
from ui.screens.db_helpers import validate_create_database_data
from utils.logger import get_logger

logger = get_logger(__name__)


class CreateDatabaseDialog(ctk.CTkToplevel):
    """Fenêtre modale de création de base."""

    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.result_path: str | None = None

        self.title("Créer une nouvelle base")
        self.geometry("640x520")
        self.resizable(False, False)
        self.transient(parent)
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

        self._build()
        self._after_center_id = self.after(10, self._center_window)

    def _build(self) -> None:
        fonts = app_theme.FONTS

        container = ctk.CTkFrame(self)
        container.pack(fill="both", expand=True, padx=20, pady=20)
        container.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            container,
            text="✨ Créer une nouvelle base",
            font=fonts.get("subtitle"),
        ).grid(row=0, column=0, columnspan=3, padx=20, pady=(20, 15), sticky="w")

        self._nom_asso_entry = self._add_entry(
            container, 1, "Nom de l'association"
        )
        self._exercice_entry = self._add_entry(
            container, 2, "Exercice (ex: 2025-2026)"
        )
        self._date_debut_entry = self._add_date_entry(container, 3, "Date de début")
        self._date_fin_entry = self._add_date_entry(container, 4, "Date de fin")
        self._solde_entry = self._add_entry(
            container, 5, "Solde d'ouverture bancaire (€)"
        )

        ctk.CTkLabel(
            container,
            text="Emplacement du fichier .db",
            font=fonts.get("normal"),
            anchor="w",
        ).grid(row=6, column=0, padx=(20, 10), pady=8, sticky="w")

        self._db_path_entry = ctk.CTkEntry(container)
        self._db_path_entry.grid(row=6, column=1, padx=(0, 10), pady=8, sticky="ew")

        ctk.CTkButton(
            container,
            text="📁",
            width=48,
            command=self._browse_db_path,
        ).grid(row=6, column=2, padx=(0, 20), pady=8)

        buttons = ctk.CTkFrame(container, fg_color="transparent")
        buttons.grid(row=7, column=0, columnspan=3, padx=20, pady=(20, 20), sticky="e")

        ctk.CTkButton(buttons, text="Annuler", command=self._on_cancel).pack(
            side="right", padx=(10, 0)
        )
        ctk.CTkButton(buttons, text="Créer", command=self._on_create).pack(side="right")

    def _add_entry(self, parent, row: int, label: str):
        ctk.CTkLabel(
            parent,
            text=label,
            font=app_theme.FONTS.get("normal"),
            anchor="w",
        ).grid(row=row, column=0, padx=(20, 10), pady=8, sticky="w")

        entry = ctk.CTkEntry(parent)
        entry.grid(row=row, column=1, columnspan=2, padx=(0, 20), pady=8, sticky="ew")
        return entry

    def _add_date_entry(self, parent, row: int, label: str) -> DateEntry:
        ctk.CTkLabel(
            parent,
            text=label,
            font=app_theme.FONTS.get("normal"),
            anchor="w",
        ).grid(row=row, column=0, padx=(20, 10), pady=8, sticky="w")

        self._configure_date_entry_style()
        date_entry = DateEntry(
            parent,
            style="Gia.DateEntry",
            date_pattern="dd/mm/yyyy",
            background=app_theme.COLORS.get("primary", "#1f6aa5"),
            foreground="#ffffff",
            borderwidth=1,
            headersbackground=app_theme.COLORS.get("primary", "#1f6aa5"),
            headersforeground="#ffffff",
        )
        date_entry.grid(row=row, column=1, columnspan=2, padx=(0, 20), pady=8, sticky="ew")
        return date_entry

    def _configure_date_entry_style(self) -> None:
        style = ttk.Style(self)
        is_dark = ctk.get_appearance_mode().lower() == "dark"
        field_background = "#2b2b2b" if is_dark else "#ffffff"
        foreground = "#f5f5f5" if is_dark else "#111111"

        style.configure(
            "Gia.DateEntry",
            fieldbackground=field_background,
            background=field_background,
            foreground=foreground,
            arrowcolor=foreground,
        )

    def _browse_db_path(self) -> None:
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Choisir l'emplacement de la base",
            defaultextension=".db",
            filetypes=[("Bases SQLite", "*.db"), ("Tous les fichiers", "*.*")],
        )
        if path:
            self._db_path_entry.delete(0, "end")
            self._db_path_entry.insert(0, path)

    def _on_create(self) -> None:
        start_date = self._date_debut_entry.get_date()
        end_date = self._date_fin_entry.get_date()
        db_path = self._db_path_entry.get().strip()
        errors = validate_create_database_data(
            nom_asso=self._nom_asso_entry.get(),
            exercice=self._exercice_entry.get(),
            date_debut=start_date,
            date_fin=end_date,
            solde_ouverture=self._solde_entry.get(),
            db_path=db_path,
        )
        if errors:
            afficher_erreur(
                self,
                "Formulaire invalide",
                "Merci de corriger les points suivants :\n\n- "
                + "\n- ".join(errors),
            )
            return

        db_file = Path(db_path)
        solde = float(Decimal(self._solde_entry.get().replace(",", ".")))
        existed_before = db_file.exists()

        try:
            set_db_file(str(db_file))
            run_migrations()
            _save_initial_config(
                nom_asso=self._nom_asso_entry.get().strip(),
                exercice=self._exercice_entry.get().strip(),
                date_debut=start_date,
                date_fin=end_date,
                solde_ouverture=solde,
            )
        except Exception as exc:
            logger.exception("Erreur lors de la création de la base")
            if not existed_before:
                _cleanup_database_files(db_file)
            afficher_erreur(
                self,
                "Création impossible",
                f"Impossible de créer la base de données.\n\nDétail : {exc}",
            )
            return

        self.result_path = str(db_file)
        self.destroy()

    def _on_cancel(self) -> None:
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

    def _center_window(self) -> None:
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = max((self.winfo_screenwidth() - width) // 2, 0)
        y = max((self.winfo_screenheight() - height) // 2, 0)
        self.geometry(f"{width}x{height}+{x}+{y}")
def _save_initial_config(
    *,
    nom_asso: str,
    exercice: str,
    date_debut: date,
    date_fin: date,
    solde_ouverture: float,
) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM config")
        conn.execute(
            """
            INSERT INTO config (
                nom_asso,
                exercice,
                date_debut,
                date_fin,
                solde_ouverture,
                disponible_banque
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                nom_asso,
                exercice,
                date_debut.isoformat(),
                date_fin.isoformat(),
                solde_ouverture,
                solde_ouverture,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _cleanup_database_files(db_file: Path) -> None:
    for suffix in ("", "-wal", "-shm"):
        candidate = Path(f"{db_file}{suffix}")
        if candidate.exists():
            candidate.unlink()
