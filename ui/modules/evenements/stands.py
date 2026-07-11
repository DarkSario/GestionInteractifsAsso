"""Vue Stands (Phase 5b) intégrée à la fiche événement."""

from __future__ import annotations

try:
    from tkinter import simpledialog, ttk
except ModuleNotFoundError:  # pragma: no cover - environnement sans Tk
    class _SimpleDialog:
        @staticmethod
        def askstring(*_args, **_kwargs):
            return None

    class ttk:  # type: ignore[override]
        Treeview = object

    simpledialog = _SimpleDialog()
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

        def bind(self, *_args, **_kwargs):
            pass

        def winfo_manager(self):
            return ""

    class _DummyCTk:
        CTkFrame = CTkLabel = CTkButton = CTkEntry = CTkOptionMenu = CTkBaseClass = CTkFont = CTkToplevel = _DummyWidget
        StringVar = _DummyVar

    ctk = _DummyCTk()

from db.models.stands import (
    add_attente,
    add_stand,
    finaliser_location_stand,
    get_attente_evenement,
    get_stands_evenement,
    get_stats_stands,
    promouvoir_attente,
    update_stand,
)
from ui.components.dialogs import afficher_info


_TYPES_STAND = {
    "Activité": "benevole",
    "Restauration": "benevole",
    "Exposition": "benevole",
    "Jeux": "benevole",
    "Location": "location",
}
_TYPES_LOCATION = {"Recette": "recette", "Dépense": "depense"}
_STATUTS = ["Prévu", "Confirmé", "Annulé"]


def _parse_float(value: str | float | int | None) -> float:
    try:
        return float(str(value or "0").replace(",", ".").strip() or 0)
    except (TypeError, ValueError):
        return 0.0


def enregistrer_stand_depuis_formulaire(
    evenement_id: int,
    formulaire: dict[str, Any],
    stand_id: int | None = None,
) -> int:
    type_ui = str(formulaire.get("type_ui") or "Activité")
    type_stand = _TYPES_STAND.get(type_ui, "benevole")
    type_location = _TYPES_LOCATION.get(str(formulaire.get("type_location") or "Recette"), "recette")
    responsable = str(formulaire.get("responsable") or "").strip() or None
    telephone = str(formulaire.get("telephone") or "").strip() or None
    emplacement = str(formulaire.get("emplacement") or "").strip() or None
    commentaire = str(formulaire.get("commentaire") or "").strip() or None
    statut = str(formulaire.get("statut") or "confirme").strip().lower().replace("é", "e")
    montant = _parse_float(formulaire.get("montant_location"))

    if stand_id is None:
        return add_stand(
            evenement_id,
            emplacement,
            str(formulaire.get("nom_stand") or "").strip(),
            type_stand,
            None,
            responsable,
            montant,
            type_location,
            0,
            commentaire,
            responsable=responsable,
            telephone=telephone,
            emplacement=emplacement,
        )

    update_stand(
        stand_id,
        nom_stand=str(formulaire.get("nom_stand") or "").strip(),
        type_stand=type_stand,
        responsable_nom_externe=responsable,
        responsable=responsable,
        telephone=telephone,
        emplacement=emplacement,
        numero_emplacement=emplacement,
        montant_location=montant,
        type_location=type_location,
        statut=statut,
        commentaire=commentaire,
    )
    return int(stand_id)


