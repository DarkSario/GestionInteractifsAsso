"""CRUD du module Trésorerie (Phase 6a)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from db.connection import get_connection
from utils.logger import get_logger

logger = get_logger(__name__)

_SUBVENTION_STATUTS = {
    "en_attente": "en_attente",
    "en attente": "en_attente",
    "accordee": "accordee",
    "obtenue": "accordee",
    "refusee": "refusee",
    "refusée": "refusee",
    "annulee": "annulee",
    "annulée": "annulee",
    "partielle": "partielle",
}
_SUBVENTION_STATUTS_OBTENUS = {"accordee", "partielle"}


def _fetch_all(query: str, params: tuple = ()) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def _fetch_one(query: str, params: tuple = ()) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute(query, params).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def _execute(query: str, params: tuple = ()) -> int:
    conn = get_connection()
    try:
        cur = conn.execute(query, params)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def _operation_signed_amount(operation: dict) -> float:
    montant = float(operation.get("montant") or 0)
    statut = operation.get("statut")
    if statut != "valide":
        return 0.0

    type_operation = operation.get("type_operation")
    if type_operation == "recette":
        return montant
    if type_operation == "depense":
        return -montant
    if type_operation == "virement_interne":
        source_module = operation.get("source_module")
        if source_module == "virement_entrant":
            return montant
        return -montant
    return 0.0


# ── Comptes bancaires ─────────────────────────────────────────────────────────


def get_all_comptes(actif_only: bool = True) -> list[dict]:
    query = """
        SELECT *
        FROM comptes_bancaires
    """
    params: list[Any] = []
    if actif_only:
        query += " WHERE actif = 1"
    query += " ORDER BY ordre ASC, id ASC"

    comptes = _fetch_all(query, tuple(params))
    for compte in comptes:
        compte["solde_actuel"] = get_solde_compte(int(compte["id"]))
    return comptes


def get_compte_by_id(compte_id: int) -> dict | None:
    compte = _fetch_one("SELECT * FROM comptes_bancaires WHERE id = ?", (compte_id,))
    if compte:
        compte["solde_actuel"] = get_solde_compte(compte_id)
    return compte


def get_compte_principal() -> dict | None:
    return _fetch_one(
        """
        SELECT *
        FROM comptes_bancaires
        WHERE est_principal = 1 AND actif = 1
        ORDER BY id ASC
        LIMIT 1
        """
    )


def get_compte_caisse() -> dict | None:
    return _fetch_one(
        """
        SELECT *
        FROM comptes_bancaires
        WHERE est_caisse = 1 AND actif = 1
        ORDER BY id ASC
        LIMIT 1
        """
    )


def add_compte(
    nom,
    type_compte,
    solde_initial,
    est_principal,
    est_caisse,
    iban,
    banque,
    ordre,
) -> int:
    compte_id = _execute(
        """
        INSERT INTO comptes_bancaires
        (nom, type_compte, solde_initial, est_principal, est_caisse, iban, banque, ordre)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            nom,
            type_compte,
            float(solde_initial or 0),
            int(bool(est_principal)),
            int(bool(est_caisse)),
            iban,
            banque,
            int(ordre or 0),
        ),
    )
    if est_principal:
        set_compte_principal(compte_id)
    return compte_id


