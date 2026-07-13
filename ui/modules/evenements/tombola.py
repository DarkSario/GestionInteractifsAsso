"""Vue Tombola (Phase 5b) intégrée à la fiche événement."""

from __future__ import annotations

try:
    from tkinter import simpledialog, ttk
except ModuleNotFoundError:  # pragma: no cover - environnement sans Tk
    class _SimpleDialog:
        @staticmethod
        def askstring(*_args, **_kwargs):
            return None

        @staticmethod
        def askinteger(*_args, **_kwargs):
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

        def insert(self, *_args, **_kwargs):
            pass

        def delete(self, *_args, **_kwargs):
            pass

        def winfo_manager(self):
            return ""

    class _DummyCTk:
        CTkFrame = CTkLabel = CTkButton = CTkEntry = CTkOptionMenu = CTkTextbox = CTkBaseClass = CTkFont = _DummyWidget
        CTkTabview = _DummyWidget
        StringVar = _DummyVar

    ctk = _DummyCTk()

from db.models.membres import get_all_membres
from db.models.tombola import (
    add_carnet,
    add_lot,
    add_participation_solidaire,
    effectuer_tirage_tombola_solidaire,
    enregistrer_gagnant,
    generer_pv_tirage,
    get_config_tombola_evenement,
    get_carnets_evenement,
    get_lots_evenement,
    get_participations_solidaires,
    get_stats_tombola,
    get_total_dons_tombola_solidaire,
    update_config_tombola_evenement,
    update_lot,
)
from ui.components.dialogs import afficher_erreur, afficher_info, afficher_succes, demander_confirmation


_STATUTS_LOT = {
    "Disponible": "disponible",
    "Réservé": "reserve",
    "Gagné": "gagne",
    "Remis": "remis",
}

_PROVENANCES_LOT = {
    "Don externe": "don_externe",
    "Acheté par un membre": "achete_membre",
    "Fourni par l'association": "association",
    "Autre": "autre",
}
_PROVENANCES_LOT_INV = {v: k for k, v in _PROVENANCES_LOT.items()}

_REMBOURSEMENT_STATUTS_LOT = {
    "Non applicable": "non_applicable",
    "En attente": "en_attente",
    "Remboursé": "rembourse",
}
_REMBOURSEMENT_STATUTS_LOT_INV = {v: k for k, v in _REMBOURSEMENT_STATUTS_LOT.items()}


def _label_statut_lot(statut: str | None) -> str:
    for label, code in _STATUTS_LOT.items():
        if code == statut:
            return label
    return "Disponible"


def _parse_float(value: str | float | int | None) -> float:
    try:
        return float(str(value or "0").replace(",", ".").strip() or 0)
    except (TypeError, ValueError):
        return 0.0


def _parse_int(value: str | float | int | None) -> int:
    try:
        return int(float(str(value or "0").replace(",", ".").strip() or 0))
    except (TypeError, ValueError):
        return 0


def enregistrer_lot_depuis_formulaire(
    evenement_id: int,
    formulaire: dict[str, Any],
    lot_id: int | None = None,
) -> int:
    valeur_estimee = _parse_float(formulaire.get("valeur_estimee"))
    valeur_lot = _parse_float(formulaire.get("valeur_lot"))
    # Les lots offerts peuvent être saisis sans valorisation initiale.
    if valeur_lot <= 0:
        valeur_lot = valeur_estimee

    type_provenance = str(formulaire.get("type_provenance") or "association").strip()
    acheteur_membre_id_val = formulaire.get("acheteur_membre_id")
    montant_avance_val = _parse_float(formulaire.get("montant_avance")) or None
    remboursement_statut_val = str(formulaire.get("remboursement_statut") or "non_applicable").strip()

    donnees = {
        "numero": _parse_int(formulaire.get("numero")),
        "description": str(formulaire.get("description") or "").strip(),
        "valeur_estimee": valeur_estimee,
        "valeur_lot": valeur_lot,
        "donateur": str(formulaire.get("donateur") or "").strip() or None,
        "numero_gagnant": str(formulaire.get("numero_gagnant") or "").strip() or None,
        "statut": _STATUTS_LOT.get(str(formulaire.get("statut") or "Disponible"), "disponible"),
        "commentaire": str(formulaire.get("commentaire") or "").strip() or None,
        "type_provenance": type_provenance,
        "acheteur_membre_id": int(acheteur_membre_id_val) if acheteur_membre_id_val else None,
        "montant_avance": montant_avance_val,
        "remboursement_statut": remboursement_statut_val,
        "donateur_externe": str(formulaire.get("donateur_externe") or "").strip() or None,
        "remarque": str(formulaire.get("remarque") or "").strip() or None,
    }
    if lot_id is None:
        return add_lot(
            evenement_id,
            donnees["numero"],
            donnees["description"],
            donnees["valeur_estimee"],
            donnees["valeur_lot"],
            "achete",
            None,
            None,
            donnees["commentaire"],
            donateur=donnees["donateur"],
            type_provenance=donnees["type_provenance"],
            acheteur_membre_id=donnees["acheteur_membre_id"],
            montant_avance=donnees["montant_avance"],
            remboursement_statut=donnees["remboursement_statut"],
            donateur_externe=donnees["donateur_externe"],
            remarque=donnees["remarque"],
        )
    update_lot(lot_id, **donnees)
    return int(lot_id)


