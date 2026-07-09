"""Tableau de bord principal (Phase 8).

Frame intégrée dans MainApp (pas une fenêtre Toplevel).
Actualisation automatique toutes les 5 minutes.
"""

from __future__ import annotations

from datetime import datetime

import customtkinter as ctk

from core.dashboard import get_donnees_dashboard
from ui import theme as app_theme
from ui.modules.dashboard.widgets import (
    BarreProgression,
    BandeauAlertes,
    CarteKPI,
    GraphiqueEvolution,
    ListeAlertes,
)
from utils.logger import get_logger

logger = get_logger(__name__)

_REFRESH_MS = 300_000  # 5 minutes


class DashboardFrame(ctk.CTkFrame):
    """Tableau de bord principal intégré dans la fenêtre principale."""

    def __init__(self, parent, navigation_callback=None, **kwargs) -> None:
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._navigation_callback = navigation_callback
        self._donnees: dict = {}
        self._after_id: str | None = None

        self._build()
        self._charger_donnees()
        self._planifier_actualisation()

    # ── Construction de la structure ──────────────────────────────────────────

    def _build(self) -> None:
        """Construit le squelette du dashboard avec scroll vertical."""
        # Conteneur scrollable
        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.pack(fill="both", expand=True)
        self._scroll.columnconfigure(0, weight=1)

    # ── Données ───────────────────────────────────────────────────────────────

    def _charger_donnees(self) -> None:
        """Charge les données et (re)construit l'affichage."""
        try:
            self._donnees = get_donnees_dashboard()
        except Exception as exc:  # noqa: BLE001
            logger.error("Erreur chargement dashboard : %s", exc)
            self._donnees = {}
        self._rendre()

    def _rendre(self) -> None:
        """Détruit et reconstruit le contenu du scroll."""
        for widget in self._scroll.winfo_children():
            widget.destroy()

        d = self._donnees
        if not d:
            ctk.CTkLabel(
                self._scroll,
                text="Impossible de charger les données du tableau de bord.",
                font=ctk.CTkFont(size=14),
            ).pack(pady=40)
            return

        self._section_entete(d)
        self._section_alertes(d)
        self._section_tresorerie(d)
        self._section_graphique(d)
        self._section_evenements(d)
        self._section_adherents_stock(d)
        self._section_sauvegarde(d)

    # ── Sections ──────────────────────────────────────────────────────────────

    def _section_entete(self, d: dict) -> None:
        frame = ctk.CTkFrame(self._scroll, fg_color="transparent")
        frame.pack(fill="x", padx=12, pady=(10, 4))

        ctk.CTkLabel(
            frame,
            text="🏠  Tableau de bord",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(side="left")

        ctk.CTkLabel(
            frame,
            text=d.get("periode", ""),
            font=ctk.CTkFont(size=14),
            text_color=("gray40", "gray60"),
        ).pack(side="left", padx=16)

        ctk.CTkButton(
            frame,
            text="🔄  Actualiser",
            width=130,
            height=30,
            command=self._charger_donnees,
            fg_color=app_theme.COLORS.get("primary", "#1f6aa5"),
            hover_color=app_theme.COLORS.get("secondary", "#144870"),
            font=ctk.CTkFont(size=12),
        ).pack(side="right")

    def _section_alertes(self, d: dict) -> None:
        alertes = d.get("alertes", [])
        if not alertes:
            return

        bandeau = BandeauAlertes(
            self._scroll,
            alertes=alertes,
            fg_color=("gray90", "gray20"),
        )
        bandeau.set_navigation_callback(self._navigation_callback)
        bandeau.pack(fill="x", padx=12, pady=(4, 8))

    def _section_tresorerie(self, d: dict) -> None:
        ctk.CTkLabel(
            self._scroll,
            text="💰  Trésorerie",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(anchor="w", padx=12, pady=(6, 4))

        frame_kpis = ctk.CTkFrame(self._scroll, fg_color="transparent")
        frame_kpis.pack(fill="x", padx=12, pady=(0, 8))
        for col in range(4):
            frame_kpis.columnconfigure(col, weight=1)

        solde = d.get("solde_global", {})
        recettes_dep = d.get("recettes_depenses", {})
        comparatif = d.get("comparatif", {})

        # Variation recettes
        var_rec = comparatif.get("variation_recettes_pct", 0.0)
        texte_var_rec = (
            f"▲ +{var_rec:.1f}% vs mois préc." if var_rec > 0
            else (f"▼ {var_rec:.1f}% vs mois préc." if var_rec < 0 else "= stable")
        )
        couleur_var_rec = "green" if var_rec >= 0 else "red"

        # Variation dépenses
        var_dep = comparatif.get("variation_depenses_pct", 0.0)
        texte_var_dep = (
            f"▲ +{var_dep:.1f}% vs mois préc." if var_dep > 0
            else (f"▼ {var_dep:.1f}% vs mois préc." if var_dep < 0 else "= stable")
        )
        couleur_var_dep = "red" if var_dep > 0 else "green"

        cartes = [
            {
                "titre": "Solde global",
                "valeur": self._fmt_monnaie(solde.get("solde_total", 0)),
                "variation": None,
                "couleur": None,
                "icone": "🏦",
            },
            {
                "titre": "Recettes (mois)",
                "valeur": f"+{self._fmt_monnaie(recettes_dep.get('total_recettes', 0))}",
                "variation": texte_var_rec,
                "couleur": couleur_var_rec,
                "icone": "📈",
            },
            {
                "titre": "Dépenses (mois)",
                "valeur": f"-{self._fmt_monnaie(recettes_dep.get('total_depenses', 0))}",
                "variation": texte_var_dep,
                "couleur": couleur_var_dep,
                "icone": "📉",
            },
            {
                "titre": "Solde net (mois)",
                "valeur": self._fmt_monnaie(recettes_dep.get("solde_net", 0)),
                "variation": None,
                "couleur": None,
                "icone": "💵",
            },
        ]
        for col, c in enumerate(cartes):
            CarteKPI(
                frame_kpis,
                titre=c["titre"],
                valeur=c["valeur"],
                variation=c["variation"],
                couleur_variation=c["couleur"],
                icone=c["icone"],
            ).grid(row=0, column=col, sticky="nsew", padx=4, pady=4)

    def _section_graphique(self, d: dict) -> None:
        frame_row = ctk.CTkFrame(self._scroll, fg_color="transparent")
        frame_row.pack(fill="x", padx=12, pady=(0, 8))
        frame_row.columnconfigure(0, weight=3)
        frame_row.columnconfigure(1, weight=2)

        # Graphique évolution
        frame_graphique = ctk.CTkFrame(frame_row, corner_radius=8)
        frame_graphique.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=0)
        ctk.CTkLabel(
            frame_graphique,
            text="📈  Évolution trésorerie (12 mois)",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(8, 4))
        GraphiqueEvolution(
            frame_graphique,
            donnees=d.get("evolution", []),
        ).pack(fill="both", expand=True, padx=4, pady=(0, 8))

        # Panneau droit : chèques + subventions
        frame_droite = ctk.CTkFrame(frame_row, fg_color="transparent")
        frame_droite.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=0)

        # Chèques en attente
        cheques = d.get("cheques", {})
        frame_cheques = ctk.CTkFrame(frame_droite, corner_radius=8)
        frame_cheques.pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(
            frame_cheques,
            text="🏦  Chèques en attente",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(8, 2))
        nb_rem = cheques.get("nb_remises", 0)
        mt_rem = cheques.get("montant_total", 0.0)
        ctk.CTkLabel(
            frame_cheques,
            text=(
                f"{nb_rem} remise(s)  —  {self._fmt_monnaie(mt_rem)}"
                if nb_rem > 0
                else "Aucune remise en attente"
            ),
            font=ctk.CTkFont(size=12),
            text_color=("orange", "#ffa726") if nb_rem > 0 else ("gray40", "gray60"),
        ).pack(anchor="w", padx=10, pady=(0, 10))

        # Subventions
        subv = d.get("subventions", {})
        frame_subv = ctk.CTkFrame(frame_droite, corner_radius=8)
        frame_subv.pack(fill="x")
        ctk.CTkLabel(
            frame_subv,
            text="🎁  Subventions",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(8, 4))
        BarreProgression(
            frame_subv,
            label="Obtenu / Demandé",
            valeur_actuelle=subv.get("montant_obtenu", 0.0),
            valeur_max=subv.get("montant_demande", 0.0),
            couleur="#43a047",
        ).pack(fill="x", padx=10, pady=(0, 10))

    def _section_evenements(self, d: dict) -> None:
        ctk.CTkLabel(
            self._scroll,
            text="📅  Événements",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(anchor="w", padx=12, pady=(4, 4))

        frame_ev = ctk.CTkFrame(self._scroll, corner_radius=8)
        frame_ev.pack(fill="x", padx=12, pady=(0, 8))

        # Événement en cours
        en_cours = d.get("evenement_en_cours")
        if en_cours:
            frame_encours = ctk.CTkFrame(frame_ev, fg_color=("#e8f5e9", "#1b5e20"), corner_radius=6)
            frame_encours.pack(fill="x", padx=10, pady=(8, 4))
            date_fin_txt = ""
            if en_cours.get("date_fin"):
                try:
                    dt = datetime.strptime(str(en_cours["date_fin"]), "%Y-%m-%d")
                    date_fin_txt = f" (jusqu'au {dt.strftime('%d/%m/%Y')})"
                except ValueError:
                    date_fin_txt = f" (jusqu'au {en_cours['date_fin']})"
            ctk.CTkLabel(
                frame_encours,
                text=f"🟢  EN COURS : {en_cours['nom']}{date_fin_txt}",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=("#1b5e20", "#a5d6a7"),
            ).pack(anchor="w", padx=10, pady=6)

        # Prochains événements
        prochains = d.get("prochains_evenements", [])
        if prochains:
            ctk.CTkLabel(
                frame_ev,
                text="Prochains événements :",
                font=ctk.CTkFont(size=12, weight="bold"),
            ).pack(anchor="w", padx=10, pady=(6, 2))
            for ev in prochains:
                date_txt = ""
                if ev.get("date_debut"):
                    try:
                        dt = datetime.strptime(str(ev["date_debut"]), "%Y-%m-%d")
                        date_txt = dt.strftime("%d/%m/%Y")
                    except ValueError:
                        date_txt = str(ev.get("date_debut", ""))
                nb_benv = int(ev.get("nb_benevoles_inscrits") or 0)
                benv_txt = f" — {nb_benv} bénévole(s)" if nb_benv > 0 else ""
                ev_label = ctk.CTkLabel(
                    frame_ev,
                    text=f"📌  {ev['nom']}  —  {date_txt}{benv_txt}",
                    font=ctk.CTkFont(size=12),
                    anchor="w",
                    cursor="hand2",
                )
                ev_label.pack(anchor="w", padx=10, pady=1)
                ev_id = ev.get("id")
                if ev_id and self._navigation_callback:
                    ev_label.bind(
                        "<Button-1>",
                        lambda e, eid=ev_id: self._navigation_callback("evenement", eid),
                    )
        else:
            ctk.CTkLabel(
                frame_ev,
                text="Aucun événement à venir.",
                font=ctk.CTkFont(size=12),
                text_color=("gray40", "gray60"),
            ).pack(anchor="w", padx=10, pady=4)

        # Bilan dernier événement
        bilan = d.get("bilan_dernier_evenement")
        if bilan:
            ctk.CTkLabel(
                frame_ev,
                text="Dernier événement terminé :",
                font=ctk.CTkFont(size=12, weight="bold"),
            ).pack(anchor="w", padx=10, pady=(8, 2))
            date_txt = ""
            if bilan.get("date"):
                try:
                    dt = datetime.strptime(str(bilan["date"]), "%Y-%m-%d")
                    date_txt = f"  {dt.strftime('%d/%m/%Y')}"
                except ValueError:
                    date_txt = f"  {bilan['date']}"
            benefice = bilan.get("benefice_net", 0.0)
            benefice_txt = f"+{self._fmt_monnaie(benefice)}" if benefice >= 0 else self._fmt_monnaie(benefice)
            ctk.CTkLabel(
                frame_ev,
                text=(
                    f"  {bilan['nom']}{date_txt}  |  "
                    f"Recettes : {self._fmt_monnaie(bilan.get('recettes_nettes', 0))}  "
                    f"| Dépenses : {self._fmt_monnaie(bilan.get('depenses', 0))}  "
                    f"| Bénéfice : {benefice_txt}"
                ),
                font=ctk.CTkFont(size=12),
            ).pack(anchor="w", padx=10, pady=(0, 8))
        else:
            ctk.CTkLabel(self._scroll if not bilan else frame_ev, text="").pack()

        # Nb bénévoles total sur les prochains événements
        nb_benv_total = d.get("nb_benevoles", 0)
        if nb_benv_total > 0:
            ctk.CTkLabel(
                frame_ev,
                text=f"👥  Total bénévoles inscrits sur les prochains événements : {nb_benv_total}",
                font=ctk.CTkFont(size=12),
            ).pack(anchor="w", padx=10, pady=(0, 8))

    def _section_adherents_stock(self, d: dict) -> None:
        frame_row = ctk.CTkFrame(self._scroll, fg_color="transparent")
        frame_row.pack(fill="x", padx=12, pady=(0, 8))
        frame_row.columnconfigure(0, weight=1)
        frame_row.columnconfigure(1, weight=1)

        # Adhérents
        adh = d.get("adherents", {})
        frame_adh = ctk.CTkFrame(frame_row, corner_radius=8)
        frame_adh.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        ctk.CTkLabel(
            frame_adh,
            text="👥  Adhérents",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(8, 4))

        adh_lignes = [
            ("Total", str(adh.get("nb_total", 0))),
            ("Actifs", str(adh.get("nb_actifs", 0))),
            ("Cotisations non renseignées", str(adh.get("nb_cotisation_non_reglee", 0))),
            ("Nouveaux ce mois", str(adh.get("nb_nouveaux_ce_mois", 0))),
        ]
        for libelle, valeur in adh_lignes:
            ligne = ctk.CTkFrame(frame_adh, fg_color="transparent")
            ligne.pack(fill="x", padx=10, pady=1)
            ctk.CTkLabel(ligne, text=libelle, font=ctk.CTkFont(size=12)).pack(side="left")
            ctk.CTkLabel(
                ligne,
                text=valeur,
                font=ctk.CTkFont(size=12, weight="bold"),
            ).pack(side="right")

        ctk.CTkButton(
            frame_adh,
            text="Voir les adhérents",
            width=160,
            height=28,
            font=ctk.CTkFont(size=11),
            command=lambda: self._navigation_callback("membres") if self._navigation_callback else None,
        ).pack(anchor="w", padx=10, pady=(6, 10))

        # Stock
        stock = d.get("stock", {})
        frame_stock = ctk.CTkFrame(frame_row, corner_radius=8)
        frame_stock.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        ctk.CTkLabel(
            frame_stock,
            text="📦  Stock — Alertes",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(8, 4))

        critique = stock.get("critique", [])
        faible = stock.get("faible", [])

        if not critique and not faible:
            ctk.CTkLabel(
                frame_stock,
                text="✅  Aucune alerte stock",
                font=ctk.CTkFont(size=12),
                text_color=("green", "#66bb6a"),
            ).pack(anchor="w", padx=10, pady=4)
        else:
            for a in critique[:4]:
                ctk.CTkLabel(
                    frame_stock,
                    text=f"🔴  Rupture : {a['nom']} ({a['quantite']:.0f})",
                    font=ctk.CTkFont(size=12),
                    text_color=("#e53935", "#ef5350"),
                    anchor="w",
                ).pack(anchor="w", padx=10, pady=1)
            for a in faible[:4]:
                ctk.CTkLabel(
                    frame_stock,
                    text=f"🟡  Faible : {a['nom']} ({a['quantite']:.0f} / seuil {a['seuil']:.0f})",
                    font=ctk.CTkFont(size=12),
                    text_color=("#fb8c00", "#ffa726"),
                    anchor="w",
                ).pack(anchor="w", padx=10, pady=1)

        ctk.CTkButton(
            frame_stock,
            text="Voir le stock",
            width=140,
            height=28,
            font=ctk.CTkFont(size=11),
            command=lambda: self._navigation_callback("stock") if self._navigation_callback else None,
        ).pack(anchor="w", padx=10, pady=(6, 10))

    def _section_sauvegarde(self, d: dict) -> None:
        sauvegarde = d.get("derniere_sauvegarde", {})
        frame = ctk.CTkFrame(self._scroll, corner_radius=8)
        frame.pack(fill="x", padx=12, pady=(0, 12))

        date_sauv = sauvegarde.get("date", "")
        nb_jours = sauvegarde.get("nb_jours_depuis")

        if date_sauv:
            try:
                dt_str = date_sauv[:10]
                from datetime import datetime as _dt  # noqa: PLC0415
                dt = _dt.strptime(dt_str, "%Y-%m-%d")
                date_sauv_fmt = dt.strftime("%d/%m/%Y")
            except ValueError:
                date_sauv_fmt = date_sauv
            nb_jours_txt = f" (il y a {nb_jours} jour(s))" if nb_jours is not None else ""
            txt = f"💾  Dernière sauvegarde : {date_sauv_fmt}{nb_jours_txt}"
        else:
            txt = "💾  Aucune sauvegarde enregistrée"

        frame_row = ctk.CTkFrame(frame, fg_color="transparent")
        frame_row.pack(fill="x", padx=10, pady=8)
        ctk.CTkLabel(
            frame_row,
            text=txt,
            font=ctk.CTkFont(size=12),
        ).pack(side="left")

        ctk.CTkButton(
            frame_row,
            text="💾  Sauvegarder maintenant",
            width=200,
            height=30,
            font=ctk.CTkFont(size=12),
            command=self._sauvegarder,
        ).pack(side="right")

    # ── Actions ───────────────────────────────────────────────────────────────

    def _sauvegarder(self) -> None:
        """Déclenche une sauvegarde manuelle."""
        if self._navigation_callback:
            self._navigation_callback("sauvegarde")

    # ── Actualisation automatique ─────────────────────────────────────────────

    def _planifier_actualisation(self) -> None:
        """Planifie l'actualisation automatique toutes les 5 minutes."""
        self._after_id = self.after(_REFRESH_MS, self._actualisation_auto)

    def _actualisation_auto(self) -> None:
        """Effectue l'actualisation automatique et replanifie."""
        self._charger_donnees()
        self._planifier_actualisation()

    def annuler_actualisation(self) -> None:
        """Annule l'actualisation automatique planifiée."""
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except Exception:  # noqa: BLE001
                pass
            self._after_id = None

    def destroy(self) -> None:
        """Annule l'actualisation avant destruction du widget."""
        self.annuler_actualisation()
        super().destroy()

    # ── Utilitaires ───────────────────────────────────────────────────────────

    @staticmethod
    def _fmt_monnaie(valeur: float) -> str:
        try:
            v = float(valeur)
        except (TypeError, ValueError):
            v = 0.0
        return f"{v:,.2f} €".replace(",", " ").replace(".", ",")
