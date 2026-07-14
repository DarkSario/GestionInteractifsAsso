"""Requêtes unifiées pour les remboursements de frais."""

from __future__ import annotations

from typing import Any

from db.connection import get_connection
from utils.logger import get_logger

logger = get_logger(__name__)


def _creer_operation_remboursement_tombola(lot_info: dict, mode: str, date_remboursement: str) -> None:
    """Crée une opération de dépense dans la trésorerie pour un remboursement de lot tombola."""
    try:
        montant_avance = lot_info.get('montant_avance')
        if not montant_avance or float(montant_avance) <= 0:
            return

        from db.models.tresorerie import add_operation, get_all_comptes
        comptes = get_all_comptes(actif_only=True)
        if not comptes:
            return

        lot_id = lot_info.get('id')
        beneficiaire_nom = (
            f"{lot_info.get('membre_nom', '') or ''} {lot_info.get('membre_prenom', '') or ''}".strip()
            or "Bénéficiaire inconnu"
        )
        description = lot_info.get('description') or f"Lot #{lot_id}"

        add_operation(
            compte_id=comptes[0]["id"],
            type_operation="depense",
            libelle=f"Remboursement lot tombola — {beneficiaire_nom}",
            montant=float(montant_avance),
            date_operation=date_remboursement,
            categorie_id=None,
            mode_paiement=mode or "especes",
            numero_facture=None,
            evenement_id=lot_info.get('evenement_id'),
            fournisseur_id=None,
            statut="valide",
            est_automatique=1,
            source_module="tombola_remboursement",
            source_id=lot_id,
            commentaire=f"Remboursement automatique lot tombola #{lot_id} — {description}",
        )
    except Exception as exc:  # noqa: BLE001
        logger.error('_creer_operation_remboursement_tombola: %s', exc)


_QUERY_EVENEMENTS = """
    SELECT
        'evenement' AS source,
        d.id AS source_id,
        'evenement:' || d.id AS remboursement_id,
        d.date AS date_piece,
        d.libelle AS description,
        d.montant AS montant,
        COALESCE(d.remboursement_statut, 'non_applicable') AS remboursement_statut,
        d.remboursement_date,
        d.remboursement_mode,
        d.remboursement_reference,
        d.avance_par_membre_id AS membre_id,
        m.nom AS membre_nom,
        m.prenom AS membre_prenom,
        e.nom AS nom_evenement,
        e.date_debut AS date_evenement,
        d.commentaire
    FROM evenement_depenses d
    LEFT JOIN membres m ON m.id = d.avance_par_membre_id
    LEFT JOIN evenements e ON e.id = d.evenement_id
    WHERE d.avance_par_membre_id IS NOT NULL
       OR COALESCE(d.remboursement_statut, 'non_applicable') != 'non_applicable'
"""

_QUERY_TRESORERIE = """
    SELECT
        'tresorerie' AS source,
        o.id AS source_id,
        'tresorerie:' || o.id AS remboursement_id,
        o.date_operation AS date_piece,
        o.libelle AS description,
        o.montant AS montant,
        COALESCE(o.remboursement_statut, 'non_applicable') AS remboursement_statut,
        o.remboursement_date,
        o.remboursement_mode,
        o.remboursement_reference,
        o.avance_par_membre_id AS membre_id,
        m.nom AS membre_nom,
        m.prenom AS membre_prenom,
        COALESCE(e.nom, 'Fonctionnement association') AS nom_evenement,
        COALESCE(e.date_debut, o.date_operation) AS date_evenement,
        o.commentaire
    FROM tresorerie_operations o
    LEFT JOIN membres m ON m.id = o.avance_par_membre_id
    LEFT JOIN evenements e ON e.id = o.evenement_id
    WHERE o.type_operation = 'depense'
      AND (
        o.avance_par_membre_id IS NOT NULL
        OR COALESCE(o.remboursement_statut, 'non_applicable') != 'non_applicable'
      )
"""


_QUERY_TOMBOLA = """
    SELECT
        'tombola' AS source,
        tl.id AS source_id,
        'tombola:' || tl.id AS remboursement_id,
        tl.remboursement_date AS date_piece,
        tl.description AS description,
        tl.montant_avance AS montant,
        COALESCE(tl.remboursement_statut, 'non_applicable') AS remboursement_statut,
        tl.remboursement_date,
        tl.remboursement_mode,
        tl.remboursement_reference,
        tl.acheteur_membre_id AS membre_id,
        m.nom AS membre_nom,
        m.prenom AS membre_prenom,
        COALESCE(e.nom, 'Tombola') AS nom_evenement,
        COALESCE(e.date_debut, tl.remboursement_date) AS date_evenement,
        tl.remarque AS commentaire
    FROM tombola_lots tl
    LEFT JOIN membres m ON m.id = tl.acheteur_membre_id
    LEFT JOIN evenements e ON e.id = tl.evenement_id
    WHERE tl.acheteur_membre_id IS NOT NULL
      AND COALESCE(tl.remboursement_statut, 'non_applicable') != 'non_applicable'
"""


