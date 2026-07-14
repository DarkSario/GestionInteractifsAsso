"""CRUD du module Dons."""

from __future__ import annotations

from datetime import date
from typing import Any

from db.connection import get_connection
from db.models.parametres_globaux import get_parametre
from utils.logger import get_logger

logger = get_logger(__name__)

_ALLOWED_FIELDS = {
    'exercice_id', 'date_don', 'type_donateur', 'membre_id', 'donateur_nom',
    'donateur_prenom', 'donateur_adresse', 'donateur_cp', 'donateur_ville',
    'donateur_siret', 'nature_don', 'montant', 'description_don', 'valeur_estimee',
    'mode_versement', 'num_recu', 'statut_recu', 'date_emission_recu', 'tresorerie_id',
    'commentaire',
}

_COLUMN_SQL = {field: field for field in _ALLOWED_FIELDS}


def _sync_operation_tresorerie_don(don_id: int, don_data: dict) -> None:
    """Crée ou met à jour l'opération trésorerie liée à un don en argent."""
    try:
        nature_don = (don_data.get('nature_don') or 'argent').lower()
        montant = float(don_data.get('montant') or 0)
        if nature_don != 'argent' or montant <= 0:
            return

        from db.models.tresorerie import add_operation, get_all_comptes, get_all_categories
        from db.connection import get_connection as _gc

        # Vérifier si une opération existe déjà pour ce don
        _conn = _gc()
        try:
            row = _conn.execute(
                "SELECT id FROM tresorerie_operations WHERE source_module = 'don' AND source_id = ?",
                (don_id,),
            ).fetchone()
            existing_id = row[0] if row else None
        finally:
            _conn.close()

        comptes = get_all_comptes(actif_only=True)
        if not comptes:
            return

        categories = get_all_categories("recette")
        cat_don = next(
            (c for c in categories if "don" in (c.get("nom") or "").lower()),
            None,
        )

        # Libellé du donateur
        prenom = don_data.get('donateur_prenom') or ''
        nom = don_data.get('donateur_nom') or ''
        donateur = f"{prenom} {nom}".strip() or "Donateur"
        date_don = str(don_data.get('date_don') or date.today().isoformat())
        mode = don_data.get('mode_versement') or "autre"
        compte_id = comptes[0]["id"]
        cat_id = int(cat_don["id"]) if cat_don else None
        libelle = f"Don — {donateur}"
        commentaire = "Don automatique enregistré"

        if existing_id:
            _conn2 = _gc()
            try:
                _conn2.execute(
                    """
                    UPDATE tresorerie_operations
                    SET montant = ?, date_operation = ?, mode_paiement = ?,
                        categorie_id = ?, libelle = ?, statut = 'valide'
                    WHERE source_module = 'don' AND source_id = ?
                    """,
                    (montant, date_don, mode, cat_id, libelle, don_id),
                )
                _conn2.commit()
            finally:
                _conn2.close()
        else:
            add_operation(
                compte_id=compte_id,
                type_operation="recette",
                libelle=libelle,
                montant=montant,
                date_operation=date_don,
                categorie_id=cat_id,
                mode_paiement=mode,
                numero_facture=None,
                evenement_id=None,
                fournisseur_id=None,
                statut="valide",
                est_automatique=1,
                source_module="don",
                source_id=don_id,
                commentaire=commentaire,
            )
    except Exception as exc:  # noqa: BLE001
        logger.error("_sync_operation_tresorerie_don (don %s): %s", don_id, exc)



def _fetch_all(query: str, params: tuple[Any, ...] = ()) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def _fetch_one(query: str, params: tuple[Any, ...] = ()) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute(query, params).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_prochain_num_recu(annee: int | str) -> str:
    annee_str = str(annee)
    dernier = _fetch_one(
        'SELECT num_recu FROM dons WHERE num_recu LIKE ? ORDER BY num_recu DESC LIMIT 1',
        (f'{annee_str}-%',),
    )
    if dernier and dernier.get('num_recu'):
        try:
            suffixe = int(str(dernier['num_recu']).split('-', 1)[1]) + 1
            return f'{annee_str}-{suffixe:03d}'
        except (IndexError, ValueError):
            pass

    depart = get_parametre('recu_don_num_depart', f'{annee_str}-001').strip()
    if depart.startswith(f'{annee_str}-'):
        return depart
    return f'{annee_str}-001'


def add_don(**kwargs) -> int:
    champs = {k: kwargs.get(k) for k in _ALLOWED_FIELDS if k in kwargs}
    date_don = str(champs.get('date_don') or date.today().isoformat())
    annee = date_don[:4] if len(date_don) >= 4 else str(date.today().year)
    champs.setdefault('date_don', date_don)
    champs.setdefault('type_donateur', 'particulier')
    champs.setdefault('nature_don', 'argent')
    champs.setdefault('statut_recu', 'en_attente')
    champs.setdefault('num_recu', get_prochain_num_recu(annee))

    colonnes = ', '.join(_COLUMN_SQL[cle] for cle in champs)
    placeholders = ', '.join(['?'] * len(champs))
    valeurs = [champs[cle] for cle in champs]

    conn = get_connection()
    try:
        cur = conn.execute(
            f'INSERT INTO dons ({colonnes}) VALUES ({placeholders})',
            tuple(valeurs),
        )
        conn.commit()
        don_id = int(cur.lastrowid)
    finally:
        conn.close()

    if don_id:
        _sync_operation_tresorerie_don(don_id, champs)
    return don_id


