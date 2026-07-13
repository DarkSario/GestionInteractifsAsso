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
from ui.components.form_dialog import FormDialog

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
        filtres.grid_columnconfigure((1, 3), weight=1)

        ctk.CTkLabel(filtres, text='Exercice :').grid(row=0, column=0, sticky='e', padx=(10, 5), pady=5)
        ctk.CTkOptionMenu(
            filtres,
            values=self._charger_exercices(),
            variable=self._var_exercice,
            width=200,
        ).grid(row=0, column=1, sticky='ew', padx=(0, 10), pady=5)

        ctk.CTkLabel(filtres, text='Type :').grid(row=0, column=2, sticky='e', padx=(10, 5), pady=5)
        ctk.CTkOptionMenu(
            filtres,
            values=list(_TYPES.values()),
            variable=self._var_type,
            width=180,
        ).grid(row=0, column=3, sticky='ew', padx=(0, 10), pady=5)

        ctk.CTkLabel(filtres, text='Statut :').grid(row=1, column=0, sticky='e', padx=(10, 5), pady=5)
        ctk.CTkOptionMenu(
            filtres,
            values=list(_STATUTS.values()),
            variable=self._var_statut,
            width=180,
        ).grid(row=1, column=1, sticky='ew', padx=(0, 10), pady=5)

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
        ctk.CTkButton(actions, text='🔄 Actualiser', width=130, command=self._charger).pack(side='left', padx=(8, 0))
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

    def _reset_filtres(self) -> None:
        self._var_exercice.set('Tous')
        self._var_type.set('Tous')
        self._var_statut.set('Tous')
        self._var_date_debut.set('')
        self._var_date_fin.set('')
        self._charger()

    def _charger(self) -> None:
        self._dons = get_all_dons(self._filters())
        self._tree.delete(*self._tree.get_children())
        for don in self._dons:
            donateur = f"{don.get('donateur_nom') or ''} {don.get('donateur_prenom') or ''}".strip()
            montant = float(
                don.get('valeur_estimee')
                if don.get('nature_don') == 'nature'
                else don.get('montant')
                or 0
            )
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


