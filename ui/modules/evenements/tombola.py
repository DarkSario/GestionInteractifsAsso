"""Vue Tombola (Phase 5b) intégrée à la fiche événement."""

from __future__ import annotations

from tkinter import simpledialog, ttk
from typing import Any

import customtkinter as ctk

from db.models.tombola import (
    add_carnet,
    add_lot,
    enregistrer_gagnant,
    generer_pv_tirage,
    get_config_tombola_evenement,
    get_carnets_evenement,
    get_lots_evenement,
    get_stats_tombola,
    update_config_tombola_evenement,
    update_lot,
)
from ui.components.dialogs import afficher_erreur, afficher_info


class TombolaView(ctk.CTkFrame):
    """Composant UI pour gérer la tombola d'un événement."""

    def __init__(self, parent: Any, evenement_id: int | None = None) -> None:
        super().__init__(parent)
        self._evenement_id = evenement_id
        self._build_ui()
        self.refresh()

    def set_evenement_id(self, evenement_id: int | None) -> None:
        self._evenement_id = evenement_id
        self.refresh()

    def _build_ui(self) -> None:
        self._tabs = ctk.CTkTabview(self)
        self._tabs.pack(fill="both", expand=True, padx=8, pady=8)

        self._tabs.add("🎟️ Carnets")
        self._tabs.add("🏆 Lots")
        self._tabs.add("🎲 Tirage")

        self._build_tab_carnets(self._tabs.tab("🎟️ Carnets"))
        self._build_tab_lots(self._tabs.tab("🏆 Lots"))
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

        ctk.CTkButton(
            parent, text="+ Ajouter un carnet", command=self._ajouter_carnet
        ).pack(anchor="w", padx=8, pady=(4, 6))
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
        actions = ctk.CTkFrame(parent, fg_color="transparent")
        actions.pack(fill="x", padx=8, pady=(8, 6))
        ctk.CTkButton(actions, text="+ Ajouter un lot", command=self._ajouter_lot).pack(
            side="left"
        )
        ctk.CTkButton(actions, text="🔁 Modifier statut", command=self._modifier_statut_lot).pack(
            side="left", padx=8
        )
        ctk.CTkButton(actions, text="✏️ Modifier valeur", command=self._modifier_valeur_lot).pack(
            side="left"
        )
        self._tree_lots = ttk.Treeview(
            parent,
            columns=("numero", "description", "valeur", "type", "statut"),
            show="headings",
            height=10,
        )
        for col, label, width in [
            ("numero", "N°", 60),
            ("description", "Description", 320),
            ("valeur", "Valeur", 100),
            ("type", "Type", 120),
            ("statut", "Statut", 120),
        ]:
            self._tree_lots.heading(col, text=label)
            self._tree_lots.column(col, width=width, anchor="center")
        self._tree_lots.pack(fill="both", expand=True, padx=8, pady=4)

    def _build_tab_tirage(self, parent: Any) -> None:
        ctk.CTkButton(
            parent, text="🎲 Lancer le tirage", command=self._lancer_tirage
        ).pack(anchor="w", padx=8, pady=(8, 6))
        ctk.CTkButton(
            parent, text="📄 Exporter PV de tirage", command=self._export_pv
        ).pack(anchor="w", padx=8, pady=(0, 8))
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
        self._refresh_carnets()
        self._refresh_lots()

    def _refresh_carnets(self) -> None:
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
            vendeur = (
                c.get("vendeur_nom_externe")
                or " ".join(
                    p for p in [c.get("vendeur_prenom"), c.get("vendeur_nom")] if p
                ).strip()
            )
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
        self._tree_lots.delete(*self._tree_lots.get_children())
        self._txt_tirage.delete("1.0", "end")
        if not self._evenement_id:
            return

        lots = get_lots_evenement(self._evenement_id)
        for lot in lots:
            valeur_lot = (
                lot.get("valeur_lot")
                if lot.get("valeur_lot") is not None
                else lot.get("valeur_estimee")
            )
            self._tree_lots.insert(
                "",
                "end",
                iid=str(lot["id"]),
                values=(
                    lot.get("numero"),
                    lot.get("description"),
                    self._fmt(float(valeur_lot or 0)),
                    "Sponsorisé" if lot.get("type_lot") == "sponsorise" else "Acheté",
                    str(lot.get("statut") or "").replace("_", " ").title(),
                ),
            )
        available_lots = [lot for lot in lots if lot.get("statut") == "disponible"]
        for lot in available_lots:
            self._txt_tirage.insert(
                "end", f"Lot {lot['numero']} — {lot['description']}\n"
            )

    def _ajouter_lot(self) -> None:
        if not self._check_evenement():
            return
        numero = simpledialog.askinteger("Nouveau lot", "Numéro du lot :", parent=self)
        if not numero:
            return
        description = simpledialog.askstring(
            "Nouveau lot", "Description :", parent=self
        )
        if not description:
            return
        valeur = simpledialog.askstring("Nouveau lot", "Valeur du lot (€) :", parent=self, initialvalue="0")
        try:
            valeur_lot = float((valeur or "0").replace(",", "."))
        except ValueError:
            valeur_lot = 0.0
        add_lot(self._evenement_id, numero, description, valeur_lot, valeur_lot, "achete", None, None, None)
        self._refresh_lots()

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
        lots = [
            lot
            for lot in get_lots_evenement(self._evenement_id)
            if lot.get("statut") == "disponible"
        ]
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
                    afficher_erreur(
                        self,
                        "Tirage",
                        f"Impossible d'enregistrer le gagnant pour le lot {lot['numero']}.",
                    )
                    return
        self.refresh()

    def _export_pv(self) -> None:
        if not self._check_evenement():
            return
        data = generer_pv_tirage(self._evenement_id)
        texte = [
            f"PV Tombola — {data['evenement'].get('nom', '')}",
            f"Généré le {data['date_generation']}",
            "",
        ]
        for lot in data["lots"]:
            texte.append(
                f"Lot {lot['numero']} | {lot['description']} | "
                f"Gagnant: {lot.get('numero_gagnant') or '—'}"
            )
        self._txt_tirage.delete("1.0", "end")
        self._txt_tirage.insert("1.0", "\n".join(texte))
        afficher_info(
            self, "PV de tirage", "Le contenu du PV est affiché dans l'onglet Tirage."
        )

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
        update_config_tombola_evenement(
            self._evenement_id,
            prix_ticket,
            prix_carnet,
            tickets_par_carnet=tickets_par_carnet,
        )
        afficher_info(self, "Configuration tombola", "Tarifs tombola enregistrés.")

    def _modifier_statut_lot(self) -> None:
        if not self._check_evenement():
            return
        selected = self._tree_lots.selection()
        if not selected:
            return
        lot_id = int(selected[0])
        statut = simpledialog.askstring(
            "Modifier statut lot",
            "Nouveau statut (disponible/reserve/gagne/remis) :",
            parent=self,
            initialvalue="disponible",
        )
        statut = (statut or "").strip().lower()
        if statut not in {"disponible", "reserve", "gagne", "remis"}:
            return
        update_lot(lot_id, statut=statut)
        self._refresh_lots()

    def _modifier_valeur_lot(self) -> None:
        if not self._check_evenement():
            return
        selected = self._tree_lots.selection()
        if not selected:
            return
        lot_id = int(selected[0])
        valeur = simpledialog.askstring(
            "Modifier valeur lot",
            "Nouvelle valeur (€) :",
            parent=self,
            initialvalue="0",
        )
        try:
            valeur_float = float((valeur or "0").replace(",", "."))
        except ValueError:
            return
        update_lot(lot_id, valeur_lot=valeur_float, valeur_estimee=valeur_float)
        self._refresh_lots()
