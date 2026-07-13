-- Migration Phase 16 : Table des cotisations adhérents
CREATE TABLE IF NOT EXISTS cotisations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    adherent_id INTEGER NOT NULL REFERENCES membres(id) ON DELETE CASCADE,
    exercice_id INTEGER REFERENCES exercices(id) ON DELETE SET NULL,
    annee INTEGER NOT NULL,
    montant REAL NOT NULL DEFAULT 0.0,
    statut TEXT NOT NULL DEFAULT 'offerte' CHECK(statut IN ('offerte', 'payee', 'en_attente')),
    date_paiement TEXT,
    mode_paiement TEXT,
    commentaire TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_cotisations_adherent ON cotisations(adherent_id);
CREATE INDEX IF NOT EXISTS idx_cotisations_annee ON cotisations(annee);
