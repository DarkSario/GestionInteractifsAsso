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
from ui.components.dialogs import afficher_erreur, afficher_info, afficher_succes
from ui.components.form_dialog import FormDialog

_STATUTS = {
    'tous': 'Tous',
    'en_attente': '🟡 En attente',
    'rembourse': '🟢 Remboursé',
    'non_applicable': '⚫ Non applicable',
}
_SOURCES = {'tous': 'Toutes', 'evenement': 'Événement', 'tresorerie': 'Trésorerie', 'tombola': 'Tombola'}
_MODE_REMBOURSEMENT_DEFAUT = 'Virement'


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

        filtres.grid_columnconfigure((1, 3), weight=1)
        membres = ['Tous'] + [f"{m['nom']} {m['prenom']}".strip() for m in self._membres]
        ctk.CTkLabel(filtres, text='Adhérent :').grid(row=0, column=0, sticky='e', padx=(10, 5), pady=5)
        ctk.CTkOptionMenu(filtres, values=membres, variable=self._var_membre, width=220).grid(row=0, column=1, sticky='ew', padx=(0, 10), pady=5)
        ctk.CTkLabel(filtres, text='Statut :').grid(row=0, column=2, sticky='e', padx=(10, 5), pady=5)
        ctk.CTkOptionMenu(filtres, values=list(_STATUTS.values()), variable=self._var_statut, width=170).grid(row=0, column=3, sticky='ew', padx=(0, 10), pady=5)
        ctk.CTkLabel(filtres, text='Source :').grid(row=1, column=0, sticky='e', padx=(10, 5), pady=5)
        ctk.CTkOptionMenu(filtres, values=list(_SOURCES.values()), variable=self._var_source, width=160).grid(row=1, column=1, sticky='ew', padx=(0, 10), pady=5)
        ctk.CTkLabel(filtres, text='Période du :').grid(row=1, column=2, sticky='e', padx=(10, 5), pady=5)
        frame_periode = ctk.CTkFrame(filtres, fg_color='transparent')
        frame_periode.grid(row=1, column=3, sticky='ew', padx=(0, 10), pady=5)
        frame_periode.grid_columnconfigure((0, 2), weight=1)
        ctk.CTkEntry(frame_periode, textvariable=self._var_date_debut, placeholder_text='AAAA-MM-JJ').grid(row=0, column=0, sticky='ew')
        ctk.CTkLabel(frame_periode, text='au').grid(row=0, column=1, padx=6)
        ctk.CTkEntry(frame_periode, textvariable=self._var_date_fin, placeholder_text='AAAA-MM-JJ').grid(row=0, column=2, sticky='ew')
        frame_actions_filtres = ctk.CTkFrame(filtres, fg_color='transparent')
        frame_actions_filtres.grid(row=2, column=3, sticky='e', padx=(0, 10), pady=(4, 6))
        ctk.CTkButton(frame_actions_filtres, text='🔍 Filtrer', width=120, command=self._charger).pack(side='left')
        ctk.CTkButton(frame_actions_filtres, text='🔄 Reset', width=110, command=self._reset_filtres).pack(side='left', padx=(8, 0))

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
        ctk.CTkButton(actions, text='✏️ Modifier', width=120, command=self._modifier).pack(side='left', padx=(8, 0))
        ctk.CTkButton(actions, text='🖨️ Générer PDF', width=150, command=self._generer_pdf).pack(side='left', padx=(8, 0))
        ctk.CTkButton(actions, text='🔄 Actualiser', width=130, command=self._charger).pack(side='left', padx=(8, 0))
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

    def _reset_filtres(self) -> None:
        self._var_membre.set('Tous')
        self._var_source.set('Toutes')
        self._var_statut.set('🟡 En attente')
        self._var_date_debut.set('')
        self._var_date_fin.set('')
        self._charger()

    def _selection(self) -> dict[str, Any] | None:
        selection = self._tree.selection()
        if not selection:
            afficher_info(self, 'Remboursements', 'Sélectionnez un remboursement.')
            return None
        identifiant = selection[0]
        return next((ligne for ligne in self._lignes if str(ligne['remboursement_id']) == identifiant), None)

    def _appliquer_dialog_rembourse(self, ligne: dict[str, Any], titre: str, msg_ok: str, msg_err: str) -> None:
        dialog = _DialogMarquerRembourse(self, ligne, titre=titre)
        self.wait_window(dialog)
        if not dialog.result:
            return
        ok = marquer_rembourse(
            str(ligne['source']),
            int(ligne['source_id']),
            dialog.result['mode'],
            dialog.result['reference'],
            dialog.result['date'],
            dialog.result.get('commentaire'),
        )
        if ok:
            afficher_succes(self, 'Remboursements', msg_ok)
            self._charger()
        else:
            afficher_erreur(self, 'Remboursements', msg_err)

    def _marquer(self) -> None:
        ligne = self._selection()
        if not ligne:
            return
        self._appliquer_dialog_rembourse(
            ligne,
            titre='✅ Marquer remboursé',
            msg_ok='Le remboursement a été mis à jour.',
            msg_err='Impossible de mettre à jour ce remboursement.',
        )

    def _modifier(self) -> None:
        ligne = self._selection()
        if not ligne:
            return
        self._appliquer_dialog_rembourse(
            ligne,
            titre='✏️ Modifier remboursement',
            msg_ok='Le remboursement a été modifié.',
            msg_err='Impossible de modifier ce remboursement.',
        )

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


class _DialogMarquerRembourse(FormDialog):
    def __init__(self, parent: Any, ligne: dict[str, Any], titre: str = '✅ Marquer remboursé') -> None:
        super().__init__(parent, titre=titre, largeur=500, hauteur=400)
        self._var_mode = ctk.StringVar(value=str(ligne.get('remboursement_mode') or _MODE_REMBOURSEMENT_DEFAUT))
        self._var_reference = ctk.StringVar(value=str(ligne.get('remboursement_reference') or ''))
        self._var_date = ctk.StringVar(value=str(ligne.get('remboursement_date') or datetime.now().strftime('%Y-%m-%d')))
        self._var_commentaire = ctk.StringVar(value=str(ligne.get('commentaire') or ''))
        self._build()

    def _build(self) -> None:
        frame = ctk.CTkFrame(self.frame_content)
        frame.pack(fill='both', expand=True, padx=16, pady=16)
        champs = [
            ('Mode de remboursement', ctk.CTkOptionMenu(frame, values=['Virement', 'Chèque', 'Espèces', 'CB', 'Autre'], variable=self._var_mode)),
            ('Référence (N° chèque, virement...)', ctk.CTkEntry(frame, textvariable=self._var_reference)),
            ('Date du remboursement (AAAA-MM-JJ)', ctk.CTkEntry(frame, textvariable=self._var_date)),
            ('Commentaire', ctk.CTkEntry(frame, textvariable=self._var_commentaire)),
        ]
        for label, widget in champs:
            bloc = ctk.CTkFrame(frame, fg_color='transparent')
            bloc.pack(fill='x', pady=5)
            ctk.CTkLabel(bloc, text=label, anchor='w').pack(fill='x')
            widget.pack(fill='x', pady=(2, 0))

    def _on_valider(self) -> None:
        if not self._var_mode.get().strip() or not self._var_date.get().strip():
            return
        self.result = {
            'mode': self._var_mode.get().strip(),
            'reference': self._var_reference.get().strip() or None,
            'date': self._var_date.get().strip(),
            'commentaire': self._var_commentaire.get().strip() or None,
        }
        self.destroy()
