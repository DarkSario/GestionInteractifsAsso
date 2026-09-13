-- Phase 21 : gestion détaillée des caisses par événement

CREATE TABLE IF NOT EXISTS evenement_caisses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evenement_id INTEGER NOT NULL REFERENCES evenements(id),
    nom_caisse TEXT NOT NULL,
    commentaire TEXT,
    FOREIGN KEY (evenement_id) REFERENCES evenements(id)
);

-- Harmonisation de la table historique evenement_caisses
ALTER TABLE evenement_caisses ADD COLUMN nom TEXT;
ALTER TABLE evenement_caisses ADD COLUMN statut TEXT DEFAULT 'ouvert';
ALTER TABLE evenement_caisses ADD COLUMN created_at TEXT;
ALTER TABLE evenement_caisses ADD COLUMN updated_at TEXT;

UPDATE evenement_caisses
SET nom = COALESCE(nom, nom_caisse)
WHERE COALESCE(nom, '') = '';

UPDATE evenement_caisses
SET created_at = COALESCE(NULLIF(created_at, ''), datetime('now')),
    updated_at = COALESCE(NULLIF(updated_at, ''), datetime('now')),
    statut = COALESCE(NULLIF(statut, ''), 'ouvert');

-- Détail des lignes de caisse (début / fin)
CREATE TABLE IF NOT EXISTS evenement_caisse_lignes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    caisse_id INTEGER NOT NULL REFERENCES evenement_caisses(id) ON DELETE CASCADE,
    type_ouverture TEXT NOT NULL CHECK(type_ouverture IN ('debut', 'fin')),
    designation TEXT NOT NULL,
    montant_unitaire REAL NOT NULL DEFAULT 0,
    quantite INTEGER NOT NULL DEFAULT 1,
    total REAL NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_evenement_caisses_evenement_id
    ON evenement_caisses(evenement_id);
CREATE INDEX IF NOT EXISTS idx_evenement_caisse_lignes_caisse_id
    ON evenement_caisse_lignes(caisse_id);
CREATE INDEX IF NOT EXISTS idx_evenement_caisse_lignes_type
    ON evenement_caisse_lignes(caisse_id, type_ouverture);
