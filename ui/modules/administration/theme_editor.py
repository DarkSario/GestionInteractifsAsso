"""Éditeur visuel du thème de l'application.

Permet de personnaliser :
- Le mode d'affichage (Clair / Sombre)
- La couleur principale et secondaire (via tkcolorpicker)
- La police et sa taille
- Le logo de l'association
"""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ui import theme as app_theme
from utils.logger import get_logger

logger = get_logger(__name__)

_DEFAULT_THEME: dict[str, Any] = {
    "appearance_mode": "dark",
    "color_theme": "blue",
    "primary_color": "#1f6aa5",
    "secondary_color": "#144870",
    "font_family": "Arial",
    "font_size": "normal",
    "logo_path": None,
}

_FONT_FAMILIES = ["Arial", "Helvetica", "Verdana", "Trebuchet MS", "Calibri", "Segoe UI"]
_FONT_SIZES = {"Petit": "small", "Normal": "normal", "Grand": "large"}
_MODES = {"Sombre": "dark", "Clair": "light"}


class ThemeEditor(ctk.CTkToplevel):
    """Fenêtre d'édition du thème visuel."""

    def __init__(self, parent: Any) -> None:
        super().__init__(parent)
        self.title("Apparence — Éditeur de thème")
        self.geometry("520x580")
        self.resizable(False, False)

        self._current = dict(app_theme.get_theme())
        self._build()

    # ── Construction de l'interface ───────────────────────────────────────────

    def _build(self) -> None:
        """Construit les widgets de l'éditeur."""
        fonts = app_theme.FONTS

        # Titre
        ctk.CTkLabel(self, text="🎨  Personnalisation de l'apparence",
                     font=fonts.get("subtitle")).pack(padx=20, pady=(20, 10))

        # Contenu scrollable
        container = ctk.CTkScrollableFrame(self)
        container.pack(fill="both", expand=True, padx=15, pady=5)
        container.columnconfigure(1, weight=1)

        row = 0

        # ── Mode d'affichage ──────────────────────────────────────────────────
        ctk.CTkLabel(container, text="Mode d'affichage :", anchor="e",
                     font=fonts.get("normal")).grid(row=row, column=0, padx=10, pady=8, sticky="e")
        mode_options = list(_MODES.keys())
        current_mode_label = next(
            (k for k, v in _MODES.items() if v == self._current.get("appearance_mode", "dark")),
            "Sombre",
        )
        self._mode_var = ctk.StringVar(value=current_mode_label)
        ctk.CTkOptionMenu(container, values=mode_options, variable=self._mode_var,
                          command=self._preview_mode).grid(row=row, column=1, padx=10, pady=8, sticky="ew")
        row += 1

        # ── Thème de couleur CTK ──────────────────────────────────────────────
        ctk.CTkLabel(container, text="Thème couleur CTK :", anchor="e",
                     font=fonts.get("normal")).grid(row=row, column=0, padx=10, pady=8, sticky="e")
        self._color_theme_var = ctk.StringVar(value=self._current.get("color_theme", "blue"))
        ctk.CTkOptionMenu(container, values=["blue", "green", "dark-blue"],
                          variable=self._color_theme_var).grid(row=row, column=1, padx=10, pady=8, sticky="ew")
        row += 1

        # ── Couleur principale ────────────────────────────────────────────────
        ctk.CTkLabel(container, text="Couleur principale :", anchor="e",
                     font=fonts.get("normal")).grid(row=row, column=0, padx=10, pady=8, sticky="e")
        primary_frame = ctk.CTkFrame(container, fg_color="transparent")
        primary_frame.grid(row=row, column=1, padx=10, pady=8, sticky="ew")

        self._primary_var = ctk.StringVar(value=self._current.get("primary_color", "#1f6aa5"))
        self._primary_entry = ctk.CTkEntry(primary_frame, textvariable=self._primary_var, width=120)
        self._primary_entry.pack(side="left", padx=(0, 8))
        self._primary_preview = ctk.CTkLabel(primary_frame, text="   ", width=30,
                                             fg_color=self._primary_var.get(), corner_radius=4)
        self._primary_preview.pack(side="left", padx=(0, 8))
        ctk.CTkButton(primary_frame, text="Choisir", width=80,
                      command=lambda: self._pick_color("primary")).pack(side="left")
        self._primary_var.trace_add("write", lambda *_: self._update_color_preview("primary"))
        row += 1

        # ── Couleur secondaire ────────────────────────────────────────────────
        ctk.CTkLabel(container, text="Couleur secondaire :", anchor="e",
                     font=fonts.get("normal")).grid(row=row, column=0, padx=10, pady=8, sticky="e")
        secondary_frame = ctk.CTkFrame(container, fg_color="transparent")
        secondary_frame.grid(row=row, column=1, padx=10, pady=8, sticky="ew")

        self._secondary_var = ctk.StringVar(value=self._current.get("secondary_color", "#144870"))
        self._secondary_entry = ctk.CTkEntry(secondary_frame, textvariable=self._secondary_var, width=120)
        self._secondary_entry.pack(side="left", padx=(0, 8))
        self._secondary_preview = ctk.CTkLabel(secondary_frame, text="   ", width=30,
                                               fg_color=self._secondary_var.get(), corner_radius=4)
        self._secondary_preview.pack(side="left", padx=(0, 8))
        ctk.CTkButton(secondary_frame, text="Choisir", width=80,
                      command=lambda: self._pick_color("secondary")).pack(side="left")
        self._secondary_var.trace_add("write", lambda *_: self._update_color_preview("secondary"))
        row += 1

        # ── Police ───────────────────────────────────────────────────────────
        ctk.CTkLabel(container, text="Police :", anchor="e",
                     font=fonts.get("normal")).grid(row=row, column=0, padx=10, pady=8, sticky="e")
        self._font_var = ctk.StringVar(value=self._current.get("font_family", "Arial"))
        ctk.CTkOptionMenu(container, values=_FONT_FAMILIES,
                          variable=self._font_var).grid(row=row, column=1, padx=10, pady=8, sticky="ew")
        row += 1

        # ── Taille de police ─────────────────────────────────────────────────
        ctk.CTkLabel(container, text="Taille de police :", anchor="e",
                     font=fonts.get("normal")).grid(row=row, column=0, padx=10, pady=8, sticky="e")
        current_size_label = next(
            (k for k, v in _FONT_SIZES.items() if v == self._current.get("font_size", "normal")),
            "Normal",
        )
        self._size_var = ctk.StringVar(value=current_size_label)
        ctk.CTkOptionMenu(container, values=list(_FONT_SIZES.keys()),
                          variable=self._size_var).grid(row=row, column=1, padx=10, pady=8, sticky="ew")
        row += 1

        # ── Logo ─────────────────────────────────────────────────────────────
        ctk.CTkLabel(container, text="Logo association :", anchor="e",
                     font=fonts.get("normal")).grid(row=row, column=0, padx=10, pady=8, sticky="e")
        logo_frame = ctk.CTkFrame(container, fg_color="transparent")
        logo_frame.grid(row=row, column=1, padx=10, pady=8, sticky="ew")

        logo_path = self._current.get("logo_path") or ""
        self._logo_var = ctk.StringVar(value=logo_path)
        ctk.CTkEntry(logo_frame, textvariable=self._logo_var, width=180).pack(side="left", padx=(0, 8))
        ctk.CTkButton(logo_frame, text="Parcourir", width=80,
                      command=self._browse_logo).pack(side="left")
        row += 1

        # ── Boutons d'action ─────────────────────────────────────────────────
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=15)

        ctk.CTkButton(btn_frame, text="Enregistrer", width=140,
                      command=self._save).pack(side="left", padx=(0, 10))
        ctk.CTkButton(btn_frame, text="Réinitialiser", width=140,
                      fg_color="gray", hover_color="#555",
                      command=self._reset).pack(side="left", padx=(0, 10))
        ctk.CTkButton(btn_frame, text="Annuler", width=100,
                      fg_color="gray40", hover_color="gray30",
                      command=self.destroy).pack(side="right")

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _pick_color(self, target: str) -> None:
        """Ouvre le sélecteur de couleur pour la cible donnée.

        Args:
            target: ``"primary"`` ou ``"secondary"``.
        """
        try:
            import tkcolorpicker
            var = self._primary_var if target == "primary" else self._secondary_var
            initial = var.get()
            result = tkcolorpicker.askcolor(color=initial, parent=self)
            if result and result[1]:
                var.set(result[1])
        except ImportError:
            logger.warning("tkcolorpicker non disponible - saisie manuelle uniquement")
            from ui.components.dialogs import afficher_info
            afficher_info(
                self,
                "Color picker indisponible",
                "Le module tkcolorpicker n'est pas installé.\n"
                "Saisissez le code couleur hexadécimal directement dans le champ.",
            )

    def _update_color_preview(self, target: str) -> None:
        """Met à jour le carré de prévisualisation de la couleur."""
        try:
            if target == "primary":
                self._primary_preview.configure(fg_color=self._primary_var.get())
            else:
                self._secondary_preview.configure(fg_color=self._secondary_var.get())
        except Exception:
            pass  # Couleur invalide saisie manuellement — on ignore

    def _preview_mode(self, _: str) -> None:
        """Applique le mode d'affichage en temps réel."""
        mode = _MODES.get(self._mode_var.get(), "dark")
        ctk.set_appearance_mode(mode)

    def _browse_logo(self) -> None:
        """Ouvre une boîte de dialogue pour sélectionner un logo."""
        import tkinter.filedialog as fd
        path = fd.askopenfilename(
            parent=self,
            title="Choisir un logo",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.gif *.bmp"), ("Tous les fichiers", "*.*")],
        )
        if path:
            self._logo_var.set(path)

    def _build_theme_data(self) -> dict[str, Any]:
        """Construit le dictionnaire de thème depuis les widgets."""
        return {
            "appearance_mode": _MODES.get(self._mode_var.get(), "dark"),
            "color_theme": self._color_theme_var.get(),
            "primary_color": self._primary_var.get(),
            "secondary_color": self._secondary_var.get(),
            "font_family": self._font_var.get(),
            "font_size": _FONT_SIZES.get(self._size_var.get(), "normal"),
            "logo_path": self._logo_var.get() or None,
        }

    def _save(self) -> None:
        """Sauvegarde le thème et ferme l'éditeur."""
        data = self._build_theme_data()
        app_theme.save_theme(data)
        logger.info("Thème sauvegardé depuis l'éditeur")
        from ui.components.dialogs import afficher_info
        afficher_info(self, "Thème enregistré",
                      "Le thème a été sauvegardé.\n"
                      "Redémarrez l'application pour appliquer tous les changements.")
        self.destroy()

    def _reset(self) -> None:
        """Réinitialise les champs aux valeurs par défaut."""
        from ui.components.dialogs import demander_confirmation
        if not demander_confirmation(self, "Réinitialiser",
                                     "Remettre tous les paramètres aux valeurs par défaut ?"):
            return
        app_theme.save_theme(dict(_DEFAULT_THEME))
        ctk.set_appearance_mode(_DEFAULT_THEME["appearance_mode"])
        logger.info("Thème réinitialisé aux valeurs par défaut")
        self.destroy()
