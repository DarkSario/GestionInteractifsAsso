"""Vue Tombola (Phase 5b) intégrée à la fiche événement."""

from __future__ import annotations

from tkinter import simpledialog, ttk
from typing import Any

import customtkinter as ctk

from db.models.tombola import (add_carnet, add_lot, enregistrer_gagnant,
                               generer_pv_tirage, get_carnets_evenement,
                               get_lots_evenement, get_stats_tombola)
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
        ctk.CTkButton(
            parent, text="+ Ajouter un carnet", command=self._ajouter_carnet
        ).pack(anchor="w", padx=8, pady=(8, 6))
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
        ctk.CTkButton(parent, text="+ Ajouter un lot", command=self._ajouter_lot).pack(
            anchor="w", padx=8, pady=(8, 6)
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
            self._tree_lots.insert(
                "",
                "end",
                values=(
                    lot.get("numero"),
                    lot.get("description"),
                    self._fmt(float(lot.get("valeur_estimee") or 0)),
                    "Sponsorisé" if lot.get("type_lot") == "sponsorise" else "Acheté",
                    str(lot.get("statut") or "").replace("_", " ").title(),
                ),
            )
        non_attribues = [lot for lot in lots if lot.get("statut") == "en_attente"]
        for lot in non_attribues:
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
        add_lot(self._evenement_id, numero, description, 0, "achete", None, None, None)
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
            if lot.get("statut") == "en_attente"
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
