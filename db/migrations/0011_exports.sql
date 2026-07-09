-- Phase 9 — Exports & Rapports

-- Polices importées
CREATE TABLE IF NOT EXISTS polices_pdf (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL UNIQUE,
    fichier_ttf TEXT NOT NULL,
    fichier_ttf_bold TEXT,
    fichier_ttf_italic TEXT,
    est_systeme INTEGER DEFAULT 0,
    actif INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Paramètres exports PDF
INSERT OR IGNORE INTO parametres (cle, valeur, description) VALUES
    ('pdf_police_titre',       'Helvetica',  'Police des titres PDF'),
    ('pdf_police_corps',       'Helvetica',  'Police du corps de texte PDF'),
    ('pdf_taille_base',        '11',         'Taille de base du texte PDF (pt)'),
    ('pdf_couleur_accent',     '#000000',    'Couleur d''accentuation PDF (filets, en-têtes)'),
    ('pdf_inclure_graphiques', '0',          'Inclure graphiques par défaut dans les PDF'),
    ('pdf_format_defaut',      'A4',         'Format papier par défaut');