class _DialogDon(FormDialog):
    def __init__(self, parent: Any, membres: list[dict[str, Any]], exercices: dict[str, int | None], don: dict[str, Any] | None = None) -> None:
        super().__init__(
            parent,
            titre='✏️ Modifier un don' if don else '➕ Nouveau don',
            largeur=700,
            hauteur=750,
        )
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
        self._mettre_a_jour_visibilite_champs()

    def _label_exercice(self, exercice_id: Any) -> str:
        for label, value in self._map_exercices.items():
            if value == exercice_id:
                return label
        return 'Tous'

    def _label_membre(self, membre_id: Any) -> str:
        membre = next((m for m in self._membres if int(m['id']) == int(membre_id or 0)), None)
        return f"{membre['nom']} {membre['prenom']}".strip() if membre else '— Aucun —'

    def _build(self) -> None:
        def section(titre: str) -> ctk.CTkFrame:
            bloc_titre = ctk.CTkFrame(self.frame_content, fg_color='transparent')
            bloc_titre.pack(fill='x', pady=(8, 2))
            ctk.CTkLabel(bloc_titre, text=f'── {titre} ' + '─' * 30, anchor='w').pack(fill='x')
            bloc_contenu = ctk.CTkFrame(self.frame_content, fg_color='transparent')
            bloc_contenu.pack(fill='x', padx=4, pady=(0, 4))
            return bloc_contenu

        section_donateur = section('Donateur')

        def champ(parent: Any, label: str, widget: Any) -> ctk.CTkFrame:
            bloc = ctk.CTkFrame(parent, fg_color='transparent')
            bloc.pack(fill='x', pady=4)
            ctk.CTkLabel(bloc, text=label, width=150, anchor='e').pack(side='left', padx=(0, 8))
            widget.pack(side='left', fill='x', expand=True)
            return bloc

        champ(section_donateur, 'Exercice', ctk.CTkOptionMenu(section_donateur, values=list(self._map_exercices), variable=self._var_exercice, width=260))
        type_menu = ctk.CTkSegmentedButton(section_donateur, values=['particulier', 'entreprise'], variable=self._var_type, command=self._toggle_type_fields)
        champ(section_donateur, 'Type donateur', type_menu)
        membre_values = ['— Aucun —'] + [f"{m['nom']} {m['prenom']}".strip() for m in self._membres]
        combo_membre = ctk.CTkOptionMenu(section_donateur, values=membre_values, variable=self._var_membre, width=260, command=lambda _value: self._prefill_membre())
        champ(section_donateur, 'Lier à un adhérent', combo_membre)
        champ(section_donateur, 'Nom / raison sociale *', ctk.CTkEntry(section_donateur, textvariable=self._var_nom, width=260))
        champ(section_donateur, 'Prénom', ctk.CTkEntry(section_donateur, textvariable=self._var_prenom, width=260))
        champ(section_donateur, 'Adresse', ctk.CTkEntry(section_donateur, textvariable=self._var_adresse, width=260))
        champ(section_donateur, 'Code postal', ctk.CTkEntry(section_donateur, textvariable=self._var_cp, width=260))
        champ(section_donateur, 'Ville', ctk.CTkEntry(section_donateur, textvariable=self._var_ville, width=260))
        self._frame_siret = champ(section_donateur, 'SIRET', ctk.CTkEntry(section_donateur, textvariable=self._var_siret, width=260))

        section_don = section('Don')
        champ(section_don, 'Date du don *', ctk.CTkEntry(section_don, textvariable=self._var_date, width=260))
        nature = ctk.CTkSegmentedButton(section_don, values=['argent', 'nature'], variable=self._var_nature, command=self._toggle_nature_fields)
        champ(section_don, 'Nature', nature)
        champ(section_don, 'Montant (€)', ctk.CTkEntry(section_don, textvariable=self._var_montant, width=260))
        self._frame_description = champ(section_don, 'Description', ctk.CTkEntry(section_don, textvariable=self._var_description, width=260))
        self._frame_valeur = champ(section_don, 'Valeur estimée (€)', ctk.CTkEntry(section_don, textvariable=self._var_valeur, width=260))
        champ(section_don, 'Mode versement', ctk.CTkOptionMenu(section_don, values=['cheque', 'virement', 'especes', 'cb', 'autre'], variable=self._var_mode, width=260))

        section_options = section('Options')
        if not self._don:
            ctk.CTkCheckBox(section_options, text='Créer une recette en trésorerie', variable=self._var_creer_treso).pack(anchor='w', padx=158, pady=(4, 0))
            ctk.CTkCheckBox(section_options, text='Générer le reçu immédiatement', variable=self._var_generer_recu).pack(anchor='w', padx=158, pady=(4, 0))
        champ(section_options, 'Commentaire', ctk.CTkEntry(section_options, textvariable=self._var_commentaire, width=260))

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

    def _toggle_type_fields(self, _value: str | None = None) -> None:
        self._mettre_a_jour_visibilite_champs()

    def _toggle_nature_fields(self, _value: str | None = None) -> None:
        self._mettre_a_jour_visibilite_champs()

    def _mettre_a_jour_visibilite_champs(self) -> None:
        if self._var_type.get() == 'entreprise':
            self._frame_siret.pack(fill='x', pady=4)
        else:
            self._frame_siret.pack_forget()
        if self._var_nature.get() == 'nature':
            self._frame_description.pack(fill='x', pady=4)
            self._frame_valeur.pack(fill='x', pady=4)
        else:
            self._frame_description.pack_forget()
            self._frame_valeur.pack_forget()

    def _on_valider(self) -> None:
        if not self._var_nom.get().strip():
            afficher_erreur(self, 'Dons', 'Le nom du donateur est obligatoire.')
            return
        if self._var_nature.get() == 'argent' and not self._var_montant.get().strip():
            afficher_erreur(self, 'Dons', 'Le montant est obligatoire pour un don en argent.')
            return
        membre_id = None
        if self._var_membre.get() != '— Aucun —':
            membre = next((m for m in self._membres if f"{m['nom']} {m['prenom']}".strip() == self._var_membre.get()), None)
            membre_id = int(membre['id']) if membre else None
        exercice_id = self._map_exercices.get(self._var_exercice.get())
        try:
            montant = _parse_optional_float(self._var_montant.get())
            valeur_estimee = _parse_optional_float(self._var_valeur.get())
        except ValueError:
            afficher_erreur(self, 'Dons', 'Montant invalide.')
            return
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
            'donateur_siret': self._var_siret.get().strip() or None if self._var_type.get() == 'entreprise' else None,
            'nature_don': self._var_nature.get().strip(),
            'montant': montant,
            'description_don': self._var_description.get().strip() or None if self._var_nature.get() == 'nature' else None,
            'valeur_estimee': valeur_estimee if self._var_nature.get() == 'nature' else None,
            'mode_versement': self._var_mode.get().strip(),
            'commentaire': self._var_commentaire.get().strip() or None,
            'creer_tresorerie': bool(self._var_creer_treso.get()),
            'generer_recu': bool(self._var_generer_recu.get()),
        }
        self.destroy()