def _fetch_all(query: str, params: tuple[Any, ...] = ()) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def _query_unifiee(filters: dict[str, Any] | None = None) -> tuple[str, list[Any]]:
    filters = filters or {}

    # Vérifier si la table tombola_lots dispose des nouvelles colonnes
    try:
        from db.connection import get_connection as _gc
        _conn = _gc()
        try:
            _cols = {row['name'] for row in _conn.execute("PRAGMA table_info(tombola_lots)").fetchall()}
        finally:
            _conn.close()
        _tombola_enrichie = 'remboursement_statut' in _cols
    except Exception:
        _tombola_enrichie = False

    if _tombola_enrichie:
        union_body = f"{_QUERY_EVENEMENTS}\nUNION ALL\n{_QUERY_TRESORERIE}\nUNION ALL\n{_QUERY_TOMBOLA}"
    else:
        union_body = f"{_QUERY_EVENEMENTS}\nUNION ALL\n{_QUERY_TRESORERIE}"

    query = f"""
        SELECT *
        FROM (
            {union_body}
        ) r
        WHERE 1 = 1
    """
    params: list[Any] = []

    membre_id = filters.get('membre_id') or filters.get('adherent_id')
    if membre_id:
        query += ' AND r.membre_id = ?'
        params.append(int(membre_id))

    date_debut = filters.get('date_debut')
    if date_debut:
        query += ' AND COALESCE(r.date_piece, "") >= ?'
        params.append(str(date_debut))

    date_fin = filters.get('date_fin')
    if date_fin:
        query += ' AND COALESCE(r.date_piece, "") <= ?'
        params.append(str(date_fin))

    statut = (filters.get('statut') or 'tous').strip().lower()
    if statut not in {'', 'tous'}:
        query += ' AND r.remboursement_statut = ?'
        params.append(statut)

    source = (filters.get('source') or 'tous').strip().lower()
    if source not in {'', 'tous'}:
        query += ' AND r.source = ?'
        params.append(source)

    query += ' ORDER BY COALESCE(r.date_piece, "") DESC, r.source_id DESC'
    return query, params


def _normaliser_ligne(row: dict) -> dict:
    row = dict(row)
    nom = (row.get('membre_nom') or '').strip()
    prenom = (row.get('membre_prenom') or '').strip()
    row['beneficiaire'] = f"{nom} {prenom}".strip() or '—'
    return row


def get_remboursements_en_attente() -> list[dict]:
    return get_remboursements_all({'statut': 'en_attente'})


def get_remboursements_all(filters: dict[str, Any] | None = None) -> list[dict]:
    query, params = _query_unifiee(filters)
    return [_normaliser_ligne(row) for row in _fetch_all(query, tuple(params))]


def get_remboursement_by_unified_id(remboursement_id: str | int) -> dict | None:
    identifiant = str(remboursement_id)
    if ':' in identifiant:
        source, source_id = identifiant.split(':', 1)
        lignes = get_remboursements_all({'source': source})
        for ligne in lignes:
            if str(ligne.get('source_id')) == source_id:
                return ligne
        return None

    for ligne in get_remboursements_all():
        if str(ligne.get('source_id')) == identifiant:
            return ligne
    return None


def marquer_rembourse(
    source: str,
    identifiant: int,
    mode: str,
    reference: str | None,
    date: str,
    commentaire: str | None = None,
) -> bool:
    tables = {
        'evenement': 'evenement_depenses',
        'tresorerie': 'tresorerie_operations',
    }

    if source == 'tombola':
        try:
            from db.models.tombola import marquer_rembourse_lot
            from db.connection import get_connection as _gc

            # Récupérer les infos du lot avant remboursement
            _conn = _gc()
            try:
                _lot = _conn.execute(
                    """
                    SELECT tl.id, tl.montant_avance, tl.evenement_id, tl.description,
                           m.nom AS membre_nom, m.prenom AS membre_prenom
                    FROM tombola_lots tl
                    LEFT JOIN membres m ON m.id = tl.acheteur_membre_id
                    WHERE tl.id = ?
                    """,
                    (identifiant,),
                ).fetchone()
                lot_info = dict(_lot) if _lot else {}
            finally:
                _conn.close()

            ok = marquer_rembourse_lot(identifiant, mode, reference, date)
            if ok:
                if not lot_info:
                    logger.warning("marquer_rembourse (tombola): lot #%s introuvable, pas d'opération trésorerie créée", identifiant)
                else:
                    _creer_operation_remboursement_tombola(lot_info, mode, date)
            return ok
        except (ImportError, OSError) as exc:
            logger.error('marquer_rembourse (tombola): %s', exc)
            return False

    table = tables.get(source, '')
    if not table:
        return False

    conn = get_connection()
    try:
        conn.execute(
            f"""
            UPDATE {table}
            SET remboursement_statut = 'rembourse',
                remboursement_date = ?,
                remboursement_mode = ?,
                remboursement_reference = ?,
                commentaire = ?
            WHERE id = ?
            """,
            (date, mode or None, reference or None, commentaire or None, identifiant),
        )
        conn.commit()
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error('marquer_rembourse: %s', exc)
        return False
    finally:
        conn.close()


def get_stats_remboursements() -> dict:
    lignes = get_remboursements_en_attente()
    par_adherent: dict[int, dict[str, Any]] = {}
    total = 0.0
    for ligne in lignes:
        montant = float(ligne.get('montant') or 0)
        total += montant
        membre_id = int(ligne.get('membre_id') or 0)
        if membre_id not in par_adherent:
            par_adherent[membre_id] = {
                'membre_id': membre_id,
                'beneficiaire': ligne.get('beneficiaire') or '—',
                'montant_total': 0.0,
                'nb_remboursements': 0,
            }
        par_adherent[membre_id]['montant_total'] += montant
        par_adherent[membre_id]['nb_remboursements'] += 1

    return {
        'total_en_attente': round(total, 2),
        'nb_remboursements': len(lignes),
        'par_adherent': sorted(
            par_adherent.values(),
            key=lambda item: (item['beneficiaire'].lower(), item['membre_id']),
        ),
    }
