CREATE TABLE IF NOT EXISTS dons (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    exercice_id         INTEGER REFERENCES exercices(id) ON DELETE SET NULL,
    date_don            TEXT NOT NULL,
    type_donateur       TEXT NOT NULL CHECK(type_donateur IN ('particulier','entreprise')),
    membre_id           INTEGER REFERENCES membres(id) ON DELETE SET NULL,
    donateur_nom        TEXT NOT NULL,
    donateur_prenom     TEXT,
    donateur_adresse    TEXT,
    donateur_cp         TEXT,
    donateur_ville      TEXT,
    donateur_siret      TEXT,
    nature_don          TEXT NOT NULL DEFAULT 'argent' CHECK(nature_don IN ('argent','nature')),
    montant             REAL,
    description_don     TEXT,
    valeur_estimee      REAL,
    mode_versement      TEXT CHECK(mode_versement IN ('cheque','virement','especes','cb','autre')),
    num_recu            TEXT UNIQUE,
    statut_recu         TEXT NOT NULL DEFAULT 'en_attente' CHECK(statut_recu IN ('en_attente','emis','annule')),
    date_emission_recu  TEXT,
    tresorerie_id       INTEGER,
    commentaire         TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_dons_exercice ON dons(exercice_id);
CREATE INDEX IF NOT EXISTS idx_dons_membre ON dons(membre_id);
CREATE INDEX IF NOT EXISTS idx_dons_statut ON dons(statut_recu);
