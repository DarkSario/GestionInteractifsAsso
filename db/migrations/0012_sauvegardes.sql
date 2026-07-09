-- Phase 10 — Sauvegardes & import/export base

CREATE TABLE IF NOT EXISTS sauvegardes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom_fichier TEXT NOT NULL,
    chemin_complet TEXT NOT NULL,
    taille_octets INTEGER,
    type_sauvegarde TEXT NOT NULL DEFAULT 'manuelle'
        CHECK(type_sauvegarde IN ('manuelle','automatique','avant_restauration')),
    statut TEXT NOT NULL DEFAULT 'ok'
        CHECK(statut IN ('ok','erreur','supprimee')),
    message_erreur TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

INSERT OR IGNORE INTO parametres (cle, valeur, description) VALUES
    ('sauvegarde_rotation_max',  '10',  'Nombre maximum de sauvegardes à conserver'),
    ('sauvegarde_compression',   '1',   'Compresser les sauvegardes en .zip (0/1)'),
    ('sauvegarde_inclure_config','1',   'Inclure config/ dans l''export .zip (0/1)');
