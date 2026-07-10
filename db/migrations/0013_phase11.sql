-- Phase 11 — Corrections post-tests

-- Tombola : configuration prix ticket/carnet sur l'événement
ALTER TABLE evenements ADD COLUMN tombola_prix_ticket REAL DEFAULT 0;
ALTER TABLE evenements ADD COLUMN tombola_prix_carnet REAL DEFAULT 0;

-- Tombola : valeur_lot dédiée
ALTER TABLE tombola_lots ADD COLUMN valeur_lot REAL DEFAULT 0;

-- Tombola : élargir les statuts disponibles (nouveaux + historiques)
CREATE TABLE IF NOT EXISTS tombola_lots_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evenement_id INTEGER NOT NULL REFERENCES evenements(id),
    numero INTEGER NOT NULL,
    description TEXT NOT NULL,
    valeur_estimee REAL DEFAULT 0,
    valeur_lot REAL DEFAULT 0,
    type_lot TEXT NOT NULL DEFAULT 'achete'
        CHECK(type_lot IN ('achete','sponsorise')),
    fournisseur_id INTEGER REFERENCES fournisseurs(id),
    sponsor_nom TEXT,
    numero_gagnant TEXT,
    statut TEXT NOT NULL DEFAULT 'disponible'
        CHECK(statut IN (
            'en_attente','attribue','non_reclame',
            'disponible','reserve','gagne','remis'
        )),
    date_tirage TEXT,
    commentaire TEXT
);

INSERT INTO tombola_lots_new (
    id, evenement_id, numero, description, valeur_estimee, valeur_lot,
    type_lot, fournisseur_id, sponsor_nom, numero_gagnant, statut, date_tirage, commentaire
)
SELECT
    id,
    evenement_id,
    numero,
    description,
    COALESCE(valeur_estimee, 0),
    COALESCE(valeur_lot, valeur_estimee, 0),
    type_lot,
    fournisseur_id,
    sponsor_nom,
    numero_gagnant,
    CASE
        WHEN statut = 'en_attente' THEN 'disponible'
        WHEN statut = 'attribue' THEN 'gagne'
        WHEN statut = 'non_reclame' THEN 'reserve'
        ELSE COALESCE(statut, 'disponible')
    END,
    date_tirage,
    commentaire
FROM tombola_lots;

DROP TABLE tombola_lots;
ALTER TABLE tombola_lots_new RENAME TO tombola_lots;

-- Stands : distinguer recette/dépense
-- Choix de migration: les lignes existantes sont marquées par défaut en "recette"
-- pour préserver le comportement historique (toutes les locations étaient traitées en recette).
ALTER TABLE evenement_stands ADD COLUMN type_location TEXT DEFAULT 'recette';