class StandsView(ctk.CTkFrame):
    """Composant UI pour la gestion des stands."""

    def __init__(self, parent: Any, evenement_id: int | None = None) -> None:
        super().__init__(parent)
        self._evenement_id = evenement_id
        self._stand_selectionne: int | None = None
        self._build_ui()
        self.refresh()

    def set_evenement_id(self, evenement_id: int | None) -> None:
        self._evenement_id = evenement_id
        self.refresh()

    def _build_ui(self) -> None:
        contenu = ctk.CTkFrame(self, fg_color="transparent")
        contenu.pack(fill="both", expand=True)

        self._frame_liste = ctk.CTkFrame(contenu, fg_color="transparent")
        self._frame_liste.pack(side="left", fill="both", expand=True)

        actions = ctk.CTkFrame(self._frame_liste, fg_color="transparent")
        actions.pack(fill="x", padx=8, pady=(8, 4))
        ctk.CTkButton(actions, text="+ Ajouter un stand", command=self._ouvrir_formulaire).pack(side="left")
        ctk.CTkButton(actions, text="✏️ Modifier", command=self._modifier_stand).pack(side="left", padx=8)
        self._btn_attente = ctk.CTkButton(actions, text="📋 Liste d'attente (0)", command=self._ouvrir_attente)
        self._btn_attente.pack(side="left", padx=8)

        self._tree = ttk.Treeview(
            self._frame_liste,
            columns=("empl", "nom", "responsable", "telephone", "type", "location"),
            show="headings",
            height=10,
        )
        for col, label, width in [
            ("empl", "Empl.", 110),
            ("nom", "Nom stand", 220),
            ("responsable", "Responsable", 180),
            ("telephone", "Téléphone", 120),
            ("type", "Type", 110),
            ("location", "Loc.", 100),
        ]:
            self._tree.heading(col, text=label)
            self._tree.column(col, width=width, anchor="center")
        self._tree.pack(fill="both", expand=True, padx=8, pady=4)

        self._btn_finaliser = ctk.CTkButton(self._frame_liste, text="💸 Finaliser location sélectionnée", command=self._finaliser_location)
        self._btn_finaliser.pack(anchor="w", padx=8, pady=(4, 0))
        self._tree.bind("<<TreeviewSelect>>", self._on_select_stand)

        self._lbl_stats = ctk.CTkLabel(self._frame_liste, text="Stats : —")
        self._lbl_stats.pack(anchor="w", padx=8, pady=(4, 8))

        self._frame_formulaire = ctk.CTkFrame(contenu, width=360)
        self._frame_formulaire.pack_propagate(False)
        self._build_formulaire()

    def _build_formulaire(self) -> None:
        self._var_nom = ctk.StringVar()
        self._var_type = ctk.StringVar(value="Activité")
        self._var_responsable = ctk.StringVar()
        self._var_telephone = ctk.StringVar()
        self._var_emplacement = ctk.StringVar()
        self._var_type_location = ctk.StringVar(value="Recette")
        self._var_montant = ctk.StringVar(value="0,00")
        self._var_statut = ctk.StringVar(value="Confirmé")
        self._var_commentaire = ctk.StringVar()

        self._titre_formulaire = ctk.CTkLabel(
            self._frame_formulaire,
            text="🎪 Stand",
            font=ctk.CTkFont(size=15, weight="bold"),
        )
        self._titre_formulaire.pack(anchor="w", padx=16, pady=(16, 12))

        def champ(label: str, widget: ctk.CTkBaseClass) -> None:
            bloc = ctk.CTkFrame(self._frame_formulaire, fg_color="transparent")
            bloc.pack(fill="x", padx=16, pady=4)
            ctk.CTkLabel(bloc, text=label).pack(anchor="w")
            widget.pack(fill="x", pady=(4, 0))

        champ("Nom du stand", ctk.CTkEntry(self._frame_formulaire, textvariable=self._var_nom))
        champ("Type", ctk.CTkOptionMenu(self._frame_formulaire, values=list(_TYPES_STAND), variable=self._var_type))
        champ("Responsable", ctk.CTkEntry(self._frame_formulaire, textvariable=self._var_responsable))
        champ("Téléphone", ctk.CTkEntry(self._frame_formulaire, textvariable=self._var_telephone))
        champ("Emplacement", ctk.CTkEntry(self._frame_formulaire, textvariable=self._var_emplacement))
        champ("Type location", ctk.CTkOptionMenu(self._frame_formulaire, values=list(_TYPES_LOCATION), variable=self._var_type_location))
        champ("Montant loc. (€)", ctk.CTkEntry(self._frame_formulaire, textvariable=self._var_montant))
        champ("Statut", ctk.CTkOptionMenu(self._frame_formulaire, values=_STATUTS, variable=self._var_statut))
        champ("Commentaire", ctk.CTkEntry(self._frame_formulaire, textvariable=self._var_commentaire))

        actions = ctk.CTkFrame(self._frame_formulaire, fg_color="transparent")
        actions.pack(fill="x", padx=16, pady=(16, 16))
        ctk.CTkButton(actions, text="Annuler", fg_color="gray", hover_color="#555", command=self._fermer_formulaire).pack(side="left")
        ctk.CTkButton(actions, text="💾 Enregistrer", command=self._enregistrer_stand).pack(side="right")

    def _check_evenement(self) -> bool:
        if self._evenement_id:
            return True
        afficher_info(self, "Information", "Veuillez d'abord sauvegarder l'événement.")
        return False

    def _fmt(self, value: float) -> str:
        return f"{value:,.2f}€".replace(",", " ").replace(".", ",")

    def refresh(self) -> None:
        self._tree.delete(*self._tree.get_children())
        if not self._evenement_id:
            self._lbl_stats.configure(text="Stats : sauvegardez d'abord l'événement")
            self._btn_attente.configure(text="📋 Liste d'attente (0)")
            return

        stands = get_stands_evenement(self._evenement_id)
        for s in stands:
            responsable = s.get("responsable") or s.get("responsable_nom_externe") or " ".join(
                p for p in [s.get("responsable_prenom"), s.get("responsable_nom")] if p
            ).strip()
            self._tree.insert(
                "",
                "end",
                iid=str(s["id"]),
                values=(
                    s.get("emplacement") or s.get("numero_emplacement") or "—",
                    s.get("nom_stand"),
                    responsable or "—",
                    s.get("telephone") or "—",
                    self._format_type_stand(s),
                    self._fmt(float(s.get("montant_location") or 0)) if s.get("type_stand") == "location" else "—",
                ),
            )

        attente = get_attente_evenement(self._evenement_id)
        self._btn_attente.configure(text=f"📋 Liste d'attente ({len(attente)})")

        stats = get_stats_stands(self._evenement_id)
        self._lbl_stats.configure(
            text=(
                "Stats : "
                f"{stats['total']} stands | {stats['benevoles']} bénévoles | "
                f"{stats['locations']} locations | "
                f"{self._fmt(stats['montant_locations'])} recettes | "
                f"{self._fmt(stats['montant_locations_depenses'])} dépenses"
            )
        )
        self._on_select_stand()

    def _ouvrir_formulaire(self, stand: dict[str, Any] | None = None) -> None:
        if not self._check_evenement():
            return
        self._stand_selectionne = int(stand["id"]) if stand else None
        self._titre_formulaire.configure(text="🎪 Modifier le stand" if stand else "🎪 Stand")
        self._var_nom.set(stand.get("nom_stand") or "" if stand else "")
        self._var_type.set("Location" if stand and stand.get("type_stand") == "location" else "Activité")
        self._var_responsable.set(stand.get("responsable") or stand.get("responsable_nom_externe") or "" if stand else "")
        self._var_telephone.set(stand.get("telephone") or "" if stand else "")
        self._var_emplacement.set(stand.get("emplacement") or stand.get("numero_emplacement") or "" if stand else "")
        self._var_type_location.set("Dépense" if stand and stand.get("type_location") == "depense" else "Recette")
        self._var_montant.set(f"{float(stand.get('montant_location') or 0):.2f}".replace(".", ",") if stand else "0,00")
        self._var_statut.set("Confirmé")
        self._var_commentaire.set(stand.get("commentaire") or "" if stand else "")
        if not self._frame_formulaire.winfo_manager():
            self._frame_formulaire.pack(side="right", fill="y", padx=(12, 0))

    def _fermer_formulaire(self) -> None:
        self._stand_selectionne = None
        self._frame_formulaire.pack_forget()

    def _modifier_stand(self) -> None:
        if not self._check_evenement():
            return
        selected = self._tree.selection()
        if not selected:
            afficher_info(self, "Stand", "Sélectionnez un stand à modifier.")
            return
        stand_id = int(selected[0])
        stand = next((s for s in get_stands_evenement(self._evenement_id) if int(s["id"]) == stand_id), None)
        if stand:
            self._ouvrir_formulaire(stand)

    def _enregistrer_stand(self) -> None:
        if not self._check_evenement():
            return
        enregistrer_stand_depuis_formulaire(
            self._evenement_id,
            {
                "nom_stand": self._var_nom.get(),
                "type_ui": self._var_type.get(),
                "responsable": self._var_responsable.get(),
                "telephone": self._var_telephone.get(),
                "emplacement": self._var_emplacement.get(),
                "type_location": self._var_type_location.get(),
                "montant_location": self._var_montant.get(),
                "statut": self._var_statut.get(),
                "commentaire": self._var_commentaire.get(),
            },
            stand_id=self._stand_selectionne,
        )
        self.refresh()
        self._fermer_formulaire()

    def _finaliser_location(self) -> None:
        if not self._check_evenement():
            return
        selected = self._tree.selection()
        if not selected:
            afficher_info(self, "Location", "Sélectionnez un stand de location.")
            return
        try:
            stand_id = int(selected[0])
        except (TypeError, ValueError):
            afficher_info(self, "Location", "Sélection invalide.")
            return
        ok = finaliser_location_stand(stand_id)
        afficher_info(self, "Location", "Location comptabilisée." if ok else "Impossible de finaliser cette location.")
        self.refresh()

    def _on_select_stand(self, _event: Any | None = None) -> None:
        selected = self._tree.selection()
        if not selected:
            self._btn_finaliser.configure(text="💸 Finaliser location sélectionnée")
            return
        valeurs = self._tree.item(selected[0], "values")
        type_txt = str(valeurs[4]) if valeurs else ""
        self._btn_finaliser.configure(
            text="💸 Finaliser la dépense sélectionnée" if "🔴" in type_txt else "💸 Finaliser la recette sélectionnée"
        )

    @staticmethod
    def _format_type_stand(stand: dict) -> str:
        if stand.get("type_stand") == "benevole":
            return "Stand"
        return "🔴 Dépense" if (stand.get("type_location") or "recette") == "depense" else "🟢 Recette"

    def _ouvrir_attente(self) -> None:
        if not self._check_evenement():
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title("📋 Liste d'attente")
        dialog.geometry("520x360")
        dialog.transient(self)

        ctk.CTkButton(dialog, text="+ Inscrire", command=lambda: self._inscrire_attente(dialog)).pack(anchor="w", padx=12, pady=(10, 6))

        tree = ttk.Treeview(dialog, columns=("nom", "contact"), show="headings", height=10)
        tree.heading("nom", text="Nom")
        tree.heading("contact", text="Contact")
        tree.column("nom", width=240)
        tree.column("contact", width=220)
        tree.pack(fill="both", expand=True, padx=12, pady=6)

        for a in get_attente_evenement(self._evenement_id):
            nom = " ".join(p for p in [a.get("nom"), a.get("prenom")] if p)
            tree.insert("", "end", iid=str(a["id"]), values=(nom, a.get("contact") or "—"))

        def promouvoir() -> None:
            selected = tree.selection()
            if not selected:
                return
            promouvoir_attente(int(selected[0]))
            dialog.destroy()
            self.refresh()

        ctk.CTkButton(dialog, text="➡️ Promouvoir vers stand", command=promouvoir).pack(anchor="w", padx=12, pady=(0, 10))

    def _inscrire_attente(self, parent: Any) -> None:
        nom = simpledialog.askstring("Liste d'attente", "Nom :", parent=parent)
        if not nom:
            return
        prenom = simpledialog.askstring("Liste d'attente", "Prénom :", parent=parent)
        contact = simpledialog.askstring("Liste d'attente", "Contact :", parent=parent)
        add_attente(self._evenement_id, nom, prenom, contact, None)
        parent.destroy()
        self._ouvrir_attente()
