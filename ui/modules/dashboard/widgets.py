"""Widgets réutilisables pour le tableau de bord (Phase 8)."""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk


class CarteKPI(ctk.CTkFrame):
    """Carte avec titre, valeur principale et variation optionnelle."""

    def __init__(
        self,
        parent,
        titre: str,
        valeur: str,
        variation: str | None = None,
        couleur_variation: str | None = None,
        icone: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(parent, corner_radius=8, **kwargs)

        # Titre
        label_titre_text = f"{icone}  {titre}" if icone else titre
        ctk.CTkLabel(
            self,
            text=label_titre_text,
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray70"),
        ).pack(anchor="w", padx=12, pady=(10, 2))

        # Valeur principale
        ctk.CTkLabel(
            self,
            text=valeur,
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(anchor="w", padx=12, pady=(0, 2))

        # Variation optionnelle
        if variation is not None:
            ctk.CTkLabel(
                self,
                text=variation,
                font=ctk.CTkFont(size=11),
                text_color=couleur_variation or ("gray40", "gray60"),
            ).pack(anchor="w", padx=12, pady=(0, 10))
        else:
            # Espacement bas
            ctk.CTkLabel(self, text="").pack(pady=(0, 6))


class BandeauAlertes(ctk.CTkFrame):
    """Bandeau d'alertes coloré — masqué automatiquement s'il n'y a aucune alerte."""

    _COULEURS_NIVEAU = {
        "rouge": ("#e53935", "#b71c1c"),
        "orange": ("#fb8c00", "#e65100"),
        "bleu": ("#1e88e5", "#0d47a1"),
    }
    _ICONES_NIVEAU = {"rouge": "🔴", "orange": "🟡", "bleu": "🔵"}

    def __init__(self, parent, alertes: list[dict], **kwargs) -> None:
        super().__init__(parent, corner_radius=0, **kwargs)
        self._alertes = alertes
        self._on_click_callbacks: dict[int, callable] = {}

        if not alertes:
            # Masquer le bandeau en ne l'affichant pas
            return

        ctk.CTkLabel(
            self,
            text="⚠️  Alertes actives",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(anchor="w", padx=12, pady=(8, 2))

        for alerte in alertes:
            self._ajouter_alerte(alerte)

    def _ajouter_alerte(self, alerte: dict) -> None:
        niveau = alerte.get("niveau", "bleu")
        icone = self._ICONES_NIVEAU.get(niveau, "🔵")
        message = alerte.get("message", "")
        couleur = self._COULEURS_NIVEAU.get(niveau, ("#1e88e5", "#0d47a1"))[0]

        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="x", padx=8, pady=2)

        label = ctk.CTkLabel(
            frame,
            text=f"  {icone}  {message}",
            font=ctk.CTkFont(size=12),
            text_color=couleur,
            anchor="w",
            cursor="hand2",
        )
        label.pack(side="left", anchor="w")

        lien = alerte.get("lien_action")
        if lien:
            label.bind("<Button-1>", lambda e, l=lien: self._on_click(l))

    def _on_click(self, lien: str) -> None:
        if hasattr(self, "_navigation_callback") and self._navigation_callback:
            self._navigation_callback(lien)

    def set_navigation_callback(self, callback) -> None:
        """Définit le callback de navigation appelé au clic sur une alerte."""
        self._navigation_callback = callback


class BarreProgression(ctk.CTkFrame):
    """Barre de progression avec label pourcentage."""

    def __init__(
        self,
        parent,
        label: str,
        valeur_actuelle: float,
        valeur_max: float,
        couleur: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(parent, fg_color="transparent", **kwargs)

        pct = (
            min(1.0, valeur_actuelle / valeur_max)
            if valeur_max > 0
            else 0.0
        )
        pct_label = f"{pct * 100:.1f}%"

        # Ligne titre + pourcentage
        frame_top = ctk.CTkFrame(self, fg_color="transparent")
        frame_top.pack(fill="x")
        ctk.CTkLabel(
            frame_top, text=label, font=ctk.CTkFont(size=12)
        ).pack(side="left")
        ctk.CTkLabel(
            frame_top,
            text=pct_label,
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(side="right")

        # Barre de progression
        ctk.CTkProgressBar(
            self,
            progress_color=couleur or "#1f6aa5",
            height=12,
        ).set(pct)

        # Ligne valeurs
        ctk.CTkLabel(
            self,
            text=f"{valeur_actuelle:,.2f} € / {valeur_max:,.2f} €".replace(",", " ").replace(".", ","),
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "gray60"),
        ).pack(anchor="w", pady=(2, 0))


class GraphiqueEvolution(ctk.CTkFrame):
    """Graphique courbe d'évolution de la trésorerie.

    Utilise matplotlib si disponible, sinon un Canvas tkinter simplifié.
    """

    def __init__(self, parent, donnees: list[dict], **kwargs) -> None:
        super().__init__(parent, corner_radius=8, **kwargs)
        self._donnees = donnees

        if not donnees:
            ctk.CTkLabel(
                self, text="Aucune donnée disponible", font=ctk.CTkFont(size=12)
            ).pack(expand=True)
            return

        try:
            self._build_matplotlib()
        except ImportError:
            self._build_canvas_fallback()

    def _build_matplotlib(self) -> None:
        """Graphique via matplotlib."""
        import matplotlib  # noqa: PLC0415
        matplotlib.use("TkAgg")
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg  # noqa: PLC0415
        import matplotlib.pyplot as plt  # noqa: PLC0415

        mode = ctk.get_appearance_mode()
        bg_color = "#2b2b2b" if mode == "Dark" else "#f0f0f0"
        fg_color = "#ffffff" if mode == "Dark" else "#000000"
        grid_color = "#555555" if mode == "Dark" else "#cccccc"

        labels = [d["mois_label"] for d in self._donnees]
        valeurs = [d["solde_fin_mois"] for d in self._donnees]

        fig, ax = plt.subplots(figsize=(6, 2.5))
        fig.patch.set_facecolor(bg_color)
        ax.set_facecolor(bg_color)

        couleur_courbe = "#2196f3"
        ax.plot(labels, valeurs, color=couleur_courbe, linewidth=2, marker="o", markersize=4)
        ax.fill_between(range(len(valeurs)), valeurs, alpha=0.15, color=couleur_courbe)

        ax.tick_params(colors=fg_color, labelsize=8)
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8, color=fg_color)
        ax.yaxis.set_tick_params(colors=fg_color)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        for spine in ("bottom", "left"):
            ax.spines[spine].set_color(grid_color)
        ax.grid(axis="y", color=grid_color, linestyle="--", linewidth=0.5)
        ax.set_ylabel("Solde (€)", color=fg_color, fontsize=9)

        fig.tight_layout(pad=1.0)

        canvas = FigureCanvasTkAgg(fig, master=self)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=4, pady=4)
        plt.close(fig)

    def _build_canvas_fallback(self) -> None:
        """Graphique simplifié via tkinter.Canvas."""
        canvas_width = 500
        canvas_height = 180
        pad_left = 50
        pad_right = 15
        pad_top = 15
        pad_bottom = 40

        canvas = tk.Canvas(
            self,
            width=canvas_width,
            height=canvas_height,
            bg="#2b2b2b" if ctk.get_appearance_mode() == "Dark" else "#f0f0f0",
            highlightthickness=0,
        )
        canvas.pack(fill="both", expand=True, padx=4, pady=4)

        valeurs = [d["solde_fin_mois"] for d in self._donnees]
        labels = [d["mois_label"] for d in self._donnees]

        if not valeurs:
            return

        v_min = min(valeurs)
        v_max = max(valeurs)
        v_range = v_max - v_min if v_max != v_min else 1.0

        w = canvas_width - pad_left - pad_right
        h = canvas_height - pad_top - pad_bottom
        n = len(valeurs)

        def x_pos(i: int) -> float:
            return pad_left + (i / max(n - 1, 1)) * w

        def y_pos(v: float) -> float:
            return pad_top + h - (v - v_min) / v_range * h

        # Ligne zéro
        fg = "#ffffff" if ctk.get_appearance_mode() == "Dark" else "#333333"
        zero_y = y_pos(0) if v_min <= 0 <= v_max else None
        if zero_y is not None:
            canvas.create_line(pad_left, zero_y, pad_left + w, zero_y, fill="#888888", dash=(4, 4))

        # Courbe
        points = [(x_pos(i), y_pos(valeurs[i])) for i in range(n)]
        for i in range(len(points) - 1):
            color = "#2196f3" if valeurs[i] >= 0 else "#e53935"
            canvas.create_line(*points[i], *points[i + 1], fill=color, width=2)

        # Points et labels X
        for i, (x, y) in enumerate(points):
            canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill="#2196f3", outline="")
            if i % max(1, n // 6) == 0 or i == n - 1:
                canvas.create_text(
                    x,
                    canvas_height - pad_bottom + 12,
                    text=labels[i][:3],
                    fill=fg,
                    font=("Arial", 8),
                )

        # Axe Y — quelques valeurs
        for v in [v_min, (v_min + v_max) / 2, v_max]:
            yy = y_pos(v)
            canvas.create_text(
                pad_left - 4,
                yy,
                text=f"{v:,.0f}".replace(",", " "),
                fill=fg,
                font=("Arial", 8),
                anchor="e",
            )


class ListeAlertes(ctk.CTkFrame):
    """Liste des alertes avec icônes couleur et liens cliquables."""

    _ICONES_NIVEAU = {"rouge": "🔴", "orange": "🟡", "bleu": "🔵"}
    _COULEURS_NIVEAU = {
        "rouge": ("#e53935", "#ef5350"),
        "orange": ("#fb8c00", "#ffa726"),
        "bleu": ("#1e88e5", "#42a5f5"),
    }

    def __init__(
        self,
        parent,
        alertes: list[dict],
        on_click_callback=None,
        **kwargs,
    ) -> None:
        super().__init__(parent, **kwargs)
        self._on_click_callback = on_click_callback

        if not alertes:
            ctk.CTkLabel(
                self,
                text="✅  Aucune alerte",
                font=ctk.CTkFont(size=12),
                text_color=("green", "#66bb6a"),
            ).pack(padx=10, pady=8)
            return

        for alerte in alertes:
            self._ajouter_ligne(alerte)

    def _ajouter_ligne(self, alerte: dict) -> None:
        niveau = alerte.get("niveau", "bleu")
        icone = self._ICONES_NIVEAU.get(niveau, "🔵")
        message = alerte.get("message", "")
        couleur = self._COULEURS_NIVEAU.get(niveau, ("#1e88e5", "#42a5f5"))
        lien = alerte.get("lien_action")

        label = ctk.CTkLabel(
            self,
            text=f"{icone}  {message}",
            font=ctk.CTkFont(size=12),
            text_color=couleur,
            anchor="w",
            cursor="hand2" if lien else "",
        )
        label.pack(fill="x", padx=8, pady=2, anchor="w")
        if lien and self._on_click_callback:
            label.bind("<Button-1>", lambda e, l=lien: self._on_click_callback(l))
