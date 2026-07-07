"""Treeview générique stylé pour l'affichage de données tabulaires."""

import tkinter.ttk as ttk
from typing import Any, Sequence

import customtkinter as ctk


class DataTable(ctk.CTkFrame):
    """Tableau générique basé sur :class:`ttk.Treeview`.

    Permet d'afficher, sélectionner et trier des données tabulaires.

    Args:
        parent: Widget parent.
        columns: Séquence de noms de colonnes.
        show_index: Si ``True``, affiche une colonne numéro de ligne.
        **kwargs: Arguments passés à :class:`ctk.CTkFrame`.
    """

    def __init__(
        self,
        parent: Any,
        columns: Sequence[str],
        show_index: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(parent, **kwargs)
        self._columns = list(columns)
        self._show_index = show_index
        self._build()

    def _build(self) -> None:
        """Construit le widget Treeview avec scrollbars."""
        cols = (["#"] + self._columns) if self._show_index else self._columns

        self._tree = ttk.Treeview(self, columns=cols, show="headings", selectmode="browse")

        # Entêtes et colonnes
        for col in cols:
            self._tree.heading(col, text=col, command=lambda c=col: self._sort_by(c))
            width = 50 if col == "#" else 150
            self._tree.column(col, width=width, anchor="w")

        # Scrollbars
        vsb = ttk.Scrollbar(self, orient="vertical",   command=self._tree.yview)
        hsb = ttk.Scrollbar(self, orient="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # Placement
        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        # Alternance de couleurs (zèbre)
        self._tree.tag_configure("odd",  background="#2b2b2b" if _is_dark() else "#f5f5f5")
        self._tree.tag_configure("even", background="#1e1e1e" if _is_dark() else "#ffffff")

    def set_data(self, rows: Sequence[Sequence[Any]]) -> None:
        """Remplace toutes les données du tableau.

        Args:
            rows: Séquence de lignes (chaque ligne est une séquence de valeurs).
        """
        self.clear()
        for i, row in enumerate(rows):
            values = ([i + 1] + list(row)) if self._show_index else list(row)
            tag = "odd" if i % 2 else "even"
            self._tree.insert("", "end", values=values, tags=(tag,))

    def clear(self) -> None:
        """Supprime toutes les lignes du tableau."""
        self._tree.delete(*self._tree.get_children())

    def get_selected(self) -> tuple[Any, ...] | None:
        """Retourne les valeurs de la ligne sélectionnée, ou ``None``."""
        sel = self._tree.selection()
        if not sel:
            return None
        return self._tree.item(sel[0], "values")

    def _sort_by(self, col: str) -> None:
        """Trie le tableau par la colonne cliquée."""
        items = [(self._tree.set(k, col), k) for k in self._tree.get_children("")]
        # Détermine une seule fois si les valeurs sont numériques
        try:
            float(items[0][0]) if items else None
            numeric = True
        except (ValueError, IndexError):
            numeric = False

        if numeric:
            items.sort(key=lambda t: float(t[0]))
        else:
            items.sort(key=lambda t: t[0].lower())

        for index, (_, k) in enumerate(items):
            self._tree.move(k, "", index)
            tag = "odd" if index % 2 else "even"
            self._tree.item(k, tags=(tag,))


def _is_dark() -> bool:
    """Retourne ``True`` si le mode sombre est actif."""
    return ctk.get_appearance_mode().lower() == "dark"
