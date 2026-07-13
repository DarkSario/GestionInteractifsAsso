"""Sous-onglet Dépôt d'espèces du module Trésorerie."""

from __future__ import annotations

from datetime import datetime
try:
    from tkinter import ttk
except ModuleNotFoundError:  # pragma: no cover - environnement sans Tk
    class ttk:  # type: ignore[override]
        Treeview = Scrollbar = object
from typing import Any

try:
    import customtkinter as ctk
except ModuleNotFoundError:  # pragma: no cover - environnement sans Tk
    class _DummyVar:
        def __init__(self, value=None):
            self._value = value

        def get(self):
            return self._value

        def set(self, value):
            self._value = value

    class _DummyWidget:
        def __init__(self, *_args, **_kwargs):
            pass

        def pack(self, *_args, **_kwargs):
            pass

        def pack_forget(self, *_args, **_kwargs):
            pass

        def pack_propagate(self, *_args, **_kwargs):
            pass

        def configure(self, *_args, **_kwargs):
            pass

        def winfo_manager(self):
            return ""

    class _DummyCTk:
        CTkFrame = CTkLabel = CTkButton = CTkEntry = CTkComboBox = CTkOptionMenu = CTkBaseClass = CTkToplevel = _DummyWidget
        StringVar = _DummyVar

    ctk = _DummyCTk()

from db.connection import get_connection
from db.models.tresorerie import add_operation, delete_operation, get_all_comptes, get_operation_by_id, update_operation
from ui import theme as app_theme
from ui.components.dialogs import afficher_erreur, afficher_info, demander_confirmation


_STATUTS_LABELS_DEPOT = {
    "en_attente": "En attente",
    "depose": "Déposé",
    "verifie": "Vérifié",
}
_STATUTS_INV_DEPOT = {
    "En attente": "en_attente",
    "Déposé": "depose",
    "Vérifié": "verifie",
}


def _parse_float(value: str | None) -> float:
    try:
        return float(str(value or "0").replace(",", ".").strip() or 0)
    except (TypeError, ValueError):
        return 0.0


def _parse_commentaire_depot(commentaire: str) -> tuple[str, str, str, str]:
    """Analyse le commentaire structuré et retourne (statut_code, origine, reference, commentaire_pur)."""
    parties = [p.strip() for p in (commentaire or "").split("|")]
    idx = 0
    statut_code = "en_attente"
    if parties and parties[0].startswith("statut_tracabilite:"):
        statut_code = parties[0][len("statut_tracabilite:"):].strip()
        if statut_code not in _STATUTS_LABELS_DEPOT:
            statut_code = "en_attente"
        idx = 1
    origine = ""
    if idx < len(parties) and parties[idx].startswith("Origine:"):
        origine = parties[idx][len("Origine:"):].strip()
        idx += 1
    reference = parties[idx] if idx < len(parties) else ""
    idx += 1
    comment_pur = parties[idx] if idx < len(parties) else ""
    return statut_code, origine, reference, comment_pur


