"""Fenêtre de gestion des exercices — Clôture (Phase 6b)."""

from __future__ import annotations

from datetime import datetime
from tkinter import ttk
from typing import Any

import customtkinter as ctk

from core.cloture import generer_nom_exercice, verifier_chevauchement, calculer_solde_cloture
from db.models.cloture import (
    add_exercice,
    cloturer_exercice,
    decloturer_exercice,
    get_all_exercices,
    get_exercice_by_id,
    get_log_exercice,
    get_stats_exercice,
    update_exercice,
)
from ui import theme as app_theme
from ui.components.dialogs import afficher_erreur, afficher_info, demander_confirmation


class GestionExercices(ctk.CTkToplevel):
    """Fenêtre principale de gestion des exercices."""

    def __init__(self, parent: Any) -> None:
        super().__init__(parent)
        self.title("📅 Gestion des exercices")
        self.geometry("900x560")
        self.minsize(820, 460)
        self.transient(parent)

        self._exercice_selectionne: dict | None = None
        self._build_ui()
        self._charger_exercices()

    def _build_ui(self) -> None:
        fonts = app_theme.FONTS
        colors = app_theme.COLORS

        # En-tête
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(14, 6))
        ctk.CTkLabel(header, text="📅 Gestion des exercices", font=fonts.get("title")).pack(
            side="left"
        )

        # Bouton Nouvel exercice
        ctk.CTkButton(
            header,
            text="+ Nouvel exercice",
            width=160,
            fg_color=colors.get("primary", "#1f6aa5"),
            hover_color=colors.get("secondary", "#144870"),
            command=self._nouvel_exercice,
        ).pack(side="right")

        # Label explicatif
        ctk.CTkLabel(
            self,
            text=(
                "ℹ️  Un exercice correspond à une année scolaire/associative. "
                "Il sert à filtrer les données par période (comptabilité, événements, membres)."
            ),
            font=fonts.get("small"),
            text_color="gray",
            wraplength=860,
            justify="left",
        ).pack(anchor="w", padx=16, pady=(0, 4))

        # Tableau des exercices
        table_frame = ctk.CTkFrame(self)
        table_frame.pack(fill="both", expand=True, padx=16, pady=6)

        colonnes = ("nom", "type", "periode", "solde_cloture", "statut")
        self._tree = ttk.Treeview(
            table_frame,
            columns=colonnes,
            show="headings",
            height=12,
        )
        self._tree.heading("nom", text="Exercice")
        self._tree.heading("type", text="Type")
        self._tree.heading("periode", text="Période")
        self._tree.heading("solde_cloture", text="Solde clôt.")
        self._tree.heading("statut", text="Statut")

        self._tree.column("nom", width=130)
        self._tree.column("type", width=90, anchor="center")
        self._tree.column("periode", width=180, anchor="center")
        self._tree.column("solde_cloture", width=130, anchor="e")
        self._tree.column("statut", width=120, anchor="center")

        self._tree.tag_configure("cloture", foreground="#888888")
        self._tree.tag_configure("ouvert", foreground="#2e7d32")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)
        self._tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._tree.bind("<<TreeviewSelect>>", self._on_selection)
        self._tree.bind("<Double-1>", self._consulter)

        # Boutons d'action
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=(4, 14))

        self._btn_cloturer = ctk.CTkButton(
            btn_frame,
            text="🔒 Clôturer",
            width=130,
            state="disabled",
            command=self._cloturer,
        )
        self._btn_cloturer.pack(side="left", padx=(0, 8))

        self._btn_decloturer = ctk.CTkButton(
            btn_frame,
            text="🔓 Déclôturer",
            width=130,
            state="disabled",
            fg_color="#e65100",
            hover_color="#bf360c",
            command=self._decloturer,
        )
        self._btn_decloturer.pack(side="left", padx=(0, 8))

        self._btn_modifier = ctk.CTkButton(
            btn_frame,
            text="✏️ Modifier",
            width=130,
            state="disabled",
            fg_color="gray",
            hover_color="#555",
            command=self._modifier_exercice,
        )
        self._btn_modifier.pack(side="left", padx=(0, 8))

        self._btn_consulter = ctk.CTkButton(
            btn_frame,
            text="👁️ Consulter",
            width=130,
            state="disabled",
            command=self._consulter,
        )
        self._btn_consulter.pack(side="left", padx=(0, 8))

        self._btn_log = ctk.CTkButton(
            btn_frame,
            text="📋 Journal",
            width=130,
            state="disabled",
            fg_color="gray",
            hover_color="#555",
            command=self._voir_log,
        )
        self._btn_log.pack(side="left")

    def _charger_exercices(self) -> None:
        """Recharge la liste des exercices dans le tableau."""
        for item in self._tree.get_children():
            self._tree.delete(item)

        exercices = get_all_exercices()
        for ex in exercices:
            periode = (
                f"{self._fmt_date(ex['date_debut'])} → {self._fmt_date(ex['date_fin'])}"
            )
            solde_cloture = (
                self._fmt_montant(float(ex["solde_cloture"]))
                if ex.get("solde_cloture") is not None
                else "—"
            )
            if ex["statut"] == "cloture":
                statut_txt = "🔒 Clôturé"
                tag = "cloture"
            else:
                statut_txt = "🟢 Ouvert"
                tag = "ouvert"

            type_txt = "Scolaire" if ex["type_exercice"] == "scolaire" else "Civile"

            self._tree.insert(
                "",
                "end",
                iid=str(ex["id"]),
                values=(ex["nom"], type_txt, periode, solde_cloture, statut_txt),
                tags=(tag,),
            )

    def _on_selection(self, _event: Any = None) -> None:
        """Met à jour les boutons selon la sélection."""
        sel = self._tree.selection()
        if not sel:
            self._exercice_selectionne = None
            self._btn_cloturer.configure(state="disabled")
            self._btn_decloturer.configure(state="disabled")
            self._btn_modifier.configure(state="disabled")
            self._btn_consulter.configure(state="disabled")
            self._btn_log.configure(state="disabled")
            return

        exercice_id = int(sel[0])
        self._exercice_selectionne = get_exercice_by_id(exercice_id)
        if not self._exercice_selectionne:
            return

        statut = self._exercice_selectionne["statut"]
        self._btn_cloturer.configure(state="normal" if statut == "ouvert" else "disabled")
        self._btn_decloturer.configure(state="normal" if statut == "cloture" else "disabled")
        self._btn_modifier.configure(state="normal" if statut == "ouvert" else "disabled")
        self._btn_consulter.configure(state="normal")
        self._btn_log.configure(state="normal")

    def _nouvel_exercice(self) -> None:
        """Ouvre le dialogue de création d'un exercice."""
        dialog = _DialogNouvelExercice(self)
        dialog.grab_set()
        self.wait_window(dialog)
        if dialog.resultat:
            self._charger_exercices()

    def _modifier_exercice(self) -> None:
        """Ouvre le dialogue de modification d'un exercice ouvert."""
        if not self._exercice_selectionne:
            return
        dialog = _DialogModifierExercice(self, self._exercice_selectionne)
        dialog.grab_set()
        self.wait_window(dialog)
        if dialog.resultat:
            self._charger_exercices()
            self._on_selection()

    def _cloturer(self) -> None:
        """Ouvre le dialogue de clôture."""
        if not self._exercice_selectionne:
            return
        from ui.modules.tresorerie.cloture_dialog import ClotureDialog

        dialog = ClotureDialog(self, self._exercice_selectionne)
        dialog.grab_set()
        self.wait_window(dialog)
        self._charger_exercices()
        self._on_selection()

    def _decloturer(self) -> None:
        """Ouvre le dialogue de déclôture."""
        if not self._exercice_selectionne:
            return
        from ui.modules.tresorerie.decloture_dialog import DeclotureDialog

        dialog = DeclotureDialog(self, self._exercice_selectionne)
        dialog.grab_set()
        self.wait_window(dialog)
        self._charger_exercices()
        self._on_selection()

    def _consulter(self, _event: Any = None) -> None:
        """Ouvre la vue de consultation d'un exercice."""
        if not self._exercice_selectionne:
            sel = self._tree.selection()
            if sel:
                self._exercice_selectionne = get_exercice_by_id(int(sel[0]))
        if not self._exercice_selectionne:
            return
        dialog = _ConsultationExercice(self, self._exercice_selectionne)
        dialog.grab_set()

    def _voir_log(self) -> None:
        """Affiche le journal de clôture/déclôture."""
        if not self._exercice_selectionne:
            return
        dialog = _LogExercice(self, self._exercice_selectionne)
        dialog.grab_set()

    @staticmethod
    def _fmt_date(value: str) -> str:
        try:
            return datetime.strptime(value, "%Y-%m-%d").strftime("%d/%m/%Y")
        except (ValueError, TypeError):
            return str(value) if value else "—"

    @staticmethod
    def _fmt_montant(value: float) -> str:
        return f"{value:,.2f} €".replace(",", " ").replace(".", ",")