def update_compte(compte_id, **kwargs) -> bool:
    if not kwargs:
        return False

    allowed = {
        "nom": "UPDATE comptes_bancaires SET nom = ? WHERE id = ?",
        "type_compte": "UPDATE comptes_bancaires SET type_compte = ? WHERE id = ?",
        "solde_initial": "UPDATE comptes_bancaires SET solde_initial = ? WHERE id = ?",
        "est_principal": "UPDATE comptes_bancaires SET est_principal = ? WHERE id = ?",
        "est_caisse": "UPDATE comptes_bancaires SET est_caisse = ? WHERE id = ?",
        "iban": "UPDATE comptes_bancaires SET iban = ? WHERE id = ?",
        "banque": "UPDATE comptes_bancaires SET banque = ? WHERE id = ?",
        "actif": "UPDATE comptes_bancaires SET actif = ? WHERE id = ?",
        "ordre": "UPDATE comptes_bancaires SET ordre = ? WHERE id = ?",
    }
    updates: list[tuple[str, Any]] = []
    for key, value in kwargs.items():
        if key not in allowed:
            continue
        updates.append((allowed[key], value))

    if not updates:
        return False

    conn = get_connection()
    try:
        for statement, value in updates:
            conn.execute(statement, (value, compte_id))
        if kwargs.get("est_principal"):
            conn.execute(
                "UPDATE comptes_bancaires SET est_principal = 0 WHERE id != ?",
                (compte_id,),
            )
            conn.execute(
                """
                INSERT OR REPLACE INTO parametres (cle, valeur, description)
                VALUES ('compte_principal_id', ?, 'ID du compte bancaire principal')
                """,
                (str(compte_id),),
            )
        conn.commit()
        return True
    finally:
        conn.close()