def _get_depots() -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT o.id, o.date_operation, b.nom AS compte_nom, o.montant, o.commentaire
            FROM tresorerie_operations o
            LEFT JOIN comptes_bancaires b ON b.id = o.compte_id
            WHERE o.source_module = 'depot_especes'
            ORDER BY o.date_operation DESC, o.id DESC
            """
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


class _FormulaireDepotPopup(ctk.CTkToplevel):
    """Fenêtre popup pour créer ou modifier un dépôt d'espèces."""

    def __init__(
        self,
        parent: Any,
        comptes: list,
        depot_id: int | None = None,
        on_enregistre=None,
    ) -> None:
        super().__init__(parent)
        self.title("✏️ Modifier le dépôt" if depot_id else "💵 Nouveau dépôt d'espèces")
        self.geometry("500x520")
        self.minsize(480, 500)
        self.transient(parent)
        self.grab_set()
        self.resizable(True, True)

        self._comptes = comptes
        self._depot_id = depot_id
        self._on_enregistre = on_enregistre

        self._var_date = ctk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        self._var_montant = ctk.StringVar(value="0")
        labels_comptes = [c["nom"] for c in comptes] or ["Compte courant"]
        self._var_compte = ctk.StringVar(value=labels_comptes[0])
        self._var_origine = ctk.StringVar(value="Caisse")
        self._var_reference = ctk.StringVar(value="")
        self._var_statut = ctk.StringVar(value="En attente")
        self._var_commentaire = ctk.StringVar(value="")

        self._build_ui()
        if depot_id:
            self._pre_remplir(depot_id)

    def _build_ui(self) -> None:
        fonts = app_theme.FONTS

        titre_texte = "✏️ Modifier le dépôt" if self._depot_id else "💵 Nouveau dépôt d'espèces"
        ctk.CTkLabel(self, text=titre_texte, font=fonts.get("subtitle")).pack(
            anchor="w", padx=20, pady=(16, 8)
        )

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=16, pady=4)

        labels_comptes = [c["nom"] for c in self._comptes] or ["Compte courant"]

        def champ(label: str, widget: Any) -> None:
            bloc = ctk.CTkFrame(form, fg_color="transparent")
            bloc.pack(fill="x", pady=4)
            ctk.CTkLabel(bloc, text=label, anchor="w").pack(fill="x")
            widget.pack(fill="x", pady=(2, 0))

        champ("Date du dépôt (AAAA-MM-JJ)", ctk.CTkEntry(form, textvariable=self._var_date))
        champ("Compte de destination",
              ctk.CTkOptionMenu(form, values=labels_comptes, variable=self._var_compte))
        champ("Montant (EUR)", ctk.CTkEntry(form, textvariable=self._var_montant))
        champ("Origine", ctk.CTkEntry(form, textvariable=self._var_origine))
        champ("Référence (bordereau / ticket)", ctk.CTkEntry(form, textvariable=self._var_reference))
        champ("Statut",
              ctk.CTkOptionMenu(form,
                                values=["En attente", "Déposé", "Vérifié"],
                                variable=self._var_statut))
        champ("Commentaire", ctk.CTkEntry(form, textvariable=self._var_commentaire))

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=20, pady=(8, 16))
        ctk.CTkButton(
            actions, text="❌ Annuler", width=100, fg_color="grey", hover_color="#555", command=self.destroy
        ).pack(side="left")
        ctk.CTkButton(actions, text="💾 Enregistrer", width=150, command=self._enregistrer).pack(side="right")

    def _pre_remplir(self, depot_id: int) -> None:
        operation = get_operation_by_id(depot_id)
        if not operation:
            return
        self._var_date.set(operation.get("date_operation") or "")
        montant = float(operation.get("montant") or 0)
        self._var_montant.set(f"{montant:,.2f}".replace(",", " ").replace(".", ","))
        compte_nom = operation.get("compte_nom") or (self._comptes[0]["nom"] if self._comptes else "")
        self._var_compte.set(compte_nom)
        commentaire = operation.get("commentaire") or ""
        statut_code, origine, reference, comment_pur = _parse_commentaire_depot(commentaire)
        self._var_statut.set(_STATUTS_LABELS_DEPOT.get(statut_code, "En attente"))
        self._var_origine.set(origine or "Caisse")
        self._var_reference.set(reference)
        self._var_commentaire.set(comment_pur)

    def _enregistrer(self) -> None:
        try:
            montant = _parse_float(self._var_montant.get())
        except Exception:
            afficher_erreur(self, "Dépôt espèces", "Montant invalide.")
            return
        compte = next((c for c in self._comptes if c["nom"] == self._var_compte.get()), self._comptes[0] if self._comptes else None)
        if not compte:
            afficher_erreur(self, "Dépôt espèces", "Compte invalide.")
            return

        statut_code = _STATUTS_INV_DEPOT.get(self._var_statut.get(), "en_attente")
        # Le statut de traçabilité est encodé dans le commentaire.
        # Le statut DB reste 'annule' pour ne pas comptabiliser dans le solde.
        comment_parts = [
            f"statut_tracabilite:{statut_code}",
            f"Origine: {self._var_origine.get().strip()}",
            self._var_reference.get().strip(),
            self._var_commentaire.get().strip(),
        ]
        commentaire = " | ".join(part for part in comment_parts if part)

        try:
            if self._depot_id is not None:
                # Ne PAS modifier le statut DB (doit rester 'annule').
                # Seuls montant, date, compte et commentaire sont mis à jour.
                update_operation(
                    self._depot_id,
                    montant=montant,
                    date_operation=self._var_date.get().strip(),
                    compte_id=int(compte["id"]),
                    commentaire=commentaire or None,
                )
            else:
                # statut='annule' : enregistrement de traçabilité bancaire uniquement,
                # non comptabilisé dans le solde.
                add_operation(
                    compte_id=int(compte["id"]),
                    type_operation="recette",
                    libelle="Dépôt d'espèces",
                    montant=montant,
                    date_operation=self._var_date.get().strip(),
                    categorie_id=None,
                    mode_paiement="especes",
                    numero_facture=self._var_reference.get().strip() or None,
                    evenement_id=None,
                    fournisseur_id=None,
                    statut="annule",
                    est_automatique=0,
                    source_module="depot_especes",
                    source_id=None,
                    commentaire=commentaire or None,
                )
        except Exception as exc:
            afficher_erreur(self, "Dépôt espèces", str(exc))
            return

        if self._on_enregistre:
            self._on_enregistre()
        self.destroy()