# ── Dialogue Nouvel exercice ─────────────────────────────────────────────────


class _DialogNouvelExercice(ctk.CTkToplevel):
    """Dialogue de création d'un nouvel exercice."""

    def __init__(self, parent: Any) -> None:
        super().__init__(parent)
        self.title("+ Nouvel exercice")
        self.geometry("480x400")
        self.resizable(False, False)
        self.transient(parent)
        self.resultat = False
        self._build_ui()

    def _build_ui(self) -> None:
        fonts = app_theme.FONTS
        colors = app_theme.COLORS

        ctk.CTkLabel(self, text="Nouvel exercice", font=fonts.get("subtitle")).pack(
            padx=20, pady=(16, 12)
        )

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="x", padx=20)

        # Type
        ctk.CTkLabel(form, text="Type :", font=fonts.get("normal"), anchor="w").grid(
            row=0, column=0, sticky="w", pady=6
        )
        self._type_var = ctk.StringVar(value="scolaire")
        ctk.CTkOptionMenu(
            form,
            values=["scolaire", "civile"],
            variable=self._type_var,
            command=self._maj_nom,
        ).grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=6)

        # Date début
        ctk.CTkLabel(form, text="Date début :", font=fonts.get("normal"), anchor="w").grid(
            row=1, column=0, sticky="w", pady=6
        )
        self._debut_entry = ctk.CTkEntry(form, placeholder_text="AAAA-MM-JJ")
        self._debut_entry.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=6)
        self._debut_entry.bind("<FocusOut>", self._maj_nom)

        # Date fin
        ctk.CTkLabel(form, text="Date fin :", font=fonts.get("normal"), anchor="w").grid(
            row=2, column=0, sticky="w", pady=6
        )
        self._fin_entry = ctk.CTkEntry(form, placeholder_text="AAAA-MM-JJ")
        self._fin_entry.grid(row=2, column=1, sticky="ew", padx=(10, 0), pady=6)

        # Nom
        ctk.CTkLabel(form, text="Nom :", font=fonts.get("normal"), anchor="w").grid(
            row=3, column=0, sticky="w", pady=6
        )
        self._nom_entry = ctk.CTkEntry(form, placeholder_text="Ex : 2025-2026")
        self._nom_entry.grid(row=3, column=1, sticky="ew", padx=(10, 0), pady=6)

        # Solde ouverture
        ctk.CTkLabel(form, text="Solde ouverture :", font=fonts.get("normal"), anchor="w").grid(
            row=4, column=0, sticky="w", pady=6
        )
        self._solde_entry = ctk.CTkEntry(form, placeholder_text="0.00")
        self._solde_entry.grid(row=4, column=1, sticky="ew", padx=(10, 0), pady=6)

        form.grid_columnconfigure(1, weight=1)

        # Boutons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=16)
        ctk.CTkButton(btn_frame, text="Annuler", width=110, fg_color="gray", hover_color="#555",
                      command=self.destroy).pack(side="left", padx=8)
        ctk.CTkButton(btn_frame, text="💾 Créer", width=110,
                      fg_color=colors.get("primary", "#1f6aa5"),
                      hover_color=colors.get("secondary", "#144870"),
                      command=self._creer).pack(side="left", padx=8)

    def _maj_nom(self, _event: Any = None) -> None:
        debut = self._debut_entry.get().strip()
        type_ex = self._type_var.get()
        if debut:
            nom = generer_nom_exercice(type_ex, debut)
            self._nom_entry.delete(0, "end")
            self._nom_entry.insert(0, nom)

    def _creer(self) -> None:
        nom = self._nom_entry.get().strip()
        type_ex = self._type_var.get()
        debut = self._debut_entry.get().strip()
        fin = self._fin_entry.get().strip()
        solde_txt = self._solde_entry.get().strip() or "0"

        erreurs = []
        if not nom:
            erreurs.append("Le nom est obligatoire.")
        if not debut:
            erreurs.append("La date de début est obligatoire.")
        if not fin:
            erreurs.append("La date de fin est obligatoire.")
        try:
            solde = float(solde_txt.replace(",", "."))
        except ValueError:
            erreurs.append("Le solde d'ouverture est invalide.")
            solde = 0.0

        if debut and fin:
            if verifier_chevauchement(debut, fin, type_ex):
                erreurs.append(
                    "Cet exercice chevauche un exercice existant du même type."
                )

        if erreurs:
            afficher_erreur(self, "Erreur de saisie", "\n".join(erreurs))
            return

        add_exercice(nom, type_ex, debut, fin, solde, None)
        self.resultat = True
        self.destroy()


