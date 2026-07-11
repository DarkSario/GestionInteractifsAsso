-- Trésorerie Phase 6b — Clôture d'exercice

-- Exercices (historique des périodes)
CREATE TABLE IF NOT EXISTS exercices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    type_exercice TEXT NOT NULL DEFAULT 'scolaire'
        CHECK(type_exercice IN ('scolaire','civile')),
    date_debut TEXT NOT NULL,
    date_fin TEXT NOT NULL,
    statut TEXT NOT NULL DEFAULT 'ouvert'
        CHECK(statut IN ('ouvert','cloture')),
    solde_ouverture REAL NOT NULL DEFAULT 0,
    solde_cloture REAL,
    date_cloture TEXT,
    cloture_par TEXT DEFAULT 'admin',
    date_decloture TEXT,
    decloture_par TEXT,
    commentaire TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Log des actions de clôture/déclôture
CREATE TABLE IF NOT EXISTS exercices_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exercice_id INTEGER NOT NULL REFERENCES exercices(id),
    action TEXT NOT NULL
        CHECK(action IN ('cloture','decloture')),
    date_action TEXT DEFAULT (datetime('now')),
    utilisateur TEXT DEFAULT 'admin',
    commentaire TEXT
);

-- Paramètres sécurité déclôture
INSERT OR IGNORE INTO parametres (cle, valeur, description) VALUES
    ('mdp_decloture_hash', '', 'Hash scrypt du mot de passe de déclôture (initialisé automatiquement)'),
    ('code_master_hash', '', 'Hash scrypt du code master de récupération (initialisé automatiquement)');
