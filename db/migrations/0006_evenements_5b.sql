-- ─── TOMBOLA ────────────────────────────────────────────────────────────────

-- Lots de tombola
CREATE TABLE IF NOT EXISTS tombola_lots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evenement_id INTEGER NOT NULL REFERENCES evenements(id),
    numero INTEGER NOT NULL,
    description TEXT NOT NULL,
    valeur_estimee REAL DEFAULT 0,
    type_lot TEXT NOT NULL DEFAULT 'achete'
        CHECK(type_lot IN ('achete','sponsorise')),
    fournisseur_id INTEGER REFERENCES fournisseurs(id),
    sponsor_nom TEXT,
    numero_gagnant TEXT,
    statut TEXT NOT NULL DEFAULT 'en_attente'
        CHECK(statut IN ('en_attente','attribue','non_reclame')),
    date_tirage TEXT,
    commentaire TEXT
);

-- Carnets de tombola
CREATE TABLE IF NOT EXISTS tombola_carnets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evenement_id INTEGER NOT NULL REFERENCES evenements(id),
    numero_debut INTEGER NOT NULL,
    numero_fin INTEGER NOT NULL,
    prix_carnet REAL NOT NULL DEFAULT 0,
    vendeur_membre_id INTEGER REFERENCES membres(id),
    vendeur_nom_externe TEXT,
    statut TEXT NOT NULL DEFAULT 'emis'
        CHECK(statut IN ('emis','vendu','retourne','perdu')),
    date_remise TEXT,
    montant_encaisse REAL DEFAULT 0,
    commentaire TEXT
);

-- ─── STANDS ─────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS evenement_stands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evenement_id INTEGER NOT NULL REFERENCES evenements(id),
    numero_emplacement TEXT,
    nom_stand TEXT NOT NULL,
    type_stand TEXT NOT NULL DEFAULT 'benevole'
        CHECK(type_stand IN ('benevole','location')),
    responsable_membre_id INTEGER REFERENCES membres(id),
    responsable_nom_externe TEXT,
    montant_location REAL DEFAULT 0,
    paiement_avant INTEGER DEFAULT 0,
    statut TEXT NOT NULL DEFAULT 'confirme'
        CHECK(statut IN ('confirme','annule')),
    commentaire TEXT,
    tresorerie_id INTEGER
);

-- Liste d'attente stands
CREATE TABLE IF NOT EXISTS evenement_stands_attente (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evenement_id INTEGER NOT NULL REFERENCES evenements(id),
    nom TEXT NOT NULL,
    prenom TEXT,
    contact TEXT,
    date_inscription TEXT DEFAULT (datetime('now')),
    commentaire TEXT
);

-- ─── TABLEAUX PERSONNALISÉS ──────────────────────────────────────────────────

-- Définition d'un tableau
CREATE TABLE IF NOT EXISTS tableaux_perso (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evenement_id INTEGER NOT NULL REFERENCES evenements(id),
    nom TEXT NOT NULL,
    description TEXT,
    ordre INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Colonnes d'un tableau
CREATE TABLE IF NOT EXISTS tableaux_colonnes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tableau_id INTEGER NOT NULL REFERENCES tableaux_perso(id),
    nom TEXT NOT NULL,
    type_colonne TEXT NOT NULL DEFAULT 'texte'
        CHECK(type_colonne IN (
            'texte','nombre','montant','date','checkbox',
            'liste_paiement','liste_classes','liste_membres',
            'liste_fournisseurs','liste_statut','liste_perso'
        )),
    liste_perso_valeurs TEXT,
    afficher_total INTEGER DEFAULT 0,
    ordre INTEGER DEFAULT 0,
    largeur INTEGER DEFAULT 150
);

-- Lignes d'un tableau
CREATE TABLE IF NOT EXISTS tableaux_lignes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tableau_id INTEGER NOT NULL REFERENCES tableaux_perso(id),
    membre_id INTEGER REFERENCES membres(id),
    statut_ligne TEXT NOT NULL DEFAULT 'normal'
        CHECK(statut_ligne IN ('normal','paye','en_attente','annule')),
    ordre INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Cellules (valeurs par ligne/colonne)
CREATE TABLE IF NOT EXISTS tableaux_cellules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ligne_id INTEGER NOT NULL REFERENCES tableaux_lignes(id),
    colonne_id INTEGER NOT NULL REFERENCES tableaux_colonnes(id),
    valeur TEXT
);

-- Templates de tableaux (structures réutilisables)
CREATE TABLE IF NOT EXISTS tableaux_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    description TEXT,
    colonnes_json TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Listes personnalisées configurables (classes, statuts, etc.)
INSERT OR IGNORE INTO parametres (cle, valeur, description)
VALUES
    ('classes_scolaires', '["PS","MS","GS","CP","CE1","CE2","CM1","CM2"]',
     'Classes scolaires (JSON)'),
    ('statuts_perso', '["En attente","Confirmé","Payé","Annulé"]',
     'Statuts personnalisés pour tableaux (JSON)');
