"""Fenêtre de suivi des remboursements de frais."""

from __future__ import annotations

from datetime import datetime
from tkinter import filedialog, ttk
from typing import Any

import customtkinter as ctk

from core.remboursements import generer_pdf_remboursement
from db.models.membres import get_all_membres
from db.models.remboursements import (
    get_remboursements_all,
    get_stats_remboursements,
    marquer_rembourse,
)
from ui import theme as app_theme
from ui.components.dialogs import afficher_erreur, afficher_info

_STATUTS = {
    'tous': 'Tous',
    'en_attente': '🟡 En attente',
    'rembourse': '🟢 Remboursé',
    'non_applicable': '⚫ Non applicable',
}
_SOURCES = {'tous': 'Toutes', 'evenement': 'Événement', 'tresorerie': 'Trésorerie'}


class ListeRemboursements(ctk.CTkToplevel):
    def __init__(self, parent: Any) -> None:
        super().__init__(parent)
        self.title('💸 Remboursements')
        self.geometry('1180x720')
        self.minsize(980, 560)
        self.transient(parent)
        self._membres = get_all_membres()
        self._lignes: list[dict[str, Any]] = []
        self._build_ui()
        self._charger()

    def _build_ui(self) -> None:
        fonts = app_theme.FONTS
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(fill='x', padx=16, pady=(14, 6))
        ctk.CTkLabel(header, text='💸 Remboursements de frais', font=fonts.get('title')).pack(side='left')

        filtres = ctk.CTkFrame(self)
        filtres.pack(fill='x', padx=16, pady=(0, 8))
        self._var_membre = ctk.StringVar(value='Tous')
        self._var_source = ctk.StringVar(value='Toutes')
        self._var_statut = ctk.StringVar(value='🟡 En attente')
        self._var_date_debut = ctk.StringVar()
        self._var_date_fin = ctk.StringVar()

        def add_filter(row: Any, label: str, widget: Any) -> None:
            bloc = ctk.CTkFrame(row, fg_color='transparent')
            bloc.pack(side='left', padx=(0, 8))
            ctk.CTkLabel(bloc, text=label).pack(anchor='w')
            widget.pack(anchor='w', pady=(2, 0))

        membres = ['Tous'] + [f"{m['nom']} {m['prenom']}".strip() for m in self._membres]
        add_filter(filtres, 'Adhérent', ctk.CTkOptionMenu(filtres, values=membres, variable=self._var_membre, width=220))
        add_filter(filtres, 'Période du', ctk.CTkEntry(filtres, textvariable=self._var_date_debut, width=120, placeholder_text='AAAA-MM-JJ'))
        add_filter(filtres, 'au', ctk.CTkEntry(filtres, textvariable=self._var_date_fin, width=120, placeholder_text='AAAA-MM-JJ'))
        add_filter(filtres, 'Statut', ctk.CTkOptionMenu(filtres, values=list(_STATUTS.values()), variable=self._var_statut, width=170))
        add_filter(filtres, 'Source', ctk.CTkOptionMenu(filtres, values=list(_SOURCES.values()), variable=self._var_source, width=160))
        ctk.CTkButton(filtres, text='🔄 Filtrer', width=120, command=self._charger).pack(side='right', padx=(8, 0), pady=(20, 0))

        frame_table = ctk.CTkFrame(self)
        frame_table.pack(fill='both', expand=True, padx=16, pady=8)
        self._tree = ttk.Treeview(
            frame_table,
            columns=('date', 'beneficiaire', 'description', 'montant', 'source', 'statut'),
            show='headings',
            height=18,
        )
        for col, label, width, anchor in [
            ('date', 'Date', 100, 'center'),
            ('beneficiaire', 'Bénéficiaire', 220, 'w'),
            ('description', 'Description', 330, 'w'),
            ('montant', 'Montant', 120, 'e'),
            ('source', 'Source', 130, 'center'),
            ('statut', 'Statut', 140, 'center'),
        ]:
            self._tree.heading(col, text=label)
            self._tree.column(col, width=width, anchor=anchor)
        self._tree.tag_configure('en_attente', foreground='#e67e22')
        self._tree.tag_configure('rembourse', foreground='#27ae60')
        self._tree.tag_configure('non_applicable', foreground='grey')
        sb = ttk.Scrollbar(frame_table, orient='vertical', command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.pack(side='left', fill='both', expand=True)
        sb.pack(side='right', fill='y')

        actions = ctk.CTkFrame(self, fg_color='transparent')
        actions.pack(fill='x', padx=16, pady=(0, 6))
        ctk.CTkButton(actions, text='✅ Marquer remboursé', width=180, command=self._marquer).pack(side='left')
        ctk.CTkButton(actions, text='🖨️ Générer PDF', width=150, command=self._generer_pdf).pack(side='left', padx=(8, 0))
        ctk.CTkButton(actions, text='Fermer', width=110, fg_color='gray', command=self.destroy).pack(side='right')

        self._lbl_stats = ctk.CTkLabel(self, text='')
        self._lbl_stats.pack(anchor='w', padx=16, pady=(0, 12))

    def _filters(self) -> dict[str, Any]:
        membre_nom = self._var_membre.get()
        membre_id = None
        if membre_nom != 'Tous':
            membre = next((m for m in self._membres if f"{m['nom']} {m['prenom']}".strip() == membre_nom), None)
            membre_id = int(membre['id']) if membre else None
        statut = next((code for code, label in _STATUTS.items() if label == self._var_statut.get()), 'tous')
        source = next((code for code, label in _SOURCES.items() if label == self._var_source.get()), 'tous')
        return {
            'membre_id': membre_id,
            'date_debut': self._var_date_debut.get().strip() or None,
            'date_fin': self._var_date_fin.get().strip() or None,
            'statut': statut,
            'source': source,
        }

    def _charger(self) -> None:
        self._lignes = get_remboursements_all(self._filters())
        self._tree.delete(*self._tree.get_children())
        total = 0.0
        for ligne in self._lignes:
            total += float(ligne.get('montant') or 0)
            statut = ligne.get('remboursement_statut') or 'non_applicable'
            self._tree.insert(
                '',
                'end',
                iid=str(ligne['remboursement_id']),
                values=(
                    ligne.get('date_piece') or '',
                    ligne.get('beneficiaire') or '—',
                    ligne.get('description') or '',
                    f"{float(ligne.get('montant') or 0):.2f} €",
                    (_SOURCES.get(ligne.get('source')) or ligne.get('source') or '').title(),
                    _STATUTS.get(statut, statut),
                ),
                tags=(statut,),
            )
        stats = get_stats_remboursements()
        self._lbl_stats.configure(
            text=(
                f"Total affiché : {len(self._lignes)} remboursement(s)  |  "
                f"Montant affiché : {total:.2f} €  |  "
                f"En attente global : {stats['total_en_attente']:.2f} €"
            )
        )

    def _selection(self) -> dict[str, Any] | None:
        selection = self._tree.selection()
        if not selection:
            afficher_info(self, 'Remboursements', 'Sélectionnez un remboursement.')
            return None
        identifiant = selection[0]
        return next((ligne for ligne in self._lignes if str(ligne['remboursement_id']) == identifiant), None)

    def _marquer(self) -> None:
        ligne = self._selection()
        if not ligne:
            return
        dialog = _DialogMarquerRembourse(self, ligne)
        self.wait_window(dialog)
        if not dialog.result:
            return
        ok = marquer_rembourse(
            str(ligne['source']),
            int(ligne['source_id']),
            dialog.result['mode'],
            dialog.result['reference'],
            dialog.result['date'],
        )
        if ok:
            afficher_info(self, 'Remboursements', 'Le remboursement a été mis à jour.')
            self._charger()
        else:
            afficher_erreur(self, 'Remboursements', 'Impossible de mettre à jour ce remboursement.')

    def _generer_pdf(self) -> None:
        ligne = self._selection()
        if not ligne:
            return
        chemin = filedialog.asksaveasfilename(
            parent=self,
            title='Enregistrer le document de remboursement',
            defaultextension='.pdf',
            initialfile=f"remboursement-{ligne['source']}-{ligne['source_id']}.pdf",
            filetypes=[('PDF', '*.pdf')],
        )
        if not chemin:
            return
        resultat = generer_pdf_remboursement(str(ligne['remboursement_id']), chemin)
        if resultat.get('succes'):
            afficher_info(self, 'Remboursements', f"PDF généré : {chemin}")
        else:
            afficher_erreur(self, 'Remboursements', resultat.get('message', 'Erreur de génération PDF.'))


class _DialogMarquerRembourse(ctk.CTkToplevel):
    def __init__(self, parent: Any, ligne: dict[str, Any]) -> None:
        super().__init__(parent)
        self.title('Marquer remboursé')
        self.geometry('420x260')
        self.transient(parent)
        self.grab_set()
        self.result: dict[str, Any] | None = None
        self._var_mode = ctk.StringVar(value='Virement')
        self._var_reference = ctk.StringVar(value=str(ligne.get('remboursement_reference') or ''))
        self._var_date = ctk.StringVar(value=datetime.now().strftime('%Y-%m-%d'))
        self._build()

    def _build(self) -> None:
        frame = ctk.CTkFrame(self)
        frame.pack(fill='both', expand=True, padx=16, pady=16)
        for label, widget in [
            ('Mode', ctk.CTkEntry(frame, textvariable=self._var_mode)),
            ('Référence', ctk.CTkEntry(frame, textvariable=self._var_reference)),
            ('Date', ctk.CTkEntry(frame, textvariable=self._var_date)),
        ]:
            bloc = ctk.CTkFrame(frame, fg_color='transparent')
            bloc.pack(fill='x', pady=5)
            ctk.CTkLabel(bloc, text=label, width=110, anchor='e').pack(side='left', padx=(0, 8))
            widget.pack(side='left', fill='x', expand=True)
        actions = ctk.CTkFrame(frame, fg_color='transparent')
        actions.pack(fill='x', pady=(14, 0))
        ctk.CTkButton(actions, text='Annuler', fg_color='gray', command=self.destroy).pack(side='left')
        ctk.CTkButton(actions, text='Valider', command=self._valider).pack(side='right')

    def _valider(self) -> None:
        if not self._var_mode.get().strip() or not self._var_date.get().strip():
            return
        self.result = {
            'mode': self._var_mode.get().strip(),
            'reference': self._var_reference.get().strip() or None,
            'date': self._var_date.get().strip(),
        }
        self.destroy()
