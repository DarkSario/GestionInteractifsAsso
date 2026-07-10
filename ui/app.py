"""Fenêtre principale de l'application (CustomTkinter)."""

from __future__ import annotations

import threading
from datetime import datetime

import customtkinter as ctk

from config.settings import APP_NAME, APP_VERSION
from db.connection import get_db_file, get_connection, set_db_file
from ui import theme as app_theme
from utils.backup import verifier_sauvegarde_auto
from utils.logger import get_logger

logger = get_logger(__name__)


class MainApp(ctk.CTk):
    """Fenêtre principale de l'application Gestion Interactifs Asso."""

    def __init__(self, db_path: str | None = None) -> None:
        super().__init__()
        if db_path:
            set_db_file(db_path)

        self._config = self._load_config()
        self._dashboard_frame = None
        self._after_sauvegarde_id: str | None = None

        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("1200x800")
        self.minsize(900, 600)

        self._build_menu()
        self._build_dashboard()
        self._build_status_bar()
        self._after_sauvegarde_id = self.after(250, self._demarrer_verification_sauvegarde_auto)

        self.bind("<Control-comma>", lambda e: self._ouvrir_parametres())

        logger.info("Fenêtre principale initialisée")

    def _load_config(self) -> dict[str, str | float]:
        """Charge la configuration métier depuis la table config."""
        default_config: dict[str, str | float] = {
            "nom_asso": "Mon Association",
            "exercice": "—",
            "date_debut": "",
            "date_fin": "",
            "solde_ouverture": 0.0,
        }

        try:
            conn = get_connection()
            try:
                row = conn.execute(
                    """
                    SELECT nom_asso, exercice, date_debut, date_fin, solde_ouverture
                    FROM config
                    ORDER BY id ASC
                    LIMIT 1
                    """
                ).fetchone()
            finally:
                conn.close()
        except Exception as exc:
            logger.error("Impossible de charger la configuration : %s", exc)
            return default_config

        if not row:
            return default_config

        return {
            "nom_asso": row["nom_asso"] or default_config["nom_asso"],
            "exercice": row["exercice"] or default_config["exercice"],
            "date_debut": row["date_debut"] or "",
            "date_fin": row["date_fin"] or "",
            "solde_ouverture": row["solde_ouverture"] or 0.0,
        }

    # ── Menu ─────────────────────────────────────────────────────────────────

    def _build_menu(self) -> None:
        """Construit la barre de menu principale."""
        import tkinter as tk

        menubar = tk.Menu(self)

        menu_fichier = tk.Menu(menubar, tearoff=0)
        menu_fichier.add_command(label="📤 Exporter la base", command=self._ouvrir_export_base)
        menu_fichier.add_command(label="📥 Importer une base", command=self._ouvrir_import_base)
        menu_fichier.add_separator()
        menu_fichier.add_command(label="Quitter", command=self.destroy)
        menubar.add_cascade(label="Fichier", menu=menu_fichier)

        menu_modules = tk.Menu(menubar, tearoff=0)
        menu_modules.add_command(label="Adhérents", command=self._ouvrir_membres)
        menu_modules.add_command(label="Trésorerie", command=self._ouvrir_tresorerie)
        menu_modules.add_command(label="Événements", command=self._ouvrir_evenements)
        menu_modules.add_command(label="Buvette", command=self._ouvrir_buvette)
        menu_modules.add_command(label="Stock", command=self._ouvrir_stock)
        menubar.add_cascade(label="Modules", menu=menu_modules)

        menu_exports = tk.Menu(menubar, tearoff=0)
        menu_exports.add_command(label="📋 Bilan AG", command=self._ouvrir_bilan_ag)
        menubar.add_cascade(label="Exports", menu=menu_exports)
        menubar.add_command(label="🏠 Tableau de bord", command=self._ouvrir_dashboard)
        menubar.add_command(label="Journal général", command=self._todo)

        menu_admin = tk.Menu(menubar, tearoff=0)
        menu_admin.add_command(label="⚙️ Paramètres", command=self._ouvrir_parametres)
        menu_admin.add_separator()
        menu_admin.add_command(label="Référentiels Stock", command=self._ouvrir_referentiels_stock)
        menu_admin.add_separator()
        menu_admin.add_command(label="🖋️ Polices PDF", command=self._ouvrir_polices_pdf)
        menu_admin.add_command(label="Apparence", command=self._ouvrir_theme_editor)
        menu_admin.add_separator()
        menu_admin.add_command(label="💾 Sauvegardes", command=self._ouvrir_sauvegardes)
        menu_admin.add_separator()
        menu_admin.add_command(label="📅 Gestion des exercices", command=self._ouvrir_gestion_exercices)
        menu_admin.add_command(label="🔐 Mot de passe déclôture", command=self._ouvrir_mdp_decloture)
        menubar.add_cascade(label="Administration", menu=menu_admin)

        self.configure(menu=menubar)

    # ── Tableau de bord (page d'accueil) ────────────────────────────────────

    def _build_dashboard(self) -> None:
        """Construit et affiche le tableau de bord comme page d'accueil."""
        from ui.modules.dashboard.dashboard import DashboardFrame

        if self._dashboard_frame is not None:
            try:
                self._dashboard_frame.annuler_actualisation()
                self._dashboard_frame.destroy()
            except Exception:  # noqa: BLE001
                pass

        self._dashboard_frame = DashboardFrame(
            self,
            navigation_callback=self._naviguer,
        )
        self._dashboard_frame.pack(fill="both", expand=True)

    # ── Page d'accueil (conservée pour compatibilité) ─────────────────────────

    def _build_home(self) -> None:
        """Construit la page d'accueil (délègue vers _build_dashboard)."""
        self._build_dashboard()

    # ── Barre de statut ──────────────────────────────────────────────────────

    def _build_status_bar(self) -> None:
        """Construit la barre de statut en bas de la fenêtre."""
        self._status_bar = ctk.CTkFrame(self, height=28, corner_radius=0)
        self._status_bar.pack(fill="x", side="bottom")

        db_path = get_db_file() or "Aucune base sélectionnée"
        self._status_label = ctk.CTkLabel(
            self._status_bar,
            text=f"Base de données : {db_path}",
            font=app_theme.FONTS.get("small"),
            anchor="w",
        )
        self._status_label.pack(side="left", padx=10)

        self._status_balance_label = ctk.CTkLabel(
            self._status_bar,
            text=f"Solde d'ouverture : {self._format_currency(self._config['solde_ouverture'])}",
            font=app_theme.FONTS.get("small"),
            anchor="e",
        )
        self._status_balance_label.pack(side="right", padx=10)

    @staticmethod
    def _verifier_sauvegarde_auto_async() -> None:
        """Lance la vérification de sauvegarde auto avec journalisation."""
        try:
            verifier_sauvegarde_auto()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Erreur thread sauvegarde auto : %s", exc)

    def _demarrer_verification_sauvegarde_auto(self) -> None:
        """Démarre le thread de vérification après initialisation de l'UI."""
        self._after_sauvegarde_id = None
        threading.Thread(target=self._verifier_sauvegarde_auto_async, daemon=True).start()

    # ── Actions ──────────────────────────────────────────────────────────────

    def _todo(self) -> None:
        """Placeholder pour les fonctionnalités non encore implémentées."""
        from ui.components.dialogs import afficher_info

        afficher_info(
            self,
            "En construction",
            "Ce module n'est pas encore disponible.\nIl sera implémenté prochainement.",
        )

    def _ouvrir_dashboard(self) -> None:
        """Reconstruit et affiche le tableau de bord."""
        self._build_dashboard()

    def _naviguer(self, destination: str, extra=None) -> None:
        """Callback de navigation depuis le dashboard vers les modules.

        Args:
            destination: Identifiant du module (ex. 'stock', 'membres').
            extra: Paramètre optionnel (ex. id d'un événement).
        """
        routes = {
            "stock": self._ouvrir_stock,
            "membres": self._ouvrir_membres,
            "tresorerie": self._ouvrir_tresorerie,
            "evenements": self._ouvrir_evenements,
            "buvette": self._ouvrir_buvette,
            "exercices": self._ouvrir_gestion_exercices,
            "parametres": self._ouvrir_parametres,
        }
        action = routes.get(destination)
        if action:
            action()
        elif destination == "evenement" and extra:
            self._ouvrir_evenements()
        elif destination == "sauvegarde":
            self._ouvrir_sauvegardes()

    def _ouvrir_tresorerie(self) -> None:
        """Ouvre la fenêtre de gestion de la trésorerie."""
        from ui.modules.tresorerie.liste import ListeTresorerie

        fenetre = ListeTresorerie(self)
        fenetre.grab_set()

    def _ouvrir_evenements(self) -> None:
        """Ouvre la fenêtre de gestion des événements."""
        from ui.modules.evenements.liste import ListeEvenements

        fenetre = ListeEvenements(self)
        fenetre.grab_set()

    def _ouvrir_membres(self) -> None:
        """Ouvre la fenêtre de gestion des membres."""
        from ui.modules.membres.liste import ListeMembres

        fenetre = ListeMembres(self)
        fenetre.grab_set()

    def _ouvrir_stock(self) -> None:
        """Ouvre la fenêtre de gestion du stock."""
        from ui.modules.stock.liste import ListeStock

        fenetre = ListeStock(self)
        fenetre.grab_set()

    def _ouvrir_buvette(self) -> None:
        """Ouvre la fenêtre de gestion de la buvette."""
        from ui.modules.buvette.liste import ListeBuvette

        fenetre = ListeBuvette(self)
        fenetre.grab_set()

    def _ouvrir_parametres(self) -> None:
        """Ouvre la fenêtre des paramètres globaux de l'application."""
        from ui.modules.administration.parametres import ParametresApp

        fenetre = ParametresApp(self)
        fenetre.grab_set()

    def _ouvrir_sauvegardes(self) -> None:
        """Ouvre la fenêtre de gestion des sauvegardes."""
        from ui.modules.administration.sauvegardes import SauvegardesApp

        fenetre = SauvegardesApp(self)
        fenetre.grab_set()

    def _ouvrir_config_asso(self) -> None:
        """Ouvre le dialogue de configuration des informations de l'association."""
        from ui.modules.evenements.config_asso_dialog import ConfigAssoDialog

        dialog = ConfigAssoDialog(self)
        dialog.grab_set()

    def _ouvrir_referentiels_stock(self) -> None:
        """Ouvre la fenêtre de gestion des référentiels du stock."""
        from ui.modules.stock.referentiels import Referentiels

        fenetre = Referentiels(self)
        fenetre.grab_set()

    def _ouvrir_gestion_exercices(self) -> None:
        """Ouvre la fenêtre de gestion des exercices."""
        from ui.modules.tresorerie.cloture import GestionExercices

        fenetre = GestionExercices(self)
        fenetre.grab_set()



    def _ouvrir_bilan_ag(self) -> None:
        """Ouvre la fenêtre de génération du bilan AG."""
        from ui.modules.exports.bilan_ag import BilanAGDialog

        fenetre = BilanAGDialog(self)
        fenetre.grab_set()

    def _ouvrir_export_base(self) -> None:
        """Ouvre le dialogue d'export de la base."""
        from ui.modules.administration.import_export_dialog import ExportBaseDialog

        dialog = ExportBaseDialog(self)
        dialog.grab_set()

    def _ouvrir_import_base(self) -> None:
        """Ouvre le dialogue d'import de base."""
        from ui.modules.administration.import_export_dialog import ImportBaseDialog

        dialog = ImportBaseDialog(self)
        dialog.grab_set()

    def _ouvrir_polices_pdf(self) -> None:
        """Ouvre la fenêtre de gestion des polices PDF."""
        from ui.modules.administration.polices import GestionPolices

        fenetre = GestionPolices(self)
        fenetre.grab_set()

    def _ouvrir_mdp_decloture(self) -> None:
        """Ouvre la fenêtre de changement du mot de passe de déclôture."""
        from ui.modules.administration.mdp_decloture import MdpDecloture

        fenetre = MdpDecloture(self)
        fenetre.grab_set()

    def _ouvrir_theme_editor(self) -> None:
        """Ouvre l'éditeur de thème visuel."""
        from ui.modules.administration.theme_editor import ThemeEditor

        editor = ThemeEditor(self)
        editor.grab_set()
        self.wait_window(editor)
        app_theme.load_theme()
        self._refresh_ui()

    def _refresh_ui(self) -> None:
        """Rafraîchit l'interface après un changement de thème."""
        self._build_dashboard()
        if hasattr(self, "_status_bar"):
            self._status_bar.destroy()
        self._build_status_bar()

    def _format_period(self) -> str:
        start = self._config.get("date_debut", "")
        end = self._config.get("date_fin", "")
        if not start or not end:
            return "—"
        return f"{self._format_date(str(start))} → {self._format_date(str(end))}"

    @staticmethod
    def _format_date(value: str) -> str:
        try:
            return datetime.strptime(value, "%Y-%m-%d").strftime("%d/%m/%Y")
        except ValueError:
            return value

    @staticmethod
    def _format_currency(value: str | float) -> str:
        try:
            amount = float(value)
        except (TypeError, ValueError):
            amount = 0.0
        return f"{amount:,.2f} €".replace(",", " ").replace(".", ",")

    def destroy(self) -> None:
        """Annule les callbacks planifiés avant destruction de la fenêtre."""
        if self._after_sauvegarde_id:
            try:
                self.after_cancel(self._after_sauvegarde_id)
            except Exception:  # noqa: BLE001
                pass
            self._after_sauvegarde_id = None
        if self._dashboard_frame is not None:
            try:
                self._dashboard_frame.annuler_actualisation()
            except Exception:  # noqa: BLE001
                pass
        super().destroy()
