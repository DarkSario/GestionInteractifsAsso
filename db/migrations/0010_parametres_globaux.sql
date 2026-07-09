-- Phase 7 — Paramètres globaux

-- Classes scolaires
CREATE TABLE IF NOT EXISTS classes_scolaires (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL UNIQUE,
    ordre INTEGER DEFAULT 0,
    actif INTEGER DEFAULT 1
);

-- Types d'événements personnalisés
CREATE TABLE IF NOT EXISTS types_evenements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL UNIQUE,
    ordre INTEGER DEFAULT 0,
    actif INTEGER DEFAULT 1
);

-- Modes de paiement configurables
CREATE TABLE IF NOT EXISTS modes_paiement (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    libelle TEXT NOT NULL,
    actif INTEGER DEFAULT 1,
    est_systeme INTEGER DEFAULT 1,
    ordre INTEGER DEFAULT 0
);

-- Seed classes scolaires par défaut
INSERT OR IGNORE INTO classes_scolaires (nom, ordre) VALUES
    ('PS', 1), ('MS', 2), ('GS', 3),
    ('CP', 4), ('CE1', 5), ('CE2', 6),
    ('CM1', 7), ('CM2', 8), ('ULIS', 9);

-- Seed types d'événements par défaut
INSERT OR IGNORE INTO types_evenements (nom, ordre) VALUES
    ('Kermesse', 1), ('Spectacle', 2), ('Sortie scolaire', 3),
    ('Vente', 4), ('Repas', 5), ('Autre', 6);

-- Seed modes de paiement
INSERT OR IGNORE INTO modes_paiement (code, libelle, actif, est_systeme, ordre) VALUES
    ('especes',     'Espèces',        1, 1, 1),
    ('cheque',      'Chèque',         1, 1, 2),
    ('carte',       'Carte bancaire', 1, 1, 3),
    ('sumup',       'SumUp',          1, 1, 4),
    ('virement',    'Virement',       1, 1, 5),
    ('prelevement', 'Prélèvement',    1, 1, 6);

-- Paramètres système supplémentaires
INSERT OR IGNORE INTO parametres (cle, valeur, description) VALUES
    ('sauvegarde_auto',       '0',    'Sauvegarde automatique activée (0/1)'),
    ('sauvegarde_frequence',  '7',    'Fréquence de sauvegarde en jours'),
    ('sauvegarde_dossier',    '',     'Dossier de destination des sauvegardes'),
    ('export_dossier_defaut', '',     'Dossier d''export par défaut'),
    ('theme_mode',            'dark', 'Mode du thème (dark/light)'),
    ('derniere_sauvegarde',   '',     'Date de la dernière sauvegarde automatique');