class _DepotEspecesTab(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkFrame, root: Any) -> None:
        super().__init__(parent)
        self._tresorerie_root = root
        self._comptes = get_all_comptes(actif_only=True)
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        fonts = app_theme.FONTS
        colors = app_theme.COLORS

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(10, 6))
        ctk.CTkLabel(header, text="💵 Dépôt d'espèces", font=fonts.get("subtitle")).pack(side="left")

        ctk.CTkButton(
            header,
            text="+ Nouveau dépôt",
            width=150,
            fg_color=colors.get("primary", "#1f6aa5"),
            hover_color=colors.get("secondary", "#144870"),
            command=self._ouvrir_formulaire,
        ).pack(side="right")
        ctk.CTkButton(
            header,
            text="🗑️ Supprimer",
            width=110,
            fg_color="#b71c1c",
            hover_color="#7f0000",
            command=self._supprimer,
        ).pack(side="right", padx=(0, 8))
        ctk.CTkButton(
            header,
            text="✏️ Modifier",
            width=110,
            fg_color="gray",
            hover_color="#555",
            command=self._modifier,
        ).pack(side="right", padx=(0, 8))
        ctk.CTkButton(
            header,
            text="🔄 Actualiser",
            width=120,
            fg_color="gray",
            hover_color="#555",
            command=self.refresh,
        ).pack(side="right", padx=(0, 8))

        frame_table = ctk.CTkFrame(self)
        frame_table.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        self._tree = ttk.Treeview(
            frame_table,
            columns=("date", "compte", "montant", "origine", "reference", "statut", "commentaire"),
            show="headings",
            height=10,
        )
        for col, label, width, anchor in [
            ("date", "Date", 100, "center"),
            ("compte", "Compte", 160, "w"),
            ("montant", "Montant", 100, "e"),
            ("origine", "Origine", 150, "w"),
            ("reference", "Référence", 120, "w"),
            ("statut", "Statut", 90, "center"),
            ("commentaire", "Commentaire", 200, "w"),
        ]:
            self._tree.heading(col, text=label)
            self._tree.column(col, width=width, anchor=anchor)

        # Couleurs par statut de traçabilité
        self._tree.tag_configure("en_attente", foreground="#e67e22")
        self._tree.tag_configure("depose", foreground="#2980b9")
        self._tree.tag_configure("verifie", foreground="#27ae60")

        self._tree.pack(fill="both", expand=True, side="left")
        scrollbar = ttk.Scrollbar(frame_table, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        self._tree.bind("<Double-1>", lambda _e: self._modifier())

    def _ouvrir_formulaire(self, depot_id: int | None = None) -> None:
        if not self._comptes:
            afficher_info(self, "Dépôt espèces", "Créez d'abord un compte actif.")
            return
        popup = _FormulaireDepotPopup(
            self,
            comptes=self._comptes,
            depot_id=depot_id,
            on_enregistre=self.refresh,
        )
        self.wait_window(popup)

    def _modifier(self) -> None:
        selected = self._tree.selection()
        if not selected:
            afficher_info(self, "Dépôt espèces", "Sélectionnez un dépôt à modifier.")
            return
        try:
            depot_id = int(selected[0])
        except (TypeError, ValueError):
            return
        self._ouvrir_formulaire(depot_id)

    def _supprimer(self) -> None:
        selected = self._tree.selection()
        if not selected:
            afficher_info(self, "Dépôt espèces", "Sélectionnez un dépôt à supprimer.")
            return
        try:
            depot_id = int(selected[0])
        except (TypeError, ValueError):
            return
        if not demander_confirmation(
            self,
            "Supprimer le dépôt",
            "Supprimer définitivement ce dépôt d'espèces ?\nCette action est irréversible.",
        ):
            return
        ok = delete_operation(depot_id)
        if ok:
            self.refresh()
        else:
            afficher_erreur(self, "Dépôt espèces", "Impossible de supprimer ce dépôt.")

    def refresh(self) -> None:
        try:
            if not self.winfo_exists():
                return
            self._tree.delete(*self._tree.get_children())
        except Exception:
            return
        for row in _get_depots():
            commentaire = row.get("commentaire") or ""
            statut_code, origine, reference, comment_pur = _parse_commentaire_depot(commentaire)
            statut_label = _STATUTS_LABELS_DEPOT.get(statut_code, statut_code)
            montant = float(row.get("montant") or 0)
            montant_fmt = f"{int(abs(montant)):,}".replace(",", " ") + f",{round(abs(montant) % 1 * 100):02d} EUR"
            if montant < 0:
                montant_fmt = "-" + montant_fmt
            self._tree.insert(
                "",
                "end",
                iid=str(row.get("id") or ""),
                tags=(statut_code,),
                values=(
                    row.get("date_operation") or "",
                    row.get("compte_nom") or "—",
                    montant_fmt,
                    origine or "—",
                    reference or "—",
                    statut_label,
                    comment_pur or "",
                ),
            )


def build_tab_depot_especes(parent: ctk.CTkFrame, root: Any) -> None:
    for widget in parent.winfo_children():
        widget.destroy()
    tab = _DepotEspecesTab(parent, root)
    tab.pack(fill="both", expand=True)