def set_compte_principal(compte_id: int) -> bool:
    conn = get_connection()
    try:
        exists = conn.execute(
            "SELECT 1 FROM comptes_bancaires WHERE id = ?", (compte_id,)
        ).fetchone()
        if not exists:
            return False

        conn.execute("UPDATE comptes_bancaires SET est_principal = 0")
        conn.execute(
            "UPDATE comptes_bancaires SET est_principal = 1 WHERE id = ?", (compte_id,)
        )
        conn.execute(
            """
            INSERT OR REPLACE INTO parametres (cle, valeur, description)
            VALUES ('compte_principal_id', ?, 'ID du compte bancaire principal')
            """,
            (str(compte_id),),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def get_solde_compte(compte_id: int) -> float:
    compte = _fetch_one(
        "SELECT solde_initial FROM comptes_bancaires WHERE id = ?", (compte_id,)
    )
    if not compte:
        return 0.0

    operations = _fetch_all(
        """
        SELECT type_operation, montant, statut, source_module
        FROM tresorerie_operations
        WHERE compte_id = ?
        """,
        (compte_id,),
    )

    solde = float(compte.get("solde_initial") or 0)
    for operation in operations:
        solde += _operation_signed_amount(operation)
    return round(solde, 2)


# ── Catégories ────────────────────────────────────────────────────────────────


def get_all_categories(type_categorie=None) -> list[dict]:
    query = "SELECT * FROM tresorerie_categories"
    params: list[Any] = []
    if type_categorie:
        query += " WHERE type_categorie IN (?, 'les_deux')"
        params.append(type_categorie)
    query += " ORDER BY ordre ASC, nom ASC"
    return _fetch_all(query, tuple(params))


def add_categorie(nom, type_categorie) -> int:
    return _execute(
        """
        INSERT INTO tresorerie_categories (nom, type_categorie, est_systeme, ordre)
        VALUES (?, ?, 0, 999)
        """,
        (nom, type_categorie),
    )


def update_categorie(categorie_id, nom) -> bool:
    categorie = _fetch_one(
        "SELECT est_systeme FROM tresorerie_categories WHERE id = ?", (categorie_id,)
    )
    if not categorie or int(categorie.get("est_systeme") or 0) == 1:
        return False

    _execute(
        "UPDATE tresorerie_categories SET nom = ? WHERE id = ?",
        (nom, categorie_id),
    )
    return True


def delete_categorie(categorie_id: int) -> bool:
    categorie = _fetch_one(
        "SELECT est_systeme FROM tresorerie_categories WHERE id = ?", (categorie_id,)
    )
    if not categorie or int(categorie.get("est_systeme") or 0) == 1:
        return False

    usage = _fetch_one(
        "SELECT COUNT(*) AS total FROM tresorerie_operations WHERE categorie_id = ?",
        (categorie_id,),
    )
    if usage and int(usage.get("total") or 0) > 0:
        return False

    _execute("DELETE FROM tresorerie_categories WHERE id = ?", (categorie_id,))
    return True


# ── Opérations ────────────────────────────────────────────────────────────────


def add_operation(
    compte_id,
    type_operation,
    libelle,
    montant,
    date_operation,
    categorie_id,
    mode_paiement,
    numero_facture,
    evenement_id,
    fournisseur_id,
    statut,
    est_automatique,
    source_module,
    source_id,
    commentaire,
) -> int:
    return _execute(
        """
        INSERT INTO tresorerie_operations (
            compte_id, type_operation, libelle, montant, date_operation,
            categorie_id, mode_paiement, numero_facture, evenement_id,
            fournisseur_id, statut, est_automatique, source_module,
            source_id, commentaire
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            compte_id,
            type_operation,
            libelle,
            float(montant or 0),
            date_operation,
            categorie_id,
            mode_paiement,
            numero_facture,
            evenement_id,
            fournisseur_id,
            statut or "valide",
            int(bool(est_automatique)),
            source_module,
            source_id,
            commentaire,
        ),
    )


def update_operation(operation_id, **kwargs) -> bool:
    operation = _fetch_one(
        "SELECT est_automatique FROM tresorerie_operations WHERE id = ?",
        (operation_id,),
    )
    if not operation:
        return False
    if int(operation.get("est_automatique") or 0) == 1:
        return False

    allowed = {
        "compte_id": "UPDATE tresorerie_operations SET compte_id = ? WHERE id = ?",
        "type_operation": "UPDATE tresorerie_operations SET type_operation = ? WHERE id = ?",
        "libelle": "UPDATE tresorerie_operations SET libelle = ? WHERE id = ?",
        "montant": "UPDATE tresorerie_operations SET montant = ? WHERE id = ?",
        "date_operation": "UPDATE tresorerie_operations SET date_operation = ? WHERE id = ?",
        "categorie_id": "UPDATE tresorerie_operations SET categorie_id = ? WHERE id = ?",
        "mode_paiement": "UPDATE tresorerie_operations SET mode_paiement = ? WHERE id = ?",
        "numero_facture": "UPDATE tresorerie_operations SET numero_facture = ? WHERE id = ?",
        "evenement_id": "UPDATE tresorerie_operations SET evenement_id = ? WHERE id = ?",
        "fournisseur_id": "UPDATE tresorerie_operations SET fournisseur_id = ? WHERE id = ?",
        "statut": "UPDATE tresorerie_operations SET statut = ? WHERE id = ?",
        "commentaire": "UPDATE tresorerie_operations SET commentaire = ? WHERE id = ?",
    }
    updates: list[tuple[str, Any]] = []
    for key, value in kwargs.items():
        if key not in allowed:
            continue
        updates.append((allowed[key], value))

    if not updates:
        return False

    conn = get_connection()
    try:
        for statement, value in updates:
            conn.execute(statement, (value, operation_id))
        conn.commit()
    finally:
        conn.close()
    return True


def annuler_operation(operation_id: int) -> bool:
    operation = get_operation_by_id(operation_id)
    if not operation:
        return False

    _execute(
        "UPDATE tresorerie_operations SET statut = 'annule' WHERE id = ?",
        (operation_id,),
    )
    return True


def delete_operation(operation_id: int) -> bool:
    """Supprime définitivement une opération manuelle."""
    operation = _fetch_one(
        "SELECT est_automatique FROM tresorerie_operations WHERE id = ?",
        (operation_id,),
    )
    if not operation:
        return False
    if int(operation.get("est_automatique") or 0) == 1:
        return False
    _execute("DELETE FROM tresorerie_operations WHERE id = ?", (operation_id,))
    return True


def get_operations(
    compte_id=None,
    type_operation=None,
    date_debut=None,
    date_fin=None,
    categorie_id=None,
    statut=None,
    evenement_id=None,
) -> list[dict]:
    query = """
        SELECT o.*, c.nom AS categorie_nom, b.nom AS compte_nom
        FROM tresorerie_operations o
        LEFT JOIN tresorerie_categories c ON c.id = o.categorie_id
        LEFT JOIN comptes_bancaires b ON b.id = o.compte_id
        WHERE 1 = 1
    """
    params: list[Any] = []

    if compte_id:
        query += " AND o.compte_id = ?"
        params.append(compte_id)
    if type_operation:
        query += " AND o.type_operation = ?"
        params.append(type_operation)
    if date_debut:
        query += " AND o.date_operation >= ?"
        params.append(date_debut)
    if date_fin:
        query += " AND o.date_operation <= ?"
        params.append(date_fin)
    if categorie_id:
        query += " AND o.categorie_id = ?"
        params.append(categorie_id)
    if statut:
        query += " AND o.statut = ?"
        params.append(statut)
    if evenement_id:
        query += " AND o.evenement_id = ?"
        params.append(evenement_id)

    query += " ORDER BY o.date_operation DESC, o.id DESC"
    return _fetch_all(query, tuple(params))


def get_operation_by_id(operation_id: int) -> dict | None:
    return _fetch_one(
        """
        SELECT o.*, c.nom AS categorie_nom, b.nom AS compte_nom
        FROM tresorerie_operations o
        LEFT JOIN tresorerie_categories c ON c.id = o.categorie_id
        LEFT JOIN comptes_bancaires b ON b.id = o.compte_id
        WHERE o.id = ?
        """,
        (operation_id,),
    )


def add_virement_interne(
    compte_source_id,
    compte_destination_id,
    montant,
    date_operation,
    libelle,
    commentaire,
) -> tuple[int, int]:
    montant_float = float(montant or 0)
    libelle_base = libelle or "Virement interne"
    conn = get_connection()
    try:
        cur_sortie = conn.execute(
            """
            INSERT INTO tresorerie_operations (
                compte_id, compte_destination_id, type_operation, libelle,
                montant, date_operation, statut, est_automatique,
                source_module, commentaire
            )
            VALUES (?, ?, 'virement_interne', ?, ?, ?, 'valide', 0, 'virement_sortant', ?)
            """,
            (
                compte_source_id,
                compte_destination_id,
                f"{libelle_base} (sortie)",
                montant_float,
                date_operation,
                commentaire,
            ),
        )
        sortie_id = cur_sortie.lastrowid

        cur_entree = conn.execute(
            """
            INSERT INTO tresorerie_operations (
                compte_id, compte_destination_id, type_operation, libelle,
                montant, date_operation, statut, est_automatique,
                source_module, source_id, commentaire
            )
            VALUES (?, ?, 'virement_interne', ?, ?, ?, 'valide', 0, 'virement_entrant', ?, ?)
            """,
            (
                compte_destination_id,
                compte_source_id,
                f"{libelle_base} (entrée)",
                montant_float,
                date_operation,
                sortie_id,
                commentaire,
            ),
        )
        entree_id = cur_entree.lastrowid

        conn.execute(
            "UPDATE tresorerie_operations SET source_id = ? WHERE id = ?",
            (entree_id, sortie_id),
        )
        conn.commit()
        return int(sortie_id), int(entree_id)
    finally:
        conn.close()


# ── Remises de chèques ────────────────────────────────────────────────────────


def add_remise_cheque(
    compte_id,
    date_remise,
    reference,
    commentaire,
    nombre_cheques: int | None = None,
    montant_total: float | None = None,
    numero_bordereau: str | None = None,
) -> int:
    return _execute(
        """
        INSERT INTO remises_cheques (
            compte_id, date_remise, reference, commentaire,
            nombre_cheques, montant_total, numero_bordereau
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            compte_id,
            date_remise,
            reference,
            commentaire,
            int(nombre_cheques) if nombre_cheques is not None else 0,
            float(montant_total) if montant_total is not None else 0,
            numero_bordereau or None,
        ),
    )


def add_cheque_detail(remise_id, nom_tireur, montant, evenement_id, commentaire) -> int:
    return _execute(
        """
        INSERT INTO remises_cheques_detail (remise_id, nom_tireur, montant, evenement_id, commentaire)
        VALUES (?, ?, ?, ?, ?)
        """,
        (remise_id, nom_tireur, float(montant or 0), evenement_id, commentaire),
    )


def finaliser_remise(remise_id: int) -> bool:
    remise = _fetch_one("SELECT * FROM remises_cheques WHERE id = ?", (remise_id,))
    if not remise or remise.get("statut") != "en_attente":
        return False

    details = get_details_remise(remise_id)
    if not details:
        return False

    total = round(sum(float(d.get("montant") or 0) for d in details), 2)
    nb = len(details)

    conn = get_connection()
    try:
        libelle = remise.get("reference") or f"REM-{remise_id:04d}"
        op_cur = conn.execute(
            """
            INSERT INTO tresorerie_operations (
                compte_id, type_operation, libelle, montant, date_operation,
                mode_paiement, statut, est_automatique, source_module,
                remise_cheque_id, commentaire
            )
            VALUES (?, 'recette', ?, ?, ?, 'cheque', 'valide', 0, 'remise_cheque', ?, ?)
            """,
            (
                remise["compte_id"],
                f"Remise de chèques {libelle}",
                total,
                remise["date_remise"],
                remise_id,
                remise.get("commentaire"),
            ),
        )
        operation_id = op_cur.lastrowid

        conn.execute(
            """
            UPDATE remises_cheques
            SET montant_total = ?,
                nombre_cheques = ?,
                statut = 'remis',
                operation_id = ?
            WHERE id = ?
            """,
            (total, nb, operation_id, remise_id),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def get_remises(compte_id=None, statut=None) -> list[dict]:
    query = """
        SELECT r.*, b.nom AS compte_nom
        FROM remises_cheques r
        LEFT JOIN comptes_bancaires b ON b.id = r.compte_id
        WHERE 1 = 1
    """
    params: list[Any] = []
    if compte_id:
        query += " AND r.compte_id = ?"
        params.append(compte_id)
    if statut:
        query += " AND r.statut = ?"
        params.append(statut)
    query += " ORDER BY r.date_remise DESC, r.id DESC"
    return _fetch_all(query, tuple(params))


def get_details_remise(remise_id: int) -> list[dict]:
    return _fetch_all(
        """
        SELECT d.*, e.nom AS evenement_nom
        FROM remises_cheques_detail d
        LEFT JOIN evenements e ON e.id = d.evenement_id
        WHERE d.remise_id = ?
        ORDER BY d.id ASC
        """,
        (remise_id,),
    )


def update_remise_statut(remise_id: int, statut: str) -> bool:
    if statut not in {"en_attente", "remis", "encaisse"}:
        return False

    _execute("UPDATE remises_cheques SET statut = ? WHERE id = ?", (statut, remise_id))
    return True


def update_remise_cheque(remise_id: int, **kwargs) -> bool:
    """Met à jour une remise de chèques."""
    allowed = {
        "date_remise": "UPDATE remises_cheques SET date_remise = ? WHERE id = ?",
        "reference": "UPDATE remises_cheques SET reference = ? WHERE id = ?",
        "commentaire": "UPDATE remises_cheques SET commentaire = ? WHERE id = ?",
        "nombre_cheques": "UPDATE remises_cheques SET nombre_cheques = ? WHERE id = ?",
        "montant_total": "UPDATE remises_cheques SET montant_total = ? WHERE id = ?",
        "numero_bordereau": "UPDATE remises_cheques SET numero_bordereau = ? WHERE id = ?",
        "compte_id": "UPDATE remises_cheques SET compte_id = ? WHERE id = ?",
    }
    updates: list[tuple[str, Any]] = []
    for key, value in kwargs.items():
        if key in allowed:
            updates.append((allowed[key], value))
    if not updates:
        return False
    conn = get_connection()
    try:
        for statement, value in updates:
            conn.execute(statement, (value, remise_id))
        conn.commit()
        return True
    finally:
        conn.close()


# ── Subventions ───────────────────────────────────────────────────────────────


def add_subvention(
    organisme,
    type_organisme,
    annee,
    objet,
    montant_demande,
    date_demande,
    commentaire,
) -> int:
    return _execute(
        """
        INSERT INTO subventions
        (organisme, type_organisme, annee, objet, montant_demande, date_demande, commentaire)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            organisme,
            type_organisme,
            int(annee),
            objet,
            float(montant_demande or 0),
            date_demande,
            commentaire,
        ),
    )


def update_subvention(subvention_id, **kwargs) -> bool:
    if not kwargs:
        return False

    allowed = {
        "organisme": "UPDATE subventions SET organisme = ? WHERE id = ?",
        "type_organisme": "UPDATE subventions SET type_organisme = ? WHERE id = ?",
        "annee": "UPDATE subventions SET annee = ? WHERE id = ?",
        "objet": "UPDATE subventions SET objet = ? WHERE id = ?",
        "montant_demande": "UPDATE subventions SET montant_demande = ? WHERE id = ?",
        "montant_obtenu": "UPDATE subventions SET montant_obtenu = ? WHERE id = ?",
        "statut": "UPDATE subventions SET statut = ? WHERE id = ?",
        "date_demande": "UPDATE subventions SET date_demande = ? WHERE id = ?",
        "date_decision": "UPDATE subventions SET date_decision = ? WHERE id = ?",
        "date_versement": "UPDATE subventions SET date_versement = ? WHERE id = ?",
        "compte_id": "UPDATE subventions SET compte_id = ? WHERE id = ?",
        "operation_id": "UPDATE subventions SET operation_id = ? WHERE id = ?",
        "commentaire": "UPDATE subventions SET commentaire = ? WHERE id = ?",
    }
    updates: list[tuple[str, Any]] = []
    for key, value in kwargs.items():
        if key not in allowed:
            continue
        if key == "statut":
            valeur_normalisee = _SUBVENTION_STATUTS.get(str(value or "").strip().lower())
            if valeur_normalisee is None:
                logger.warning("update_subvention: statut invalide ignoré pour id=%s", subvention_id)
                return False
            value = valeur_normalisee
        updates.append((allowed[key], value))

    if not updates:
        return False

    conn = get_connection()
    try:
        for statement, value in updates:
            conn.execute(statement, (value, subvention_id))
        conn.commit()
    finally:
        conn.close()
    return True


def accorder_subvention(
    subvention_id: int,
    montant_obtenu: float,
    date_decision: str,
    date_versement: str,
    compte_id: int,
) -> bool:
    subvention = _fetch_one("SELECT * FROM subventions WHERE id = ?", (subvention_id,))
    if not subvention:
        return False

    conn = get_connection()
    try:
        op_cur = conn.execute(
            """
            INSERT INTO tresorerie_operations (
                compte_id, type_operation, libelle, montant, date_operation,
                statut, est_automatique, source_module, source_id, commentaire
            )
            VALUES (?, 'recette', ?, ?, ?, 'valide', 1, 'subvention', ?, ?)
            """,
            (
                compte_id,
                f"Subvention {subvention['organisme']}",
                float(montant_obtenu or 0),
                date_versement,
                subvention_id,
                subvention.get("objet"),
            ),
        )
        operation_id = op_cur.lastrowid

        conn.execute(
            """
            UPDATE subventions
            SET statut = 'accordee',
                montant_obtenu = ?,
                date_decision = ?,
                date_versement = ?,
                compte_id = ?,
                operation_id = ?
            WHERE id = ?
            """,
            (
                float(montant_obtenu or 0),
                date_decision,
                date_versement,
                compte_id,
                operation_id,
                subvention_id,
            ),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def get_all_subventions(annee=None, statut=None) -> list[dict]:
    query = "SELECT * FROM subventions WHERE 1 = 1"
    params: list[Any] = []
    if annee:
        query += " AND annee = ?"
        params.append(int(annee))
    if statut:
        query += " AND statut = ?"
        params.append(statut)
    query += " ORDER BY annee DESC, id DESC"
    return _fetch_all(query, tuple(params))


def get_stats_subventions(annee=None) -> dict:
    subventions = get_all_subventions(annee=annee)
    total_demande = round(sum(float(s.get("montant_demande") or 0) for s in subventions), 2)
    total_obtenu = round(sum(float(s.get("montant_obtenu") or 0) for s in subventions), 2)
    nb_accordees = sum(1 for s in subventions if s.get("statut") in _SUBVENTION_STATUTS_OBTENUS)
    nb_en_attente = sum(1 for s in subventions if s.get("statut") == "en_attente")

    return {
        "total_demande": total_demande,
        "total_obtenu": total_obtenu,
        "nb_accordees": nb_accordees,
        "nb_en_attente": nb_en_attente,
    }


# ── Stats globales ────────────────────────────────────────────────────────────


def get_stats_tresorerie(compte_id=None, date_debut=None, date_fin=None) -> dict:
    operations = get_operations(
        compte_id=compte_id,
        date_debut=date_debut,
        date_fin=date_fin,
        statut="valide",
    )

    total_recettes = 0.0
    total_depenses = 0.0
    par_categorie: dict[str, float] = {}

    for operation in operations:
        signed = _operation_signed_amount(operation)
        categorie = operation.get("categorie_nom") or "Sans catégorie"
        par_categorie[categorie] = round(par_categorie.get(categorie, 0.0) + signed, 2)

        if signed >= 0:
            total_recettes += signed
        else:
            total_depenses += abs(signed)

    total_recettes = round(total_recettes, 2)
    total_depenses = round(total_depenses, 2)
    return {
        "total_recettes": total_recettes,
        "total_depenses": total_depenses,
        "solde": round(total_recettes - total_depenses, 2),
        "par_categorie": par_categorie,
    }


def get_evolution_solde(compte_id: int, nb_mois=12) -> list[dict]:
    nb_mois = max(1, int(nb_mois or 1))
    compte = get_compte_by_id(compte_id)
    if not compte:
        return []

    solde_initial = float(compte.get("solde_initial") or 0)
    operations = get_operations(compte_id=compte_id, statut="valide")

    # On cumule mois par mois depuis le plus ancien demandé.
    today = date.today().replace(day=1)
    mois_ref: list[date] = []
    current = today
    for _ in range(nb_mois):
        mois_ref.append(current)
        if current.month == 1:
            current = current.replace(year=current.year - 1, month=12)
        else:
            current = current.replace(month=current.month - 1)
    mois_ref.reverse()

    evolution: list[dict] = []
    for mois in mois_ref:
        if mois.month == 12:
            next_month = mois.replace(year=mois.year + 1, month=1)
        else:
            next_month = mois.replace(month=mois.month + 1)
        fin_mois = next_month - timedelta(days=1)
        fin_mois_str = fin_mois.strftime("%Y-%m-%d")

        solde = solde_initial
        for operation in operations:
            date_operation = str(operation.get("date_operation") or "")
            if date_operation and date_operation <= fin_mois_str:
                solde += _operation_signed_amount(operation)

        evolution.append(
            {
                "mois": mois.strftime("%Y-%m"),
                "solde_fin_mois": round(solde, 2),
            }
        )

    return evolution
