"""CRUD pour le module Trésorerie."""

from __future__ import annotations

from db.connection import get_connection
from utils.logger import get_logger

logger = get_logger(__name__)


# ── Configuration ─────────────────────────────────────────────────────────────


def get_config() -> dict:
    """Retourne la configuration de l'association (1 seule ligne)."""
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT id, nom_asso, exercice, date_debut, date_fin,
                   solde_ouverture, disponible_banque, cloture, solde_report
            FROM config
            ORDER BY id ASC
            LIMIT 1
            """
        ).fetchone()
        return dict(row) if row else {}
    finally:
        conn.close()


def update_config(
    nom_asso: str,
    exercice: str,
    date_debut: str,
    date_fin: str,
    solde_ouverture: float,
    disponible_banque: float,
) -> None:
    """Met à jour (ou insère) la configuration."""
    conn = get_connection()
    try:
        existing = conn.execute("SELECT id FROM config LIMIT 1").fetchone()
        if existing:
            conn.execute(
                """
                UPDATE config
                SET nom_asso=?, exercice=?, date_debut=?, date_fin=?,
                    solde_ouverture=?, disponible_banque=?
                WHERE id=?
                """,
                (
                    nom_asso,
                    exercice,
                    date_debut,
                    date_fin,
                    solde_ouverture,
                    disponible_banque,
                    existing["id"],
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO config
                    (nom_asso, exercice, date_debut, date_fin,
                     solde_ouverture, disponible_banque)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    nom_asso,
                    exercice,
                    date_debut,
                    date_fin,
                    solde_ouverture,
                    disponible_banque,
                ),
            )
        conn.commit()
    finally:
        conn.close()


# ── Dons et subventions ───────────────────────────────────────────────────────


def get_all_dons(exercice: str | None = None) -> list[dict]:
    """Retourne tous les dons/subventions, filtrés optionnellement par exercice."""
    conn = get_connection()
    try:
        if exercice:
            rows = conn.execute(
                """
                SELECT d.id, d.date, d.source, d.montant, d.type,
                       d.justificatif, d.commentaire,
                       d.membre_id,
                       m.nom || ' ' || m.prenom AS membre_nom
                FROM dons_subventions d
                LEFT JOIN membres m ON m.id = d.membre_id
                WHERE strftime('%Y', d.date) = ?
                ORDER BY d.date DESC
                """,
                (exercice,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT d.id, d.date, d.source, d.montant, d.type,
                       d.justificatif, d.commentaire,
                       d.membre_id,
                       m.nom || ' ' || m.prenom AS membre_nom
                FROM dons_subventions d
                LEFT JOIN membres m ON m.id = d.membre_id
                ORDER BY d.date DESC
                """
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def add_don(
    date: str,
    source: str,
    montant: float,
    type_don: str,
    justificatif: str | None,
    commentaire: str | None,
    membre_id: int | None = None,
) -> int:
    """Ajoute un don/subvention et retourne son identifiant."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO dons_subventions
                (date, source, montant, type, justificatif, commentaire, membre_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (date, source, montant, type_don, justificatif, commentaire, membre_id),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_don(
    don_id: int,
    date: str,
    source: str,
    montant: float,
    type_don: str,
    justificatif: str | None,
    commentaire: str | None,
    membre_id: int | None = None,
) -> bool:
    """Met à jour un don/subvention. Retourne True si une ligne a été modifiée."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            UPDATE dons_subventions
            SET date=?, source=?, montant=?, type=?,
                justificatif=?, commentaire=?, membre_id=?
            WHERE id=?
            """,
            (date, source, montant, type_don, justificatif, commentaire, membre_id, don_id),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def delete_don(don_id: int) -> bool:
    """Supprime un don/subvention. Retourne True si une ligne a été supprimée."""
    conn = get_connection()
    try:
        cur = conn.execute("DELETE FROM dons_subventions WHERE id=?", (don_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# ── Dépenses régulières ───────────────────────────────────────────────────────


def get_all_depenses_regulieres(exercice: str | None = None) -> list[dict]:
    """Retourne toutes les dépenses régulières."""
    conn = get_connection()
    try:
        if exercice:
            rows = conn.execute(
                """
                SELECT d.id, d.date_depense, d.categorie, d.montant,
                       d.fournisseur, d.moyen_paiement, d.numero_cheque,
                       d.numero_facture, d.statut_reglement, d.commentaire,
                       d.membre_id, d.statut_remboursement,
                       m.nom || ' ' || m.prenom AS membre_nom
                FROM depenses_regulieres d
                LEFT JOIN membres m ON m.id = d.membre_id
                WHERE strftime('%Y', d.date_depense) = ?
                ORDER BY d.date_depense DESC
                """,
                (exercice,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT d.id, d.date_depense, d.categorie, d.montant,
                       d.fournisseur, d.moyen_paiement, d.numero_cheque,
                       d.numero_facture, d.statut_reglement, d.commentaire,
                       d.membre_id, d.statut_remboursement,
                       m.nom || ' ' || m.prenom AS membre_nom
                FROM depenses_regulieres d
                LEFT JOIN membres m ON m.id = d.membre_id
                ORDER BY d.date_depense DESC
                """
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def add_depense_reguliere(
    date_depense: str,
    categorie: str,
    montant: float,
    fournisseur: str | None,
    moyen_paiement: str | None,
    numero_cheque: str | None,
    numero_facture: str | None,
    statut_reglement: str,
    commentaire: str | None,
    membre_id: int | None = None,
    statut_remboursement: str = "non concerné",
) -> int:
    """Ajoute une dépense régulière et retourne son identifiant."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO depenses_regulieres
                (date_depense, categorie, montant, fournisseur,
                 moyen_paiement, numero_cheque, numero_facture,
                 statut_reglement, commentaire, membre_id, statut_remboursement)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                date_depense,
                categorie,
                montant,
                fournisseur,
                moyen_paiement,
                numero_cheque,
                numero_facture,
                statut_reglement,
                commentaire,
                membre_id,
                statut_remboursement,
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_depense_reguliere(
    depense_id: int,
    date_depense: str,
    categorie: str,
    montant: float,
    fournisseur: str | None,
    moyen_paiement: str | None,
    numero_cheque: str | None,
    numero_facture: str | None,
    statut_reglement: str,
    commentaire: str | None,
    membre_id: int | None = None,
    statut_remboursement: str = "non concerné",
) -> bool:
    """Met à jour une dépense régulière."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            UPDATE depenses_regulieres
            SET date_depense=?, categorie=?, montant=?, fournisseur=?,
                moyen_paiement=?, numero_cheque=?, numero_facture=?,
                statut_reglement=?, commentaire=?, membre_id=?,
                statut_remboursement=?
            WHERE id=?
            """,
            (
                date_depense,
                categorie,
                montant,
                fournisseur,
                moyen_paiement,
                numero_cheque,
                numero_facture,
                statut_reglement,
                commentaire,
                membre_id,
                statut_remboursement,
                depense_id,
            ),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def delete_depense_reguliere(depense_id: int) -> bool:
    """Supprime une dépense régulière."""
    conn = get_connection()
    try:
        cur = conn.execute(
            "DELETE FROM depenses_regulieres WHERE id=?", (depense_id,)
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# ── Dépenses diverses ─────────────────────────────────────────────────────────


def get_all_depenses_diverses(exercice: str | None = None) -> list[dict]:
    """Retourne toutes les dépenses diverses."""
    conn = get_connection()
    try:
        if exercice:
            rows = conn.execute(
                """
                SELECT d.id, d.date_depense, d.categorie, d.montant,
                       d.fournisseur, d.moyen_paiement, d.numero_cheque,
                       d.numero_facture, d.statut_reglement, d.commentaire,
                       d.membre_id, d.statut_remboursement,
                       m.nom || ' ' || m.prenom AS membre_nom
                FROM depenses_diverses d
                LEFT JOIN membres m ON m.id = d.membre_id
                WHERE strftime('%Y', d.date_depense) = ?
                ORDER BY d.date_depense DESC
                """,
                (exercice,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT d.id, d.date_depense, d.categorie, d.montant,
                       d.fournisseur, d.moyen_paiement, d.numero_cheque,
                       d.numero_facture, d.statut_reglement, d.commentaire,
                       d.membre_id, d.statut_remboursement,
                       m.nom || ' ' || m.prenom AS membre_nom
                FROM depenses_diverses d
                LEFT JOIN membres m ON m.id = d.membre_id
                ORDER BY d.date_depense DESC
                """
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def add_depense_diverse(
    date_depense: str,
    categorie: str,
    montant: float,
    fournisseur: str | None,
    moyen_paiement: str | None,
    numero_cheque: str | None,
    numero_facture: str | None,
    statut_reglement: str,
    commentaire: str | None,
    membre_id: int | None = None,
    statut_remboursement: str = "non concerné",
) -> int:
    """Ajoute une dépense diverse et retourne son identifiant."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO depenses_diverses
                (date_depense, categorie, montant, fournisseur,
                 moyen_paiement, numero_cheque, numero_facture,
                 statut_reglement, commentaire, membre_id, statut_remboursement)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                date_depense,
                categorie,
                montant,
                fournisseur,
                moyen_paiement,
                numero_cheque,
                numero_facture,
                statut_reglement,
                commentaire,
                membre_id,
                statut_remboursement,
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_depense_diverse(
    depense_id: int,
    date_depense: str,
    categorie: str,
    montant: float,
    fournisseur: str | None,
    moyen_paiement: str | None,
    numero_cheque: str | None,
    numero_facture: str | None,
    statut_reglement: str,
    commentaire: str | None,
    membre_id: int | None = None,
    statut_remboursement: str = "non concerné",
) -> bool:
    """Met à jour une dépense diverse."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            UPDATE depenses_diverses
            SET date_depense=?, categorie=?, montant=?, fournisseur=?,
                moyen_paiement=?, numero_cheque=?, numero_facture=?,
                statut_reglement=?, commentaire=?, membre_id=?,
                statut_remboursement=?
            WHERE id=?
            """,
            (
                date_depense,
                categorie,
                montant,
                fournisseur,
                moyen_paiement,
                numero_cheque,
                numero_facture,
                statut_reglement,
                commentaire,
                membre_id,
                statut_remboursement,
                depense_id,
            ),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def delete_depense_diverse(depense_id: int) -> bool:
    """Supprime une dépense diverse."""
    conn = get_connection()
    try:
        cur = conn.execute(
            "DELETE FROM depenses_diverses WHERE id=?", (depense_id,)
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# ── Dépôts et retraits bancaires ──────────────────────────────────────────────


def get_all_depots_retraits(exercice: str | None = None) -> list[dict]:
    """Retourne tous les dépôts et retraits bancaires."""
    conn = get_connection()
    try:
        if exercice:
            rows = conn.execute(
                """
                SELECT id, date, type, montant, reference,
                       banque, pointe, commentaire
                FROM depots_retraits_banque
                WHERE strftime('%Y', date) = ?
                ORDER BY date DESC
                """,
                (exercice,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, date, type, montant, reference,
                       banque, pointe, commentaire
                FROM depots_retraits_banque
                ORDER BY date DESC
                """
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def add_depot_retrait(
    date: str,
    type_mouvement: str,
    montant: float,
    reference: str | None,
    banque: str | None,
    pointe: int,
    commentaire: str | None,
) -> int:
    """Ajoute un dépôt ou retrait bancaire et retourne son identifiant."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO depots_retraits_banque
                (date, type, montant, reference, banque, pointe, commentaire)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (date, type_mouvement, montant, reference, banque, pointe, commentaire),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_depot_retrait(
    mouvement_id: int,
    date: str,
    type_mouvement: str,
    montant: float,
    reference: str | None,
    banque: str | None,
    pointe: int,
    commentaire: str | None,
) -> bool:
    """Met à jour un dépôt/retrait bancaire."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            UPDATE depots_retraits_banque
            SET date=?, type=?, montant=?, reference=?,
                banque=?, pointe=?, commentaire=?
            WHERE id=?
            """,
            (date, type_mouvement, montant, reference, banque, pointe, commentaire, mouvement_id),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def delete_depot_retrait(mouvement_id: int) -> bool:
    """Supprime un dépôt/retrait bancaire."""
    conn = get_connection()
    try:
        cur = conn.execute(
            "DELETE FROM depots_retraits_banque WHERE id=?", (mouvement_id,)
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# ── Rétrocessions aux écoles ──────────────────────────────────────────────────


def get_all_retrocessions(exercice: str | None = None) -> list[dict]:
    """Retourne toutes les rétrocessions aux écoles."""
    conn = get_connection()
    try:
        if exercice:
            rows = conn.execute(
                """
                SELECT id, date, ecole, montant, commentaire
                FROM retrocessions_ecoles
                WHERE strftime('%Y', date) = ?
                ORDER BY date DESC
                """,
                (exercice,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, date, ecole, montant, commentaire
                FROM retrocessions_ecoles
                ORDER BY date DESC
                """
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def add_retrocession(
    date: str,
    ecole: str,
    montant: float,
    commentaire: str | None,
) -> int:
    """Ajoute une rétrocession et retourne son identifiant."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO retrocessions_ecoles (date, ecole, montant, commentaire)
            VALUES (?, ?, ?, ?)
            """,
            (date, ecole, montant, commentaire),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def delete_retrocession(retrocession_id: int) -> bool:
    """Supprime une rétrocession."""
    conn = get_connection()
    try:
        cur = conn.execute(
            "DELETE FROM retrocessions_ecoles WHERE id=?", (retrocession_id,)
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# ── Journal général ───────────────────────────────────────────────────────────


def get_journal_general(exercice: str | None = None) -> list[dict]:
    """Retourne toutes les opérations classées par date (journal général).

    Chaque entrée comporte les clés :
    - date, libelle, categorie, montant, sens (recette/depense/banque),
      origine (table source), origine_id.
    """
    conn = get_connection()
    try:
        filtre_annee = "AND strftime('%Y', date) = ?" if exercice else ""
        params_annee: tuple = (exercice,) if exercice else ()

        filtre_annee_depense = (
            "AND strftime('%Y', date_depense) = ?" if exercice else ""
        )

        # Dons / subventions → recettes
        dons = conn.execute(
            f"""
            SELECT date, source AS libelle, type AS categorie, montant,
                   'recette' AS sens, 'dons_subventions' AS origine, id AS origine_id
            FROM dons_subventions
            WHERE 1=1 {filtre_annee}
            ORDER BY date ASC
            """,
            params_annee,
        ).fetchall()

        # Dépenses régulières → dépenses
        dep_reg = conn.execute(
            f"""
            SELECT date_depense AS date, categorie AS libelle,
                   categorie, montant,
                   'depense' AS sens, 'depenses_regulieres' AS origine, id AS origine_id
            FROM depenses_regulieres
            WHERE 1=1 {filtre_annee_depense}
            ORDER BY date_depense ASC
            """,
            params_annee,
        ).fetchall()

        # Dépenses diverses → dépenses
        dep_div = conn.execute(
            f"""
            SELECT date_depense AS date, categorie AS libelle,
                   categorie, montant,
                   'depense' AS sens, 'depenses_diverses' AS origine, id AS origine_id
            FROM depenses_diverses
            WHERE 1=1 {filtre_annee_depense}
            ORDER BY date_depense ASC
            """,
            params_annee,
        ).fetchall()

        # Dépôts/retraits → banque
        banque = conn.execute(
            f"""
            SELECT date, reference AS libelle, type AS categorie, montant,
                   type AS sens, 'depots_retraits_banque' AS origine, id AS origine_id
            FROM depots_retraits_banque
            WHERE 1=1 {filtre_annee}
            ORDER BY date ASC
            """,
            params_annee,
        ).fetchall()

        # Rétrocessions → dépenses
        retro = conn.execute(
            f"""
            SELECT date, ecole AS libelle, 'rétrocession' AS categorie, montant,
                   'depense' AS sens, 'retrocessions_ecoles' AS origine, id AS origine_id
            FROM retrocessions_ecoles
            WHERE 1=1 {filtre_annee}
            ORDER BY date ASC
            """,
            params_annee,
        ).fetchall()

        all_rows = (
            [dict(r) for r in dons]
            + [dict(r) for r in dep_reg]
            + [dict(r) for r in dep_div]
            + [dict(r) for r in banque]
            + [dict(r) for r in retro]
        )
        all_rows.sort(key=lambda r: r.get("date") or "")
        return all_rows
    finally:
        conn.close()