# ── Dialogue Modifier exercice ───────────────────────────────────────────────


class _DialogModifierExercice(ctk.CTkToplevel):
    """Dialogue de modification d'un exercice ouvert."""

    def __init__(self, parent: Any, exercice: dict) -> None:
        super().__init__(parent)
        self.title(f"✏️ Modifier — {exercice.get('nom', '')}")
        self.geometry("480x360")
        self.resizable(False, False)
        self.transient(parent)
        self._exercice = exercice
        self.resultat = False
        self._build_ui()

    def _build_ui(self) -> None:
        fonts = app_theme.FONTS
        colors = app_theme.COLORS

        ctk.CTkLabel(self, text="Modifier l'exercice", font=fonts.get("subtitle")).pack(
            padx=20, pady=(16, 12)
        )

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="x", padx=20)

        ctk.CTkLabel(form, text="Nom :", font=fonts.get("normal"), anchor="w").grid(
            row=0, column=0, sticky="w", pady=6
        )
        self._nom_entry = ctk.CTkEntry(form)
        self._nom_entry.insert(0, self._exercice.get("nom") or "")
        self._nom_entry.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=6)

        ctk.CTkLabel(form, text="Date début :", font=fonts.get("normal"), anchor="w").grid(
            row=1, column=0, sticky="w", pady=6
        )
        self._debut_entry = ctk.CTkEntry(form)
        self._debut_entry.insert(0, self._exercice.get("date_debut") or "")
        self._debut_entry.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=6)

        ctk.CTkLabel(form, text="Date fin :", font=fonts.get("normal"), anchor="w").grid(
            row=2, column=0, sticky="w", pady=6
        )
        self._fin_entry = ctk.CTkEntry(form)
        self._fin_entry.insert(0, self._exercice.get("date_fin") or "")
        self._fin_entry.grid(row=2, column=1, sticky="ew", padx=(10, 0), pady=6)

        ctk.CTkLabel(form, text="Solde ouverture :", font=fonts.get("normal"), anchor="w").grid(
            row=3, column=0, sticky="w", pady=6
        )
        self._solde_entry = ctk.CTkEntry(form)
        self._solde_entry.insert(0, str(self._exercice.get("solde_ouverture") or "0"))
        self._solde_entry.grid(row=3, column=1, sticky="ew", padx=(10, 0), pady=6)

        form.grid_columnconfigure(1, weight=1)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=16)
        ctk.CTkButton(
            btn_frame, text="Annuler", width=110, fg_color="gray", hover_color="#555",
            command=self.destroy,
        ).pack(side="left", padx=8)
        ctk.CTkButton(
            btn_frame, text="💾 Enregistrer", width=130,
            fg_color=colors.get("primary", "#1f6aa5"),
            hover_color=colors.get("secondary", "#144870"),
            command=self._enregistrer,
        ).pack(side="left", padx=8)

    def _enregistrer(self) -> None:
        nom = self._nom_entry.get().strip()
        debut = self._debut_entry.get().strip()
        fin = self._fin_entry.get().strip()
        solde_txt = self._solde_entry.get().strip() or "0"

        erreurs = []
        if not nom:
            erreurs.append("Le nom est obligatoire.")
        if not debut:
            erreurs.append("La date de début est obligatoire.")
        if not fin:
            erreurs.append("La date de fin est obligatoire.")
        try:
            solde = float(solde_txt.replace(",", "."))
        except ValueError:
            erreurs.append("Le solde d'ouverture est invalide.")
            solde = 0.0

        if erreurs:
            afficher_erreur(self, "Erreur de saisie", "\n".join(erreurs))
            return

        ok = update_exercice(
            int(self._exercice["id"]),
            nom=nom,
            date_debut=debut,
            date_fin=fin,
            solde_ouverture=solde,
        )
        if ok:
            self.resultat = True
            self.destroy()
        else:
            afficher_erreur(self, "Erreur", "Impossible de modifier cet exercice (déjà clôturé ?).")