def enregistrer_participation_solidaire_depuis_formulaire(
    evenement_id: int,
    formulaire: dict[str, Any],
) -> int:
    return add_participation_solidaire(
        evenement_id,
        str(formulaire.get("nom") or "").strip(),
        str(formulaire.get("prenom") or "").strip(),
        str(formulaire.get("telephone") or "").strip() or None,
        _parse_float(formulaire.get("montant_don")),
        str(formulaire.get("commentaire") or "").strip() or None,
    )


class TombolaView(ctk.CTkFrame):
    """Composant UI pour gérer la tombola d'un événement."""

    def __init__(self, parent: Any, evenement_id: int | None = None) -> None:
        super().__init__(parent)
        self._evenement_id = evenement_id
        self._lot_selectionne: int | None = None
        self._build_ui()
        self.refresh()

    def set_evenement_id(self, evenement_id: int | None) -> None:
        self._evenement_id = evenement_id
        try:
            if self.winfo_exists():
                self.refresh()
        except Exception:
            pass

    def _build_ui(self) -> None:
        self._tabs = ctk.CTkTabview(self)
        self._tabs.pack(fill="both", expand=True, padx=8, pady=8)

        self._tabs.add("🎟️ Carnets")
        self._tabs.add("🏆 Lots")
        self._tabs.add("💝 Solidaire")
        self._tabs.add("🎲 Tirage")

        self._build_tab_carnets(self._tabs.tab("🎟️ Carnets"))
        self._build_tab_lots(self._tabs.tab("🏆 Lots"))
        self._build_tab_solidaire(self._tabs.tab("💝 Solidaire"))
        self._build_tab_tirage(self._tabs.tab("🎲 Tirage"))

    def _build_tab_carnets(self, parent: Any) -> None:
        cfg = ctk.CTkFrame(parent, fg_color="transparent")
        cfg.pack(fill="x", padx=8, pady=(8, 4))
        ctk.CTkLabel(cfg, text="Prix ticket (€)").pack(side="left")
        self._var_prix_ticket = ctk.StringVar(value="0")
        ctk.CTkEntry(cfg, textvariable=self._var_prix_ticket, width=90).pack(side="left", padx=(6, 14))
        ctk.CTkLabel(cfg, text="Prix carnet (€)").pack(side="left")
        self._var_prix_carnet = ctk.StringVar(value="0")
        ctk.CTkEntry(cfg, textvariable=self._var_prix_carnet, width=90).pack(side="left", padx=6)
        ctk.CTkLabel(cfg, text="Tickets / carnet").pack(side="left", padx=(14, 0))
        self._var_tickets_par_carnet = ctk.StringVar(value="5")
        ctk.CTkEntry(cfg, textvariable=self._var_tickets_par_carnet, width=70).pack(side="left", padx=6)
        ctk.CTkButton(cfg, text="💾 Enregistrer", width=120, command=self._sauver_config).pack(side="left", padx=(8, 0))

        ctk.CTkButton(parent, text="+ Ajouter un carnet", command=self._ajouter_carnet).pack(anchor="w", padx=8, pady=(4, 6))
        self._tree_carnets = ttk.Treeview(
            parent,
            columns=("numeros", "prix", "vendeur", "statut", "encaisse"),
            show="headings",
            height=8,
        )
        for col, label, width in [
            ("numeros", "Numéros", 120),
            ("prix", "Prix", 90),
            ("vendeur", "Vendeur", 180),
            ("statut", "Statut", 100),
            ("encaisse", "Encaissé", 100),
        ]:
            self._tree_carnets.heading(col, text=label)
            self._tree_carnets.column(col, width=width, anchor="center")
        self._tree_carnets.pack(fill="both", expand=True, padx=8, pady=4)

        self._lbl_stats = ctk.CTkLabel(parent, text="Stats : —")
        self._lbl_stats.pack(anchor="w", padx=8, pady=(2, 8))

    def _build_tab_lots(self, parent: Any) -> None:
        contenu = ctk.CTkFrame(parent, fg_color="transparent")
        contenu.pack(fill="both", expand=True)

        self._frame_lots_liste = ctk.CTkFrame(contenu, fg_color="transparent")
        self._frame_lots_liste.pack(side="left", fill="both", expand=True)

        actions = ctk.CTkFrame(self._frame_lots_liste, fg_color="transparent")
        actions.pack(fill="x", padx=8, pady=(8, 6))
        ctk.CTkButton(actions, text="+ Ajouter un lot", command=self._ouvrir_formulaire_lot).pack(side="left")
        ctk.CTkButton(actions, text="✏️ Modifier", command=self._modifier_lot).pack(side="left", padx=8)
        self._tree_lots = ttk.Treeview(
            self._frame_lots_liste,
            columns=("numero", "description", "valeur", "provenance", "acheteur", "statut_remboursement"),
            show="headings",
            height=10,
        )
        for col, label, width in [
            ("numero", "N°", 55),
            ("description", "Description", 200),
            ("valeur", "Valeur", 90),
            ("provenance", "Provenance", 130),
            ("acheteur", "Acheteur", 130),
            ("statut_remboursement", "Remboursement", 120),
        ]:
            self._tree_lots.heading(col, text=label)
            self._tree_lots.column(col, width=width, anchor="center")
        self._tree_lots.pack(fill="both", expand=True, padx=8, pady=4)

        self._frame_lot_formulaire = ctk.CTkFrame(contenu, width=360)
        self._frame_lot_formulaire.pack_propagate(False)
        self._build_formulaire_lot()

    def _build_formulaire_lot(self) -> None:
        self._var_numero_lot = ctk.StringVar()
        self._var_description_lot = ctk.StringVar()
        self._var_valeur_lot = ctk.StringVar(value="0,00")
        self._var_donateur_lot = ctk.StringVar()
        self._var_statut_lot = ctk.StringVar(value="Disponible")
        self._var_numero_gagnant_lot = ctk.StringVar()
        self._var_commentaire_lot = ctk.StringVar()
        self._var_provenance_lot = ctk.StringVar(value="Fourni par l'association")
        self._var_acheteur_lot = ctk.StringVar(value="—")
        self._var_montant_avance_lot = ctk.StringVar(value="0,00")
        self._var_remboursement_statut_lot = ctk.StringVar(value="Non applicable")
        self._var_donateur_externe_lot = ctk.StringVar()
        self._var_remarque_lot = ctk.StringVar()
        self._membres_list = get_all_membres()

        self._titre_form_lot = ctk.CTkLabel(
            self._frame_lot_formulaire,
            text="🎁 Lot tombola",
            font=ctk.CTkFont(size=15, weight="bold"),
        )
        self._titre_form_lot.pack(anchor="w", padx=16, pady=(16, 12))

        scroll = ctk.CTkScrollableFrame(self._frame_lot_formulaire, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=8)

        def champ(label: str, widget: ctk.CTkBaseClass) -> ctk.CTkFrame:
            bloc = ctk.CTkFrame(scroll, fg_color="transparent")
            bloc.pack(fill="x", padx=8, pady=4)
            ctk.CTkLabel(bloc, text=label, anchor="w").pack(fill="x")
            widget.pack(fill="x", pady=(2, 0))
            return bloc

        champ("Numéro lot", ctk.CTkEntry(scroll, textvariable=self._var_numero_lot))
        champ("Description *", ctk.CTkEntry(scroll, textvariable=self._var_description_lot))
        champ("Valeur estimée (€)", ctk.CTkEntry(scroll, textvariable=self._var_valeur_lot))
        champ("Statut", ctk.CTkOptionMenu(scroll, values=list(_STATUTS_LOT), variable=self._var_statut_lot))
        champ("Numéro gagnant", ctk.CTkEntry(scroll, textvariable=self._var_numero_gagnant_lot))

        # ── Provenance ──────────────────────────────────────────────
        champ(
            "Type de provenance",
            ctk.CTkOptionMenu(
                scroll,
                values=list(_PROVENANCES_LOT),
                variable=self._var_provenance_lot,
                command=self._on_provenance_change,
            ),
        )

        # Bloc acheteur (visible si "Acheté par un membre")
        self._bloc_acheteur = ctk.CTkFrame(scroll, fg_color="transparent")
        noms_membres = ["—"] + [f"{m['nom']} {m['prenom']}".strip() for m in self._membres_list]
        ctk.CTkLabel(self._bloc_acheteur, text="Acheté par", anchor="w").pack(fill="x", padx=8)
        ctk.CTkOptionMenu(self._bloc_acheteur, values=noms_membres, variable=self._var_acheteur_lot).pack(fill="x", padx=8, pady=(2, 4))
        ctk.CTkLabel(self._bloc_acheteur, text="Montant avancé (€)", anchor="w").pack(fill="x", padx=8)
        ctk.CTkEntry(self._bloc_acheteur, textvariable=self._var_montant_avance_lot).pack(fill="x", padx=8, pady=(2, 4))
        ctk.CTkLabel(self._bloc_acheteur, text="Remboursement", anchor="w").pack(fill="x", padx=8)
        ctk.CTkOptionMenu(self._bloc_acheteur, values=list(_REMBOURSEMENT_STATUTS_LOT), variable=self._var_remboursement_statut_lot).pack(fill="x", padx=8, pady=(2, 4))

        # Bloc donateur externe (visible si "Don externe")
        self._bloc_donateur_ext = ctk.CTkFrame(scroll, fg_color="transparent")
        ctk.CTkLabel(self._bloc_donateur_ext, text="Donateur (nom)", anchor="w").pack(fill="x", padx=8)
        ctk.CTkEntry(self._bloc_donateur_ext, textvariable=self._var_donateur_externe_lot).pack(fill="x", padx=8, pady=(2, 4))

        champ("Remarque", ctk.CTkEntry(scroll, textvariable=self._var_remarque_lot))
        champ("Commentaire", ctk.CTkEntry(scroll, textvariable=self._var_commentaire_lot))

        # Déclencher visibilité initiale
        self._on_provenance_change(self._var_provenance_lot.get())

        actions = ctk.CTkFrame(self._frame_lot_formulaire, fg_color="transparent")
        actions.pack(fill="x", padx=16, pady=(8, 16))
        ctk.CTkButton(actions, text="Annuler", fg_color="gray", hover_color="#555", command=self._fermer_formulaire_lot).pack(side="left")
        ctk.CTkButton(actions, text="💾 Enregistrer", command=self._enregistrer_lot).pack(side="right")

    def _on_provenance_change(self, valeur: str) -> None:
        code = _PROVENANCES_LOT.get(valeur, "association")
        if code == "achete_membre":
            if not self._bloc_acheteur.winfo_manager():
                self._bloc_acheteur.pack(fill="x", padx=8, pady=2)
            self._bloc_donateur_ext.pack_forget()
        elif code == "don_externe":
            self._bloc_acheteur.pack_forget()
            if not self._bloc_donateur_ext.winfo_manager():
                self._bloc_donateur_ext.pack(fill="x", padx=8, pady=2)
        else:
            self._bloc_acheteur.pack_forget()
            self._bloc_donateur_ext.pack_forget()

    def _build_tab_solidaire(self, parent: Any) -> None:
        contenu = ctk.CTkFrame(parent, fg_color="transparent")
        contenu.pack(fill="both", expand=True)

        self._frame_solidaire_liste = ctk.CTkFrame(contenu, fg_color="transparent")
        self._frame_solidaire_liste.pack(side="left", fill="both", expand=True)

        actions = ctk.CTkFrame(self._frame_solidaire_liste, fg_color="transparent")
        actions.pack(fill="x", padx=8, pady=(8, 6))
        ctk.CTkButton(actions, text="+ Ajouter participant", command=self._ouvrir_formulaire_solidaire).pack(side="left")
        ctk.CTkButton(actions, text="🎲 Effectuer le tirage au sort", command=self._tirer_solidaire).pack(side="right")

        self._lbl_stats_solidaire = ctk.CTkLabel(self._frame_solidaire_liste, text="")
        self._lbl_stats_solidaire.pack(anchor="w", padx=8, pady=(0, 8))

        self._tree_solidaire = ttk.Treeview(
            self._frame_solidaire_liste,
            columns=("nom", "prenom", "telephone", "don", "statut"),
            show="headings",
            height=10,
        )
        for col, label, width in [
            ("nom", "Nom", 160),
            ("prenom", "Prénom", 140),
            ("telephone", "Téléphone", 120),
            ("don", "Don", 90),
            ("statut", "Statut", 120),
        ]:
            self._tree_solidaire.heading(col, text=label)
            self._tree_solidaire.column(col, width=width, anchor="center")
        self._tree_solidaire.pack(fill="both", expand=True, padx=8, pady=4)

        self._lbl_gagnant_solidaire = ctk.CTkLabel(self._frame_solidaire_liste, text="Aucun gagnant tiré.")
        self._lbl_gagnant_solidaire.pack(anchor="w", padx=8, pady=(6, 8))

        self._frame_solidaire_formulaire = ctk.CTkFrame(contenu, width=340)
        self._frame_solidaire_formulaire.pack_propagate(False)
        self._build_formulaire_solidaire()

    def _build_formulaire_solidaire(self) -> None:
        self._var_nom_solidaire = ctk.StringVar()
        self._var_prenom_solidaire = ctk.StringVar()
        self._var_telephone_solidaire = ctk.StringVar()
        self._var_don_solidaire = ctk.StringVar(value="0,00")
        self._var_commentaire_solidaire = ctk.StringVar()

        ctk.CTkLabel(
            self._frame_solidaire_formulaire,
            text="💝 Nouvelle participation",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(anchor="w", padx=16, pady=(16, 12))

        def champ(label: str, widget: ctk.CTkBaseClass) -> None:
            bloc = ctk.CTkFrame(self._frame_solidaire_formulaire, fg_color="transparent")
            bloc.pack(fill="x", padx=16, pady=4)
            ctk.CTkLabel(bloc, text=label).pack(anchor="w")
            widget.pack(fill="x", pady=(4, 0))

        champ("Nom", ctk.CTkEntry(self._frame_solidaire_formulaire, textvariable=self._var_nom_solidaire))
        champ("Prénom", ctk.CTkEntry(self._frame_solidaire_formulaire, textvariable=self._var_prenom_solidaire))
        champ("Téléphone", ctk.CTkEntry(self._frame_solidaire_formulaire, textvariable=self._var_telephone_solidaire))
        champ("Montant don (€)", ctk.CTkEntry(self._frame_solidaire_formulaire, textvariable=self._var_don_solidaire))
        champ("Commentaire", ctk.CTkEntry(self._frame_solidaire_formulaire, textvariable=self._var_commentaire_solidaire))

        actions = ctk.CTkFrame(self._frame_solidaire_formulaire, fg_color="transparent")
        actions.pack(fill="x", padx=16, pady=(16, 16))
        ctk.CTkButton(actions, text="Annuler", fg_color="gray", hover_color="#555", command=self._fermer_formulaire_solidaire).pack(side="left")
        ctk.CTkButton(actions, text="💾 Enregistrer", command=self._enregistrer_participation_solidaire).pack(side="right")

    def _build_tab_tirage(self, parent: Any) -> None:
        ctk.CTkButton(parent, text="🎲 Lancer le tirage", command=self._lancer_tirage).pack(anchor="w", padx=8, pady=(8, 6))
        ctk.CTkButton(parent, text="📄 Exporter PV de tirage", command=self._export_pv).pack(anchor="w", padx=8, pady=(0, 8))
        self._txt_tirage = ctk.CTkTextbox(parent, height=260)
        self._txt_tirage.pack(fill="both", expand=True, padx=8, pady=4)

    def _check_evenement(self) -> bool:
        if self._evenement_id:
            return True
        afficher_info(self, "Information", "Veuillez d'abord sauvegarder l'événement.")
        return False

    def _fmt(self, value: float) -> str:
        return f"{value:,.2f}€".replace(",", " ").replace(".", ",")

    def refresh(self) -> None:
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        self._refresh_carnets()
        self._refresh_lots()
        self._refresh_solidaire()

    def _refresh_carnets(self) -> None:
        try:
            if not self._tree_carnets.winfo_exists():
                return
        except Exception:
            return
        self._tree_carnets.delete(*self._tree_carnets.get_children())
        if not self._evenement_id:
            self._lbl_stats.configure(text="Stats : sauvegardez d'abord l'événement")
            return
        config = get_config_tombola_evenement(self._evenement_id)
        self._var_prix_ticket.set(str(config["prix_ticket"]).replace(".", ","))
        self._var_prix_carnet.set(str(config["prix_carnet"]).replace(".", ","))
        self._var_tickets_par_carnet.set(str(config.get("tickets_par_carnet") or 5))

        carnets = get_carnets_evenement(self._evenement_id)
        for c in carnets:
            vendeur = c.get("vendeur_nom_externe") or " ".join(p for p in [c.get("vendeur_prenom"), c.get("vendeur_nom")] if p).strip()
            try:
                numeros = f"{int(c['numero_debut']):03d}-{int(c['numero_fin']):03d}"
            except (TypeError, ValueError):
                numeros = f"{c.get('numero_debut', '—')}-{c.get('numero_fin', '—')}"
            self._tree_carnets.insert(
                "",
                "end",
                values=(
                    numeros,
                    self._fmt(float(c.get("prix_carnet") or 0)),
                    vendeur or "—",
                    str(c.get("statut") or "—").replace("_", " "),
                    self._fmt(float(c.get("montant_encaisse") or 0)),
                ),
            )

        stats = get_stats_tombola(self._evenement_id)
        self._lbl_stats.configure(
            text=(
                "Stats : "
                f"{stats['total_carnets']} billets émis | "
                f"{stats['vendus']} vendus | "
                f"{stats['perdus']} perdus | "
                f"{self._fmt(stats['montant_total'])} encaissés"
            )
        )

    def _refresh_lots(self) -> None:
        try:
            if not self._tree_lots.winfo_exists():
                return
        except Exception:
            return
        self._tree_lots.delete(*self._tree_lots.get_children())
        self._txt_tirage.delete("1.0", "end")
        if not self._evenement_id:
            return

        lots = get_lots_evenement(self._evenement_id)
        for lot in lots:
            valeur_lot = lot.get("valeur_lot") if lot.get("valeur_lot") is not None else lot.get("valeur_estimee")
            provenance_code = lot.get("type_provenance") or "association"
            provenance_label = _PROVENANCES_LOT_INV.get(provenance_code, provenance_code.replace("_", " ").title())
            acheteur = ""
            if provenance_code == "achete_membre":
                nom = (lot.get("acheteur_nom") or "").strip()
                prenom = (lot.get("acheteur_prenom") or "").strip()
                acheteur = f"{nom} {prenom}".strip() or "—"
            elif provenance_code == "don_externe":
                acheteur = lot.get("donateur_externe") or "—"
            remb_code = lot.get("remboursement_statut") or "non_applicable"
            remb_label = _REMBOURSEMENT_STATUTS_LOT_INV.get(remb_code, "—")
            self._tree_lots.insert(
                "",
                "end",
                iid=str(lot["id"]),
                values=(
                    lot.get("numero"),
                    lot.get("description"),
                    self._fmt(float(valeur_lot or 0)),
                    provenance_label,
                    acheteur or "—",
                    remb_label,
                ),
            )
        available_lots = [lot for lot in lots if lot.get("statut") == "disponible"]
        for lot in available_lots:
            self._txt_tirage.insert("end", f"Lot {lot['numero']} — {lot['description']}\n")

    def _refresh_solidaire(self) -> None:
        try:
            if not self._tree_solidaire.winfo_exists():
                return
        except Exception:
            return
        self._tree_solidaire.delete(*self._tree_solidaire.get_children())
        if not self._evenement_id:
            self._lbl_stats_solidaire.configure(text="Sauvegardez d'abord l'événement.")
            self._lbl_gagnant_solidaire.configure(text="Aucun gagnant tiré.")
            return
        participations = get_participations_solidaires(self._evenement_id)
        total = get_total_dons_tombola_solidaire(self._evenement_id)
        self._lbl_stats_solidaire.configure(
            text=f"Total dons collectés : {self._fmt(total)}   |   Nb participants : {len(participations)}"
        )
        gagnant = None
        for participation in participations:
            est_gagnant = int(participation.get("est_gagnant") or 0) == 1
            if est_gagnant:
                gagnant = participation
            self._tree_solidaire.insert(
                "",
                "end",
                iid=str(participation["id"]),
                values=(
                    participation.get("nom") or "",
                    participation.get("prenom") or "",
                    participation.get("telephone") or "—",
                    self._fmt(float(participation.get("montant_don") or 0)),
                    "🏆 Gagnant" if est_gagnant else "Participant",
                ),
            )
        if gagnant:
            self._lbl_gagnant_solidaire.configure(
                text=(
                    f"Gagnant : {gagnant.get('nom', '')} {gagnant.get('prenom', '')}"
                    f" — {gagnant.get('telephone') or 'Sans téléphone'}"
                )
            )
        else:
            self._lbl_gagnant_solidaire.configure(text="Aucun gagnant tiré.")

    def _ouvrir_formulaire_lot(self, lot: dict[str, Any] | None = None) -> None:
        if not self._check_evenement():
            return
        valeur_reference = 0.0
        if lot:
            valeur_reference = float(
                (
                    lot.get("valeur_lot")
                    if lot.get("valeur_lot") is not None
                    else lot.get("valeur_estimee")
                )
                or 0
            )
        self._lot_selectionne = int(lot["id"]) if lot else None
        self._titre_form_lot.configure(text="🎁 Modifier le lot" if lot else "🎁 Lot tombola")
        self._var_numero_lot.set(str(lot.get("numero") or "") if lot else "")
        self._var_description_lot.set(lot.get("description") or "" if lot else "")
        self._var_valeur_lot.set(
            f"{valeur_reference:.2f}".replace(".", ",") if lot else "0,00"
        )
        self._var_donateur_lot.set(lot.get("donateur") or "" if lot else "")
        self._var_statut_lot.set(_label_statut_lot(lot.get("statut")) if lot else "Disponible")
        self._var_numero_gagnant_lot.set(lot.get("numero_gagnant") or "" if lot else "")
        self._var_commentaire_lot.set(lot.get("commentaire") or "" if lot else "")

        # Nouveaux champs provenance
        provenance_code = lot.get("type_provenance") or "association" if lot else "association"
        provenance_label = _PROVENANCES_LOT_INV.get(provenance_code, "Fourni par l'association")
        self._var_provenance_lot.set(provenance_label)

        if lot and lot.get("acheteur_membre_id"):
            nom = (lot.get("acheteur_nom") or "").strip()
            prenom = (lot.get("acheteur_prenom") or "").strip()
            acheteur_label = f"{nom} {prenom}".strip()
            self._var_acheteur_lot.set(acheteur_label if acheteur_label else "—")
        else:
            self._var_acheteur_lot.set("—")

        montant_av = float(lot.get("montant_avance") or 0) if lot else 0.0
        self._var_montant_avance_lot.set(f"{montant_av:.2f}".replace(".", ","))
        remb_code = lot.get("remboursement_statut") or "non_applicable" if lot else "non_applicable"
        self._var_remboursement_statut_lot.set(_REMBOURSEMENT_STATUTS_LOT_INV.get(remb_code, "Non applicable"))
        self._var_donateur_externe_lot.set(lot.get("donateur_externe") or "" if lot else "")
        self._var_remarque_lot.set(lot.get("remarque") or "" if lot else "")

        self._on_provenance_change(self._var_provenance_lot.get())

        if not self._frame_lot_formulaire.winfo_manager():
            self._frame_lot_formulaire.pack(side="right", fill="y", padx=(12, 0))

    def _fermer_formulaire_lot(self) -> None:
        self._lot_selectionne = None
        self._frame_lot_formulaire.pack_forget()

    def _modifier_lot(self) -> None:
        if not self._check_evenement():
            return
        selected = self._tree_lots.selection()
        if not selected:
            afficher_info(self, "Lots", "Sélectionnez un lot à modifier.")
            return
        lot_id = int(selected[0])
        lot = next((item for item in get_lots_evenement(self._evenement_id) if int(item["id"]) == lot_id), None)
        if lot:
            self._ouvrir_formulaire_lot(lot)

    def _enregistrer_lot(self) -> None:
        if not self._check_evenement():
            return

        provenance_label = self._var_provenance_lot.get()
        provenance_code = _PROVENANCES_LOT.get(provenance_label, "association")

        acheteur_membre_id = None
        if provenance_code == "achete_membre":
            acheteur_label = self._var_acheteur_lot.get()
            if acheteur_label and acheteur_label != "—":
                membre = next(
                    (m for m in self._membres_list if f"{m['nom']} {m['prenom']}".strip() == acheteur_label),
                    None,
                )
                acheteur_membre_id = int(membre["id"]) if membre else None

        enregistrer_lot_depuis_formulaire(
            self._evenement_id,
            {
                "numero": self._var_numero_lot.get(),
                "description": self._var_description_lot.get(),
                "valeur_estimee": self._var_valeur_lot.get(),
                "donateur": self._var_donateur_lot.get(),
                "statut": self._var_statut_lot.get(),
                "numero_gagnant": self._var_numero_gagnant_lot.get(),
                "commentaire": self._var_commentaire_lot.get(),
                "type_provenance": provenance_code,
                "acheteur_membre_id": acheteur_membre_id,
                "montant_avance": self._var_montant_avance_lot.get() if provenance_code == "achete_membre" else None,
                "remboursement_statut": (
                    _REMBOURSEMENT_STATUTS_LOT.get(self._var_remboursement_statut_lot.get(), "non_applicable")
                    if provenance_code == "achete_membre"
                    else "non_applicable"
                ),
                "donateur_externe": self._var_donateur_externe_lot.get() if provenance_code == "don_externe" else None,
                "remarque": self._var_remarque_lot.get(),
            },
            lot_id=self._lot_selectionne,
        )
        self._refresh_lots()
        self._fermer_formulaire_lot()
        afficher_succes(self, 'Tombola', 'Le lot a été enregistré avec succès.')

    def _ouvrir_formulaire_solidaire(self) -> None:
        if not self._check_evenement():
            return
        self._var_nom_solidaire.set("")
        self._var_prenom_solidaire.set("")
        self._var_telephone_solidaire.set("")
        self._var_don_solidaire.set("0,00")
        self._var_commentaire_solidaire.set("")
        if not self._frame_solidaire_formulaire.winfo_manager():
            self._frame_solidaire_formulaire.pack(side="right", fill="y", padx=(12, 0))

    def _fermer_formulaire_solidaire(self) -> None:
        self._frame_solidaire_formulaire.pack_forget()

    def _enregistrer_participation_solidaire(self) -> None:
        if not self._check_evenement():
            return
        enregistrer_participation_solidaire_depuis_formulaire(
            self._evenement_id,
            {
                "nom": self._var_nom_solidaire.get(),
                "prenom": self._var_prenom_solidaire.get(),
                "telephone": self._var_telephone_solidaire.get(),
                "montant_don": self._var_don_solidaire.get(),
                "commentaire": self._var_commentaire_solidaire.get(),
            },
        )
        self._refresh_solidaire()
        self._fermer_formulaire_solidaire()

    def _tirer_solidaire(self) -> None:
        if not self._check_evenement():
            return
        if not demander_confirmation(self, "Tombola solidaire", "Effectuer le tirage au sort maintenant ?"):
            return
        gagnant = effectuer_tirage_tombola_solidaire(self._evenement_id)
        if not gagnant:
            afficher_info(self, "Tombola solidaire", "Aucun participant disponible pour le tirage.")
            return
        self._refresh_solidaire()
        afficher_info(
            self,
            "Tombola solidaire",
            f"Gagnant : {gagnant.get('nom', '')} {gagnant.get('prenom', '')} — {gagnant.get('telephone') or 'Sans téléphone'}",
        )

    def _ajouter_carnet(self) -> None:
        if not self._check_evenement():
            return
        debut = simpledialog.askinteger("Nouveau carnet", "Numéro début :", parent=self)
        fin = simpledialog.askinteger("Nouveau carnet", "Numéro fin :", parent=self)
        if debut is None or fin is None:
            return
        add_carnet(self._evenement_id, debut, fin, 0, None, None, None)
        self._refresh_carnets()

    def _lancer_tirage(self) -> None:
        if not self._check_evenement():
            return
        lots = [lot for lot in get_lots_evenement(self._evenement_id) if lot.get("statut") == "disponible"]
        if not lots:
            afficher_info(self, "Tirage", "Aucun lot en attente.")
            return

        for lot in lots:
            numero = simpledialog.askstring(
                "Tirage",
                f"Numéro gagnant pour le lot {lot['numero']} ({lot['description']}) :",
                parent=self,
            )
            if numero:
                ok = enregistrer_gagnant(int(lot["id"]), numero)
                if not ok:
                    afficher_erreur(self, "Tirage", f"Impossible d'enregistrer le gagnant pour le lot {lot['numero']}.")
                    return
        self.refresh()

    def _export_pv(self) -> None:
        if not self._check_evenement():
            return
        data = generer_pv_tirage(self._evenement_id)
        texte = [f"PV Tombola — {data['evenement'].get('nom', '')}", f"Généré le {data['date_generation']}", ""]
        for lot in data["lots"]:
            texte.append(f"Lot {lot['numero']} | {lot['description']} | Gagnant: {lot.get('numero_gagnant') or '—'}")
        self._txt_tirage.delete("1.0", "end")
        self._txt_tirage.insert("1.0", "\n".join(texte))
        afficher_info(self, "PV de tirage", "Le contenu du PV est affiché dans l'onglet Tirage.")

    def _sauver_config(self) -> None:
        if not self._check_evenement():
            return
        try:
            prix_ticket = float(self._var_prix_ticket.get().replace(",", "."))
            prix_carnet = float(self._var_prix_carnet.get().replace(",", "."))
            tickets_par_carnet = int(self._var_tickets_par_carnet.get() or 5)
        except ValueError:
            afficher_erreur(self, "Configuration tombola", "Montants invalides.")
            return
        update_config_tombola_evenement(self._evenement_id, prix_ticket, prix_carnet, tickets_par_carnet=tickets_par_carnet)
        afficher_info(self, "Configuration tombola", "Tarifs tombola enregistrés.")
