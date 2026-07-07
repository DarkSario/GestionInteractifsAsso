"""Formulaire générique pour la saisie de données."""

from typing import Any, Callable

import customtkinter as ctk

from ui import theme as app_theme


class FormField:
    """Décrit un champ de formulaire.

    Args:
        name: Identifiant interne du champ.
        label: Libellé affiché.
        field_type: Type du champ (``"text"``, ``"password"``, ``"combobox"``, ``"checkbox"``).
        required: Si ``True``, le champ est obligatoire.
        options: Liste d'options pour un champ ``"combobox"``.
        default: Valeur par défaut.
    """

    def __init__(
        self,
        name: str,
        label: str,
        field_type: str = "text",
        required: bool = False,
        options: list[str] | None = None,
        default: Any = "",
    ) -> None:
        self.name = name
        self.label = label
        self.field_type = field_type
        self.required = required
        self.options = options or []
        self.default = default


class GenericForm(ctk.CTkFrame):
    """Formulaire générique composé de champs configurables.

    Args:
        parent: Widget parent.
        fields: Liste de :class:`FormField`.
        on_submit: Callback appelé avec ``dict[name, value]`` lors de la soumission.
        submit_label: Libellé du bouton de soumission.
        **kwargs: Arguments passés à :class:`ctk.CTkFrame`.
    """

    def __init__(
        self,
        parent: Any,
        fields: list[FormField],
        on_submit: Callable[[dict[str, Any]], None] | None = None,
        submit_label: str = "Enregistrer",
        **kwargs: Any,
    ) -> None:
        super().__init__(parent, **kwargs)
        self._fields = fields
        self._on_submit = on_submit
        self._submit_label = submit_label
        self._widgets: dict[str, Any] = {}
        self._build()

    def _build(self) -> None:
        """Construit les widgets du formulaire."""
        fonts = app_theme.FONTS

        for row, field in enumerate(self._fields):
            # Libellé
            lbl_text = field.label + (" *" if field.required else "")
            ctk.CTkLabel(self, text=lbl_text, font=fonts.get("normal"), anchor="e").grid(
                row=row, column=0, padx=(10, 5), pady=5, sticky="e"
            )

            # Widget selon le type
            if field.field_type == "combobox":
                widget = ctk.CTkComboBox(self, values=field.options)
                widget.set(field.default or (field.options[0] if field.options else ""))
            elif field.field_type == "checkbox":
                var = ctk.BooleanVar(value=bool(field.default))
                widget = ctk.CTkCheckBox(self, text="", variable=var)
                self._widgets[f"_var_{field.name}"] = var
            elif field.field_type == "password":
                widget = ctk.CTkEntry(self, show="•")
                widget.insert(0, str(field.default))
            else:  # text par défaut
                widget = ctk.CTkEntry(self)
                widget.insert(0, str(field.default))

            widget.grid(row=row, column=1, padx=(0, 10), pady=5, sticky="ew")
            self._widgets[field.name] = widget

        self.columnconfigure(1, weight=1)

        # Bouton de soumission
        if self._on_submit:
            ctk.CTkButton(
                self,
                text=self._submit_label,
                command=self._submit,
                font=fonts.get("bold"),
            ).grid(
                row=len(self._fields),
                column=0,
                columnspan=2,
                pady=15,
            )

    def get_values(self) -> dict[str, Any]:
        """Retourne les valeurs saisies dans le formulaire."""
        result: dict[str, Any] = {}
        for field in self._fields:
            widget = self._widgets.get(field.name)
            if widget is None:
                continue
            if field.field_type == "checkbox":
                var = self._widgets.get(f"_var_{field.name}")
                result[field.name] = var.get() if var else False
            elif field.field_type == "combobox":
                result[field.name] = widget.get()
            else:
                result[field.name] = widget.get()
        return result

    def set_values(self, values: dict[str, Any]) -> None:
        """Remplit le formulaire avec les valeurs données.

        Args:
            values: Dictionnaire ``{name: value}``.
        """
        for field in self._fields:
            if field.name not in values:
                continue
            widget = self._widgets.get(field.name)
            if widget is None:
                continue
            val = values[field.name]
            if field.field_type == "checkbox":
                var = self._widgets.get(f"_var_{field.name}")
                if var:
                    var.set(bool(val))
            elif field.field_type == "combobox":
                widget.set(str(val))
            else:
                widget.delete(0, "end")
                widget.insert(0, str(val) if val is not None else "")

    def clear(self) -> None:
        """Réinitialise tous les champs à leurs valeurs par défaut."""
        for field in self._fields:
            widget = self._widgets.get(field.name)
            if widget is None:
                continue
            if field.field_type == "checkbox":
                var = self._widgets.get(f"_var_{field.name}")
                if var:
                    var.set(bool(field.default))
            elif field.field_type == "combobox":
                widget.set(field.default or (field.options[0] if field.options else ""))
            else:
                widget.delete(0, "end")
                widget.insert(0, str(field.default))

    def _submit(self) -> None:
        """Appelle le callback de soumission avec les valeurs du formulaire."""
        if self._on_submit:
            self._on_submit(self.get_values())