class _ConsultationExercice(ctk.CTkToplevel):
    """Fenêtre de consultation d'un exercice (lecture seule)."""

    def __init__(self, parent: Any, exercice: dict) -> None:
        super().__init__(parent)
        nom = exercice.get("nom", "")
        self.title(f"📊 Exercice {nom}")
        self.geometry("900x580")
        self.transient(parent)
        self._exercice = exercice
        self._build_ui()

    def _build_ui(self) -> None:
        fonts = app_theme.FONTS
        ex = self._exercice
        stats = get_stats_exercice(int(ex["id"]))

        # En-tête
        titre = ex.get("nom", "")
        if ex["statut"] == "cloture" and ex.get("date_cloture"):
            try:
                dc = datetime.strptime(ex["date_cloture"][:10], "%Y-%m-%d").strftime("%d/%m/%Y")
            except Exception:
                dc = ex["date_cloture"][:10]
            titre += f"  (Clôturé le {dc})"
        ctk.CTkLabel(self, text=f"📊 {titre}", font=fonts.get("title")).pack(
            padx=16, pady=(14, 4)
        )

        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.pack(fill="x", padx=20, pady=6)
        periode = (
            f"{self._fmt_date(ex['date_debut'])} → {self._fmt_date(ex['date_fin'])}"
        )
        ctk.CTkLabel(
            info_frame, text=f"Période : {periode}", font=fonts.get("normal")
        ).pack(side="left", padx=(0, 20))
        ctk.CTkLabel(
            info_frame,
            text=f"Solde ouverture : {self._fmt_montant(float(ex.get('solde_ouverture') or 0))}",
            font=fonts.get("normal"),
        ).pack(side="left", padx=(0, 20))
        if ex.get("solde_cloture") is not None:
            ctk.CTkLabel(
                info_frame,
                text=f"Solde clôture : {self._fmt_montant(float(ex['solde_cloture']))}",
                font=fonts.get("normal"),
            ).pack(side="left")

        # Tableau des opérations
        from core.cloture import get_operations_periode

        table_frame = ctk.CTkFrame(self)
        table_frame.pack(fill="both", expand=True, padx=16, pady=6)

        colonnes = ("date", "libelle", "categorie", "montant", "type")
        tree = ttk.Treeview(table_frame, columns=colonnes, show="headings", height=14)
        tree.heading("date", text="Date")
        tree.heading("libelle", text="Libellé")
        tree.heading("categorie", text="Catégorie")
        tree.heading("montant", text="Montant")
        tree.heading("type", text="Type")

        tree.column("date", width=100, anchor="center")
        tree.column("libelle", width=320)
        tree.column("categorie", width=180)
        tree.column("montant", width=120, anchor="e")
        tree.column("type", width=90, anchor="center")

        tree.tag_configure("recette", foreground="#2e7d32")
        tree.tag_configure("depense", foreground="#b71c1c")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        ops = get_operations_periode(ex["date_debut"], ex["date_fin"])
        for op in ops:
            m = float(op.get("montant") or 0)
            type_op = op.get("type_operation", "")
            signe = "+" if type_op == "recette" else "-"
            tree.insert(
                "",
                "end",
                values=(
                    op.get("date_operation", ""),
                    op.get("libelle", ""),
                    op.get("categorie_nom") or "—",
                    f"{signe}{self._fmt_montant(m)}",
                    type_op,
                ),
                tags=(type_op,),
            )

        # Totaux
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=16, pady=(0, 14))
        ctk.CTkLabel(
            footer,
            text=f"Total recettes : {self._fmt_montant(stats['total_recettes'])}",
            font=fonts.get("normal"),
            text_color="#2e7d32",
        ).pack(side="left", padx=(0, 20))
        ctk.CTkLabel(
            footer,
            text=f"Total dépenses : {self._fmt_montant(stats['total_depenses'])}",
            font=fonts.get("normal"),
            text_color="#b71c1c",
        ).pack(side="left")

    @staticmethod
    def _fmt_date(value: str) -> str:
        try:
            return datetime.strptime(value, "%Y-%m-%d").strftime("%d/%m/%Y")
        except (ValueError, TypeError):
            return str(value) if value else "—"

    @staticmethod
    def _fmt_montant(value: float) -> str:
        return f"{value:,.2f} €".replace(",", " ").replace(".", ",")


