-- Phase 13 — UX & formulaires + corrections

CREATE TABLE IF NOT EXISTS tombola_solidaire_participations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evenement_id INTEGER NOT NULL REFERENCES evenements(id) ON DELETE CASCADE,
    nom TEXT NOT NULL,
    prenom TEXT NOT NULL,
    telephone TEXT,
    montant_don REAL NOT NULL DEFAULT 0,
    date_participation TEXT DEFAULT (date('now')),
    est_gagnant INTEGER DEFAULT 0,
    commentaire TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Valeur alignée avec MODULES_EVENEMENT_PAR_DEFAUT côté application.
ALTER TABLE evenements ADD COLUMN modules_actifs_json TEXT DEFAULT '["billetterie","depenses","benevoles"]';
ALTER TABLE evenements ADD COLUMN tombola_tickets_par_carnet INTEGER DEFAULT 5;

ALTER TABLE evenement_stands ADD COLUMN responsable TEXT;
ALTER TABLE evenement_stands ADD COLUMN telephone TEXT;
ALTER TABLE evenement_stands ADD COLUMN emplacement TEXT;

ALTER TABLE tombola_lots ADD COLUMN donateur TEXT;

ALTER TABLE remises_cheques ADD COLUMN numero_bordereau TEXT;

-- Étendre les statuts de subvention pour gérer les cas partiels.
CREATE TABLE IF NOT EXISTS subventions_phase13 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organisme TEXT NOT NULL,
    type_organisme TEXT NOT NULL DEFAULT 'autre'
        CHECK(type_organisme IN ('mairie','departement','region','entreprise','autre')),
    annee INTEGER NOT NULL,
    objet TEXT,
    montant_demande REAL DEFAULT 0,
    montant_obtenu REAL DEFAULT 0,
    statut TEXT NOT NULL DEFAULT 'en_attente'
        CHECK(statut IN ('en_attente','accordee','refusee','annulee','partielle')),
    date_demande TEXT,
    date_decision TEXT,
    date_versement TEXT,
    compte_id INTEGER REFERENCES comptes_bancaires(id),
    operation_id INTEGER REFERENCES tresorerie_operations(id),
    commentaire TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

INSERT INTO subventions_phase13 (
    id, organisme, type_organisme, annee, objet, montant_demande, montant_obtenu,
    statut, date_demande, date_decision, date_versement, compte_id, operation_id,
    commentaire, created_at
)
SELECT
    id,
    organisme,
    type_organisme,
    annee,
    objet,
    montant_demande,
    montant_obtenu,
    CASE
        WHEN statut = 'partielle' THEN 'partielle'
        ELSE COALESCE(statut, 'en_attente')
    END,
    date_demande,
    date_decision,
    date_versement,
    compte_id,
    operation_id,
    commentaire,
    created_at
FROM subventions;

DROP TABLE subventions;
ALTER TABLE subventions_phase13 RENAME TO subventions;
