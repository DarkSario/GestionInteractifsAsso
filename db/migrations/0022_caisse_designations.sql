-- Phase 22 : désignations globales réutilisables pour les caisses événement

CREATE TABLE IF NOT EXISTS caisse_designations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL UNIQUE,
    montant_unitaire REAL NOT NULL DEFAULT 0,
    description TEXT,
    ordre INTEGER NOT NULL DEFAULT 0,
    actif INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS evenement_caisse_lignes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    caisse_id INTEGER NOT NULL REFERENCES evenement_caisses(id) ON DELETE CASCADE,
    type_ouverture TEXT NOT NULL CHECK(type_ouverture IN ('debut', 'fin')),
    designation TEXT NOT NULL,
    montant_unitaire REAL NOT NULL DEFAULT 0,
    quantite INTEGER NOT NULL DEFAULT 1,
    total REAL NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    designation_id INTEGER REFERENCES caisse_designations(id) ON DELETE SET NULL,
    designation_text TEXT
);

ALTER TABLE evenement_caisse_lignes ADD COLUMN designation_id INTEGER REFERENCES caisse_designations(id) ON DELETE SET NULL;
ALTER TABLE evenement_caisse_lignes ADD COLUMN designation_text TEXT;

UPDATE evenement_caisse_lignes
SET designation_text = COALESCE(NULLIF(designation_text, ''), designation)
WHERE COALESCE(designation, '') != '';

CREATE INDEX IF NOT EXISTS idx_caisse_designations_actif_ordre
    ON caisse_designations(actif, ordre, nom);
CREATE INDEX IF NOT EXISTS idx_evenement_caisse_lignes_designation_id
    ON evenement_caisse_lignes(designation_id);

INSERT INTO caisse_designations (nom, montant_unitaire, description, ordre, actif)
VALUES
    ('Pièces 1€', 1.0, '', 10, 1),
    ('Pièces 2€', 2.0, '', 20, 1),
    ('Billets 5€', 5.0, '', 30, 1),
    ('Billets 10€', 10.0, '', 40, 1),
    ('Billets 20€', 20.0, '', 50, 1),
    ('Billets 50€', 50.0, '', 60, 1),
    ('Billets 100€', 100.0, '', 70, 1),
    ('Chèques', 0.0, 'À remplir', 80, 1),
    ('SumUp/CB', 0.0, 'À remplir', 90, 1),
    ('Tickets resto', 0.0, 'À remplir', 100, 1),
    ('Bons d''achat', 0.0, 'À remplir', 110, 1),
    ('Autre', 0.0, 'À remplir', 120, 1)
ON CONFLICT(nom) DO UPDATE SET
    montant_unitaire = excluded.montant_unitaire,
    description = excluded.description,
    ordre = excluded.ordre,
    actif = 1,
    updated_at = datetime('now');
