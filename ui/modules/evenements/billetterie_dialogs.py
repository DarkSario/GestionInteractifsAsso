"""Dialogues de billetterie et d'annulation d'une fiche événement."""

from __future__ import annotations

from datetime import date
from typing import Any
import tkinter as tk

import customtkinter as ctk

from core.evenements import (
    calculer_frais_sumup,
    valider_vente,
)
from db.models.evenements import get_parametre
from ui import theme as app_theme
from ui.components.dialogs import afficher_erreur
from ui.modules.evenements.constantes import (
    CANAUX,
    CANAUX_INV,
    MODES_INV,
    MODES_PAIEMENT,
)
from utils.logger import get_logger

logger = get_logger(__name__)


class _DialogTarif(ctk.CTkToplevel):
    """Dialogue de création/édition d'un tarif."""

    def __init__(self, parent: Any, tarif: dict | None = None) -> None:
        super().__init__(parent)
        self.title("Tarif")
        self.geometry("400x280")
        self.resizable(False, False)
        self.transient(parent)
        self.result: dict | None = None

        self._var_nom = tk.StringVar(value=tarif["nom"] if tarif else "")
        self._var_prix = tk.StringVar(
            value=f"{tarif['prix']:.2f}".replace(".", ",") if tarif else "0,00"
        )
        self._var_gratuit = tk.BooleanVar(
            value=bool(tarif["est_gratuit"]) if tarif else False
        )

        self._build()

    def _build(self) -> None:
        ctk.CTkLabel(self, text="Nom du tarif *").pack(
            anchor="w", padx=20, pady=(16, 2)
        )
        ctk.CTkEntry(self, textvariable=self._var_nom, width=320).pack(padx=20)

        ctk.CTkLabel(self, text="Prix (€)").pack(anchor="w", padx=20, pady=(10, 2))
        ctk.CTkEntry(self, textvariable=self._var_prix, width=320).pack(padx=20)

        ctk.CTkCheckBox(self, text="Tarif gratuit", variable=self._var_gratuit).pack(
            anchor="w", padx=20, pady=10
        )

        frame_btn = ctk.CTkFrame(self, fg_color="transparent")
        frame_btn.pack(pady=(6, 16))
        ctk.CTkButton(frame_btn, text="Enregistrer", width=110, command=self._valider).pack(
            side="left", padx=8
        )
        ctk.CTkButton(
            frame_btn,
            text="Annuler",
            width=100,
            fg_color="gray",
            hover_color="#555",
            command=self.destroy,
        ).pack(side="left", padx=8)

    def _valider(self) -> None:
        self.result = {
            "nom": self._var_nom.get().strip(),
            "prix": self._var_prix.get().strip(),
            "est_gratuit": self._var_gratuit.get(),
        }
        self.destroy()