# ── Journal exercice ─────────────────────────────────────────────────────────


class _LogExercice(ctk.CTkToplevel):
    """Fenêtre d'affichage du journal de clôture/déclôture."""

    def __init__(self, parent: Any, exercice: dict) -> None:
        super().__init__(parent)
        self.title(f"📋 Journal — {exercice.get('nom', '')}")
        self.geometry("600x380")
        self.transient(parent)
        self._exercice = exercice
        self._build_ui()

    def _build_ui(self) -> None:
        fonts = app_theme.FONTS

        ctk.CTkLabel(
            self,
            text=f"📋 Journal de l'exercice {self._exercice.get('nom', '')}",
            font=fonts.get("subtitle"),
        ).pack(padx=16, pady=(14, 8))

        table_frame = ctk.CTkFrame(self)
        table_frame.pack(fill="both", expand=True, padx=16, pady=6)

        colonnes = ("date", "action", "utilisateur", "commentaire")
        tree = ttk.Treeview(table_frame, columns=colonnes, show="headings", height=10)
        tree.heading("date", text="Date")
        tree.heading("action", text="Action")
        tree.heading("utilisateur", text="Utilisateur")
        tree.heading("commentaire", text="Commentaire")

        tree.column("date", width=150, anchor="center")
        tree.column("action", width=100, anchor="center")
        tree.column("utilisateur", width=100, anchor="center")
        tree.column("commentaire", width=220)

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        logs = get_log_exercice(int(self._exercice["id"]))
        for log in logs:
            action = "🔒 Clôture" if log["action"] == "cloture" else "🔓 Déclôture"
            tree.insert(
                "",
                "end",
                values=(
                    log.get("date_action", "")[:16],
                    action,
                    log.get("utilisateur", "admin"),
                    log.get("commentaire") or "—",
                ),
            )

        if not logs:
            ctk.CTkLabel(
                self, text="Aucune action enregistrée.", font=fonts.get("normal")
            ).pack(pady=10)

        ctk.CTkButton(self, text="Fermer", width=100, command=self.destroy).pack(pady=(4, 14))