def get_all_dons(filters: dict[str, Any] | None = None) -> list[dict]:
    filters = filters or {}
    query = """
        SELECT d.*, m.nom AS membre_nom, m.prenom AS membre_prenom
        FROM dons d
        LEFT JOIN membres m ON m.id = d.membre_id
        WHERE 1 = 1
    """
    params: list[Any] = []

    exercice_id = filters.get('exercice_id')
    if exercice_id not in (None, '', 'tous'):
        query += ' AND d.exercice_id = ?'
        params.append(int(exercice_id))

    type_donateur = (filters.get('type_donateur') or 'tous').strip().lower()
    if type_donateur not in {'', 'tous'}:
        query += ' AND d.type_donateur = ?'
        params.append(type_donateur)

    statut = (filters.get('statut_recu') or filters.get('statut') or 'tous').strip().lower()
    if statut not in {'', 'tous'}:
        query += ' AND d.statut_recu = ?'
        params.append(statut)

    date_debut = filters.get('date_debut')
    if date_debut:
        query += ' AND d.date_don >= ?'
        params.append(str(date_debut))

    date_fin = filters.get('date_fin')
    if date_fin:
        query += ' AND d.date_don <= ?'
        params.append(str(date_fin))

    query += ' ORDER BY d.date_don DESC, d.id DESC'
    return _fetch_all(query, tuple(params))


def get_don_by_id(don_id: int) -> dict | None:
    return _fetch_one(
        """
        SELECT d.*, m.nom AS membre_nom, m.prenom AS membre_prenom
        FROM dons d
        LEFT JOIN membres m ON m.id = d.membre_id
        WHERE d.id = ?
        """,
        (don_id,),
    )


def update_don(don_id: int, **kwargs) -> bool:
    champs = {k: kwargs.get(k) for k in _ALLOWED_FIELDS if k in kwargs}
    if not champs:
        return False
    champs['updated_at'] = "datetime('now')"

    assignees: list[str] = []
    valeurs: list[Any] = []
    for cle, valeur in champs.items():
        if cle == 'updated_at' and valeur == "datetime('now')":
            assignees.append("updated_at = datetime('now')")
            continue
        assignees.append(f'{_COLUMN_SQL[cle]} = ?')
        valeurs.append(valeur)
    valeurs.append(don_id)

    conn = get_connection()
    try:
        conn.execute(
            f"UPDATE dons SET {', '.join(assignees)} WHERE id = ?",
            tuple(valeurs),
        )
        conn.commit()
        ok = True
    except Exception as exc:  # noqa: BLE001
        logger.error('update_don: %s', exc)
        return False
    finally:
        conn.close()

    if ok:
        don = get_don_by_id(don_id)
        if don:
            _sync_operation_tresorerie_don(don_id, don)
    return ok


def delete_don(don_id: int) -> bool:
    conn = get_connection()
    try:
        conn.execute('DELETE FROM dons WHERE id = ?', (don_id,))
        conn.commit()
        return True
    finally:
        conn.close()


def marquer_recu_emis(don_id: int) -> bool:
    return update_don(don_id, statut_recu='emis', date_emission_recu=date.today().isoformat())


def get_stats_dons(exercice_id: int | None = None) -> dict:
    query = """
        SELECT
            COUNT(*) AS total,
            COUNT(
                DISTINCT COALESCE(
                    CASE WHEN membre_id IS NOT NULL THEN 'membre:' || CAST(membre_id AS TEXT) END,
                    'donateur:' || TRIM(COALESCE(donateur_nom, '') || '|' || COALESCE(donateur_prenom, ''))
                )
            ) AS nb_donateurs,
            COALESCE(SUM(CASE WHEN nature_don = 'argent' THEN COALESCE(montant, 0) ELSE 0 END), 0) AS total_argent,
            COALESCE(SUM(CASE WHEN nature_don = 'nature' THEN COALESCE(valeur_estimee, 0) ELSE 0 END), 0) AS total_nature,
            COALESCE(
                SUM(
                    CASE
                        WHEN nature_don = 'nature' THEN COALESCE(valeur_estimee, 0)
                        ELSE COALESCE(montant, 0)
                    END
                ),
                0
            ) AS total_montants
        FROM dons
        WHERE 1 = 1
    """
    params: list[Any] = []
    if exercice_id is not None:
        query += ' AND exercice_id = ?'
        params.append(exercice_id)

    row = _fetch_one(query, tuple(params)) or {}
    return {
        'total': int(row.get('total') or 0),
        'nb_donateurs': int(row.get('nb_donateurs') or 0),
        'total_argent': round(float(row.get('total_argent') or 0), 2),
        'total_nature': round(float(row.get('total_nature') or 0), 2),
        'montant_total': round(float(row.get('total_montants') or 0), 2),
    }