class _DialogVente(ctk.CTkToplevel):
    """Dialogue d'enregistrement d'une vente billetterie."""

    def __init__(self, parent: Any, evenement_id: int, tarifs: list[dict]) -> None:
        super().__init__(parent)
        self.title("Enregistrer une vente")
        self.geometry("560x580")
        self.resizable(False, False)
        self.transient(parent)
        self.result: dict | None = None
        self._tarifs = tarifs
        self._evenement_id = evenement_id

        self._var_date = tk.StringVar(value=date.today().strftime("%Y-%m-%d"))
        self._var_canal = tk.StringVar(value="Sur place")
        self._var_mode = tk.StringVar(value="Espèces")
        self._var_nom_tireur = tk.StringVar()
        self._var_commentaire = tk.StringVar()
        self._qtés: list[tk.StringVar] = []

        self._build()

    def _build(self) -> None:
        fonts = app_theme.FONTS

        scroll = ctk.CTkScrollableFrame(self)
        scroll.pack(fill="both", expand=True, padx=16, pady=10)

        def field(label, widget_fn):
            f = ctk.CTkFrame(scroll, fg_color="transparent")
            f.pack(fill="x", pady=3)
            ctk.CTkLabel(f, text=label, width=160, anchor="e").pack(
                side="left", padx=(0, 8)
            )
            w = widget_fn(f)
            w.pack(side="left")
            return w

        field(
            "Date *", lambda p: ctk.CTkEntry(p, textvariable=self._var_date, width=180)
        )
        field(
            "Canal *",
            lambda p: ctk.CTkOptionMenu(
                p, values=list(CANAUX.values()), variable=self._var_canal, width=180
            ),
        )
        self._combo_mode = field(
            "Mode paiement *",
            lambda p: ctk.CTkOptionMenu(
                p,
                values=list(MODES_PAIEMENT.values()),
                variable=self._var_mode,
                command=self._on_mode_change,
                width=180,
            ),
        )
        self._frame_tireur = ctk.CTkFrame(scroll, fg_color="transparent")
        self._frame_tireur.pack(fill="x", pady=3)
        ctk.CTkLabel(
            self._frame_tireur, text="Nom du tireur", width=160, anchor="e"
        ).pack(side="left", padx=(0, 8))
        ctk.CTkEntry(
            self._frame_tireur, textvariable=self._var_nom_tireur, width=180
        ).pack(side="left")
        self._frame_tireur.pack_forget()

        sep = ctk.CTkFrame(scroll, height=2, fg_color="#444")
        sep.pack(fill="x", pady=6)

        ctk.CTkLabel(scroll, text="Tarifs", font=fonts.get("bold")).pack(
            anchor="w", pady=(0, 4)
        )

        for tarif in self._tarifs:
            var_qte = tk.StringVar(value="0")
            self._qtés.append(var_qte)
            f = ctk.CTkFrame(scroll, fg_color="transparent")
            f.pack(fill="x", pady=2)
            ctk.CTkLabel(
                f,
                text=f"{tarif['nom']}  ({tarif['prix']:.2f} €)",
                width=220,
                anchor="w",
            ).pack(side="left")
            ctk.CTkLabel(f, text="Qté :").pack(side="left", padx=(8, 4))
            ctk.CTkEntry(f, textvariable=var_qte, width=60).pack(side="left")
            var_qte.trace_add("write", self._actualiser_total)

        sep2 = ctk.CTkFrame(scroll, height=2, fg_color="#444")
        sep2.pack(fill="x", pady=6)

        self._lbl_total = ctk.CTkLabel(scroll, text="Montant total : 0,00 €")
        self._lbl_total.pack(anchor="w")
        self._lbl_frais = ctk.CTkLabel(scroll, text="", text_color="#888")
        self._lbl_frais.pack(anchor="w")
        self._lbl_net = ctk.CTkLabel(scroll, text="")
        self._lbl_net.pack(anchor="w")

        sep3 = ctk.CTkFrame(scroll, height=2, fg_color="#444")
        sep3.pack(fill="x", pady=6)

        frame_btn = ctk.CTkFrame(scroll, fg_color="transparent")
        frame_btn.pack(pady=4)
        ctk.CTkButton(
            frame_btn, text="Enregistrer", width=140, command=self._valider
        ).pack(side="left", padx=8)
        ctk.CTkButton(
            frame_btn,
            text="Annuler",
            width=100,
            fg_color="gray",
            hover_color="#555",
            command=self.destroy,
        ).pack(side="left", padx=8)

    def _on_mode_change(self, val: str) -> None:
        if val == "Chèque":
            self._frame_tireur.pack(fill="x", pady=3)
        else:
            self._frame_tireur.pack_forget()
        self._actualiser_total()

    @staticmethod
    def _lire_quantite(var: tk.StringVar) -> int:
        valeur = var.get()
        try:
            return int(valeur)
        except (ValueError, TypeError):
            if valeur not in (None, ""):
                logger.warning("Quantité de billet invalide : %r", valeur)
            return 0

    def _actualiser_total(self, *_) -> None:
        total = 0.0
        for tarif, var in zip(self._tarifs, self._qtés):
            qte = self._lire_quantite(var)
            total += qte * float(tarif["prix"])

        taux_str = get_parametre("taux_sumup") or "1.75"
        taux = float(taux_str)
        mode = MODES_INV.get(self._var_mode.get(), "especes")
        frais = calculer_frais_sumup(total, taux) if mode in {"sumup", "carte"} else 0.0
        net = total - frais

        self._lbl_total.configure(
            text=f"Montant total : {total:,.2f} €".replace(",", " ").replace(".", ",")
        )
        if mode in {"sumup", "carte"}:
            self._lbl_frais.configure(
                text=f"Frais SumUp ({taux}%) : {frais:,.2f} €".replace(
                    ",", " "
                ).replace(".", ",")
            )
        else:
            self._lbl_frais.configure(text="")
        self._lbl_net.configure(
            text=f"Montant net : {net:,.2f} €".replace(",", " ").replace(".", ",")
        )

    def _valider(self) -> None:
        lignes = []
        for tarif, var in zip(self._tarifs, self._qtés):
            qte = self._lire_quantite(var)
            lignes.append(
                {
                    "tarif_id": tarif["id"],
                    "tarif_nom": tarif["nom"],
                    "quantite": qte,
                    "prix_unitaire": tarif["prix"],
                }
            )

        mode = MODES_INV.get(self._var_mode.get(), "especes")
        erreurs = valider_vente(lignes, mode)
        if erreurs:
            afficher_erreur(self, "Erreur", "\n".join(erreurs))
            return

        self.result = {
            "date": self._var_date.get().strip(),
            "canal": CANAUX_INV.get(self._var_canal.get(), "sur_place"),
            "mode_paiement": mode,
            "nom_tireur": self._var_nom_tireur.get().strip() or None,
            "commentaire": self._var_commentaire.get().strip() or None,
            "lignes": lignes,
        }
        self.destroy()

class _DialogMotif(ctk.CTkToplevel):
    """Dialogue pour saisir un motif d'annulation."""

    def __init__(self, parent: Any) -> None:
        super().__init__(parent)
        self.title("Motif d'annulation")
        self.geometry("380x180")
        self.resizable(False, False)
        self.transient(parent)
        self.motif: str = ""
        self._var = tk.StringVar()

        ctk.CTkLabel(self, text="Motif (optionnel) :").pack(
            anchor="w", padx=20, pady=(16, 4)
        )
        ctk.CTkEntry(self, textvariable=self._var, width=320).pack(padx=20)

        frame_btn = ctk.CTkFrame(self, fg_color="transparent")
        frame_btn.pack(pady=16)
        ctk.CTkButton(frame_btn, text="Confirmer", width=110, command=self._ok).pack(
            side="left", padx=8
        )
        ctk.CTkButton(
            frame_btn,
            text="Annuler",
            width=100,
            fg_color="gray",
            hover_color="#555",
            command=self.destroy,
        ).pack(side="left", padx=8)

    def _ok(self) -> None:
        self.motif = self._var.get().strip()
        self.destroy()
