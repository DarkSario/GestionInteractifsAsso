"""Fenêtre de gestion des dons."""

from __future__ import annotations

from datetime import date
from tkinter import filedialog, ttk
from typing import Any

import customtkinter as ctk

from core.dons import creer_recette_tresorerie, generer_pdf_recu_don
from db.connection import get_connection
from db.models.dons import add_don, delete_don, get_all_dons, get_don_by_id, get_stats_dons, marquer_recu_emis, update_don
from db.models.membres import get_all_membres, get_membre_by_id
from ui import theme as app_theme
from ui.components.dialogs import afficher_erreur, afficher_info, demander_confirmation

_STATUTS = {'tous': 'Tous', 'en_attente': '🟡 En attente', 'emis': '🟢 Émis', 'annule': '🔴 Annulé'}
_TYPES = {'tous': 'Tous', 'particulier': 'Particulier', 'entreprise': 'Entreprise'}


def _parse_optional_float(value: str) -> float | None:
    brut = value.strip().replace(',', '.')
    if not brut:
        return None
    return float(brut)


class ListeDons(ctk.CTkToplevel):
    def __init__(self, parent: Any) -> None:
        super().__init__(parent)
        self.title('💝 Dons')
        self.geometry('1180x720')
        self.minsize(980, 560)
        self.transient(parent)
        self._membres = get_all_membres()
        self._dons: list[dict[str, Any]] = []
        self._build_ui()
        self._charger()

    def _build_ui(self) -> None:
        fonts = app_theme.FONTS
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(fill='x', padx=16, pady=(14, 6))
        ctk.CTkLabel(header, text='💝 Dons', font=fonts.get('title')).pack(side='left')

        self._var_exercice = ctk.StringVar(value='Tous')
        self._var_type = ctk.StringVar(value='Tous')
        self._var_statut = ctk.StringVar(value='Tous')
        self._var_date_debut = ctk.StringVar()
        self._var_date_fin = ctk.StringVar()

        filtres = ctk.CTkFrame(self)
        filtres.pack(fill='x', padx=16, pady=(0, 8))

        def add_filter(parent: Any, label: str, widget: Any) -> None:
            bloc = ctk.CTkFrame(parent, fg_color='transparent')
            bloc.pack(side='left', padx=(0, 8))
            ctk.CTkLabel(bloc, text=label).pack(anchor='w')
            widget.pack(anchor='w', pady=(2, 0))

        add_filter(filtres, 'Exercice', ctk.CTkOptionMenu(filtres, values=self._charger_exercices(), variable=self._var_exercice, width=180))
        add_filter(filtres, 'Type', ctk.CTkOptionMenu(filtres, values=list(_TYPES.values()), variable=self._var_type, width=150))
        add_filter(filtres, 'Statut', ctk.CTkOptionMenu(filtres, values=list(_STATUTS.values()), variable=self._var_statut, width=150))
        add_filter(filtres, 'Période du', ctk.CTkEntry(filtres, textvariable=self._var_date_debut, width=120, placeholder_text='AAAA-MM-JJ'))
        add_filter(filtres, 'au', ctk.CTkEntry(filtres, textvariable=self._var_date_fin, width=120, placeholder_text='AAAA-MM-JJ'))
        ctk.CTkButton(filtres, text='🔄 Filtrer', width=120, command=self._charger).pack(side='right', padx=(8, 0), pady=(20, 0))

        frame_table = ctk.CTkFrame(self)
        frame_table.pack(fill='both', expand=True, padx=16, pady=8)
        self._tree = ttk.Treeview(
            frame_table,
            columns=('num_recu', 'date', 'donateur', 'type', 'montant', 'nature', 'statut'),
            show='headings',
            height=18,
        )
        for col, label, width, anchor in [
            ('num_recu', 'N° Reçu', 110, 'center'),
            ('date', 'Date', 100, 'center'),
            ('donateur', 'Donateur', 260, 'w'),
            ('type', 'Type', 110, 'center'),
            ('montant', 'Montant', 110, 'e'),
            ('nature', 'Nature', 120, 'center'),
            ('statut', 'Statut', 120, 'center'),
        ]:
            self._tree.heading(col, text=label)
            self._tree.column(col, width=width, anchor=anchor)
        self._tree.tag_configure('en_attente', foreground='#e67e22')
        self._tree.tag_configure('emis', foreground='#27ae60')
        self._tree.tag_configure('annule', foreground='#c0392b')
        sb = ttk.Scrollbar(frame_table, orient='vertical', command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.pack(side='left', fill='both', expand=True)
        sb.pack(side='right', fill='y')

        actions = ctk.CTkFrame(self, fg_color='transparent')
        actions.pack(fill='x', padx=16, pady=(0, 6))
        ctk.CTkButton(actions, text='➕ Nouveau don', width=150, command=self._ajouter).pack(side='left')
        ctk.CTkButton(actions, text='✏️ Modifier', width=120, command=self._modifier).pack(side='left', padx=(8, 0))
        ctk.CTkButton(actions, text='🗑️ Supprimer', width=120, fg_color='#8b1a1a', hover_color='#6b1414', command=self._supprimer).pack(side='left', padx=(8, 0))
        ctk.CTkButton(actions, text='✅ Marquer reçu émis', width=180, command=self._marquer_emis).pack(side='left', padx=(8, 0))
        ctk.CTkButton(actions, text='🖨️ Générer / Réimprimer reçu', width=230, command=self._generer_pdf).pack(side='left', padx=(8, 0))
        ctk.CTkButton(actions, text='Fermer', width=110, fg_color='gray', command=self.destroy).pack(side='right')

        self._lbl_stats = ctk.CTkLabel(self, text='')
        self._lbl_stats.pack(anchor='w', padx=16, pady=(0, 12))

    def _charger_exercices(self) -> list[str]:
        conn = get_connection()
        try:
            rows = conn.execute('SELECT id, nom FROM exercices ORDER BY id DESC').fetchall()
            self._map_exercices = {'Tous': None}
            labels = ['Tous']
            for row in rows:
                label = row['nom'] or f"Exercice {row['id']}"
                self._map_exercices[label] = int(row['id'])
                labels.append(label)
            return labels
        finally:
            conn.close()

    def _filters(self) -> dict[str, Any]:
        return {
            'exercice_id': self._map_exercices.get(self._var_exercice.get()),
            'type_donateur': next((code for code, label in _TYPES.items() if label == self._var_type.get()), 'tous'),
            'statut_recu': next((code for code, label in _STATUTS.items() if label == self._var_statut.get()), 'tous'),
            'date_debut': self._var_date_debut.get().strip() or None,
            'date_fin': self._var_date_fin.get().strip() or None,
        }

    def _charger(self) -> None:
        self._dons = get_all_dons(self._filters())
        self._tree.delete(*self._tree.get_children())
        for don in self._dons:
            donateur = f"{don.get('donateur_nom') or ''} {don.get('donateur_prenom') or ''}".strip()
            montant = float(don.get('montant') or don.get('valeur_estimee') or 0)
            statut = don.get('statut_recu') or 'en_attente'
            self._tree.insert(
                '', 'end', iid=str(don['id']),
                values=(
                    don.get('num_recu') or '',
                    don.get('date_don') or '',
                    donateur,
                    _TYPES.get(don.get('type_donateur'), don.get('type_donateur')),
                    f'{montant:.2f} €',
                    '🎁 Nature' if don.get('nature_don') == 'nature' else '💶 Argent',
                    _STATUTS.get(statut, statut),
                ),
                tags=(statut,),
            )
        stats = get_stats_dons(self._map_exercices.get(self._var_exercice.get()))
        self._lbl_stats.configure(
            text=(
                f"Total dons : {stats['montant_total']:.2f} €  |  "
                f"Donateurs uniques : {stats['nb_donateurs']}  |  "
                f"Argent : {stats['total_argent']:.2f} €  |  "
                f"Nature : {stats['total_nature']:.2f} €"
            )
        )

    def _selection(self) -> dict[str, Any] | None:
        selection = self._tree.selection()
        if not selection:
            afficher_info(self, 'Dons', 'Sélectionnez un don.')
            return None
        don_id = int(selection[0])
        return next((don for don in self._dons if int(don['id']) == don_id), None) or get_don_by_id(don_id)

    def _ajouter(self) -> None:
        dialog = _DialogDon(self, self._membres, self._map_exercices)
        self.wait_window(dialog)
        if not dialog.result:
            return
        payload = dict(dialog.result)
        creer_treso = bool(payload.pop('creer_tresorerie', False))
        generer_recu = bool(payload.pop('generer_recu', False))
        don_id = add_don(**payload)
        if creer_treso:
            creer_recette_tresorerie(don_id)
        if generer_recu:
            self._sauver_pdf(don_id)
        self._charger()

    def _modifier(self) -> None:
        don = self._selection()
        if not don:
            return
        dialog = _DialogDon(self, self._membres, self._map_exercices, don=don)
        self.wait_window(dialog)
        if not dialog.result:
            return
        payload = dict(dialog.result)
        payload.pop('creer_tresorerie', None)
        payload.pop('generer_recu', None)
        update_don(int(don['id']), **payload)
        self._charger()

    def _supprimer(self) -> None:
        don = self._selection()
        if not don:
            return
        if demander_confirmation(self, 'Supprimer le don', 'Confirmer la suppression de ce don ?'):
            delete_don(int(don['id']))
            self._charger()

    def _marquer_emis(self) -> None:
        don = self._selection()
        if not don:
            return
        marquer_recu_emis(int(don['id']))
        self._charger()

    def _sauver_pdf(self, don_id: int) -> None:
        don = get_don_by_id(don_id)
        if not don:
            return
        chemin = filedialog.asksaveasfilename(
            parent=self,
            title='Enregistrer le reçu de don',
            defaultextension='.pdf',
            initialfile=f"recu-don-{don.get('num_recu') or don_id}.pdf",
            filetypes=[('PDF', '*.pdf')],
        )
        if not chemin:
            return
        resultat = generer_pdf_recu_don(don_id, chemin)
        if resultat.get('succes'):
            afficher_info(self, 'Dons', f"Reçu généré : {chemin}")
        else:
            afficher_erreur(self, 'Dons', resultat.get('message', 'Impossible de générer le reçu.'))

    def _generer_pdf(self) -> None:
        don = self._selection()
        if not don:
            return
        self._sauver_pdf(int(don['id']))


class _DialogDon(ctk.CTkToplevel):
    def __init__(self, parent: Any, membres: list[dict[str, Any]], exercices: dict[str, int | None], don: dict[str, Any] | None = None) -> None:
        super().__init__(parent)
        self.title('Don')
        self.geometry('560x720')
        self.transient(parent)
        self.grab_set()
        self.result: dict[str, Any] | None = None
        self._membres = membres
        self._map_exercices = exercices
        self._don = don

        self._var_exercice = ctk.StringVar(value=self._label_exercice(don.get('exercice_id')) if don else 'Tous')
        self._var_type = ctk.StringVar(value=(don.get('type_donateur') if don else 'particulier'))
        self._var_membre = ctk.StringVar(value=self._label_membre(don.get('membre_id')) if don else '— Aucun —')
        self._var_nom = ctk.StringVar(value=don.get('donateur_nom') if don else '')
        self._var_prenom = ctk.StringVar(value=don.get('donateur_prenom') if don else '')
        self._var_adresse = ctk.StringVar(value=don.get('donateur_adresse') if don else '')
        self._var_cp = ctk.StringVar(value=don.get('donateur_cp') if don else '')
        self._var_ville = ctk.StringVar(value=don.get('donateur_ville') if don else '')
        self._var_siret = ctk.StringVar(value=don.get('donateur_siret') if don else '')
        self._var_date = ctk.StringVar(value=don.get('date_don') if don else date.today().isoformat())
        self._var_nature = ctk.StringVar(value=don.get('nature_don') if don else 'argent')
        self._var_montant = ctk.StringVar(value=f"{float(don.get('montant') or 0):.2f}" if don and don.get('montant') is not None else '')
        self._var_description = ctk.StringVar(value=don.get('description_don') if don else '')
        self._var_valeur = ctk.StringVar(value=f"{float(don.get('valeur_estimee') or 0):.2f}" if don and don.get('valeur_estimee') is not None else '')
        self._var_mode = ctk.StringVar(value=don.get('mode_versement') if don else 'virement')
        self._var_commentaire = ctk.StringVar(value=don.get('commentaire') if don else '')
        self._var_creer_treso = ctk.BooleanVar(value=False)
        self._var_generer_recu = ctk.BooleanVar(value=False)
        self._build()

    def _label_exercice(self, exercice_id: Any) -> str:
        for label, value in self._map_exercices.items():
            if value == exercice_id:
                return label
        return 'Tous'

    def _label_membre(self, membre_id: Any) -> str:
        membre = next((m for m in self._membres if int(m['id']) == int(membre_id or 0)), None)
        return f"{membre['nom']} {membre['prenom']}".strip() if membre else '— Aucun —'

    def _build(self) -> None:
        scroll = ctk.CTkScrollableFrame(self)
        scroll.pack(fill='both', expand=True, padx=16, pady=16)

        def champ(label: str, widget: Any) -> None:
            bloc = ctk.CTkFrame(scroll, fg_color='transparent')
            bloc.pack(fill='x', pady=4)
            ctk.CTkLabel(bloc, text=label, width=150, anchor='e').pack(side='left', padx=(0, 8))
            widget.pack(side='left', fill='x', expand=True)

        champ('Exercice', ctk.CTkOptionMenu(scroll, values=list(self._map_exercices), variable=self._var_exercice, width=260))
        type_menu = ctk.CTkOptionMenu(scroll, values=['particulier', 'entreprise'], variable=self._var_type, width=260)
        champ('Type donateur', type_menu)
        membre_values = ['— Aucun —'] + [f"{m['nom']} {m['prenom']}".strip() for m in self._membres]
        combo_membre = ctk.CTkOptionMenu(scroll, values=membre_values, variable=self._var_membre, width=260, command=lambda _value: self._prefill_membre())
        champ('Lier à un adhérent', combo_membre)
        champ('Nom / raison sociale *', ctk.CTkEntry(scroll, textvariable=self._var_nom, width=260))
        champ('Prénom', ctk.CTkEntry(scroll, textvariable=self._var_prenom, width=260))
        champ('Adresse', ctk.CTkEntry(scroll, textvariable=self._var_adresse, width=260))
        champ('Code postal', ctk.CTkEntry(scroll, textvariable=self._var_cp, width=260))
        champ('Ville', ctk.CTkEntry(scroll, textvariable=self._var_ville, width=260))
        champ('SIRET', ctk.CTkEntry(scroll, textvariable=self._var_siret, width=260))
        champ('Date du don', ctk.CTkEntry(scroll, textvariable=self._var_date, width=260))
        champ('Nature', ctk.CTkOptionMenu(scroll, values=['argent', 'nature'], variable=self._var_nature, width=260))
        champ('Montant (€)', ctk.CTkEntry(scroll, textvariable=self._var_montant, width=260))
        champ('Description don', ctk.CTkEntry(scroll, textvariable=self._var_description, width=260))
        champ('Valeur estimée (€)', ctk.CTkEntry(scroll, textvariable=self._var_valeur, width=260))
        champ('Mode versement', ctk.CTkOptionMenu(scroll, values=['cheque', 'virement', 'especes', 'cb', 'autre'], variable=self._var_mode, width=260))
        champ('Commentaire', ctk.CTkEntry(scroll, textvariable=self._var_commentaire, width=260))
        if not self._don:
            ctk.CTkCheckBox(scroll, text='Créer recette en trésorerie automatiquement', variable=self._var_creer_treso).pack(anchor='w', padx=160, pady=(6, 0))
            ctk.CTkCheckBox(scroll, text='Générer le reçu immédiatement après enregistrement', variable=self._var_generer_recu).pack(anchor='w', padx=160, pady=(4, 0))

        actions = ctk.CTkFrame(scroll, fg_color='transparent')
        actions.pack(fill='x', pady=(14, 0))
        ctk.CTkButton(actions, text='Annuler', fg_color='gray', command=self.destroy).pack(side='left')
        ctk.CTkButton(actions, text='Valider', command=self._valider).pack(side='right')

    def _prefill_membre(self) -> None:
        label = self._var_membre.get()
        if label == '— Aucun —':
            return
        membre = next((m for m in self._membres if f"{m['nom']} {m['prenom']}".strip() == label), None)
        if not membre:
            return
        detail = get_membre_by_id(int(membre['id']))
        if not detail:
            return
        self._var_nom.set(detail.get('nom') or '')
        self._var_prenom.set(detail.get('prenom') or '')
        self._var_adresse.set(detail.get('commentaire') or self._var_adresse.get())

    def _valider(self) -> None:
        if not self._var_nom.get().strip():
            afficher_erreur(self, 'Dons', 'Le nom du donateur est obligatoire.')
            return
        membre_id = None
        if self._var_membre.get() != '— Aucun —':
            membre = next((m for m in self._membres if f"{m['nom']} {m['prenom']}".strip() == self._var_membre.get()), None)
            membre_id = int(membre['id']) if membre else None
        exercice_id = self._map_exercices.get(self._var_exercice.get())
        self.result = {
            'exercice_id': exercice_id,
            'date_don': self._var_date.get().strip(),
            'type_donateur': self._var_type.get().strip(),
            'membre_id': membre_id,
            'donateur_nom': self._var_nom.get().strip(),
            'donateur_prenom': self._var_prenom.get().strip() or None,
            'donateur_adresse': self._var_adresse.get().strip() or None,
            'donateur_cp': self._var_cp.get().strip() or None,
            'donateur_ville': self._var_ville.get().strip() or None,
            'donateur_siret': self._var_siret.get().strip() or None,
            'nature_don': self._var_nature.get().strip(),
            'montant': _parse_optional_float(self._var_montant.get()),
            'description_don': self._var_description.get().strip() or None,
            'valeur_estimee': _parse_optional_float(self._var_valeur.get()),
            'mode_versement': self._var_mode.get().strip(),
            'commentaire': self._var_commentaire.get().strip() or None,
            'creer_tresorerie': bool(self._var_creer_treso.get()),
            'generer_recu': bool(self._var_generer_recu.get()),
        }
        self.destroy()
