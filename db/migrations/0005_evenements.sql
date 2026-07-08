-- Évolution de la table evenements (ajout des nouvelles colonnes Phase 5a)
ALTER TABLE evenements ADD COLUMN type TEXT;
ALTER TABLE evenements ADD COLUMN date_debut TEXT;
ALTER TABLE evenements ADD COLUMN date_fin TEXT;
ALTER TABLE evenements ADD COLUMN statut TEXT DEFAULT 'planifie';
ALTER TABLE evenements ADD COLUMN budget_previsionnel REAL;
ALTER TABLE evenements ADD COLUMN bilan_fin TEXT;
ALTER TABLE evenements ADD COLUMN created_at TEXT DEFAULT (datetime('now'));

-- Tarifs billetterie par événement
CREATE TABLE IF NOT EXISTS evenement_tarifs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evenement_id INTEGER NOT NULL REFERENCES evenements(id),
    nom TEXT NOT NULL,
    prix REAL NOT NULL DEFAULT 0,
    est_gratuit INTEGER DEFAULT 0,
    ordre INTEGER DEFAULT 0
);

-- Ventes billetterie (1 transaction = plusieurs tarifs possibles)
CREATE TABLE IF NOT EXISTS evenement_ventes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evenement_id INTEGER NOT NULL REFERENCES evenements(id),
    date TEXT NOT NULL,
    canal TEXT NOT NULL DEFAULT 'sur_place'
        CHECK(canal IN ('sur_place','prevente')),
    mode_paiement TEXT NOT NULL
        CHECK(mode_paiement IN ('especes','cheque','carte','sumup')),
    nom_tireur TEXT,
    montant_total REAL NOT NULL DEFAULT 0,
    frais_sumup REAL DEFAULT 0,
    montant_net REAL NOT NULL DEFAULT 0,
    statut TEXT NOT NULL DEFAULT 'valide'
        CHECK(statut IN ('valide','annule','rembourse')),
    motif_annulation TEXT,
    commentaire TEXT,
    tresorerie_id INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Lignes de vente (détail par tarif)
CREATE TABLE IF NOT EXISTS evenement_vente_lignes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vente_id INTEGER NOT NULL REFERENCES evenement_ventes(id),
    tarif_id INTEGER NOT NULL REFERENCES evenement_tarifs(id),
    quantite INTEGER NOT NULL DEFAULT 1,
    prix_unitaire REAL NOT NULL DEFAULT 0,
    sous_total REAL NOT NULL DEFAULT 0
);

-- Billets individuels (numérotation)
CREATE TABLE IF NOT EXISTS evenement_billets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vente_ligne_id INTEGER NOT NULL REFERENCES evenement_vente_lignes(id),
    numero TEXT NOT NULL,
    tarif_id INTEGER NOT NULL REFERENCES evenement_tarifs(id),
    statut TEXT NOT NULL DEFAULT 'emis'
        CHECK(statut IN ('emis','utilise','annule'))
);

-- Évolution de la table evenement_depenses (ajout des nouvelles colonnes Phase 5a)
ALTER TABLE evenement_depenses ADD COLUMN libelle TEXT;
ALTER TABLE evenement_depenses ADD COLUMN date TEXT;
ALTER TABLE evenement_depenses ADD COLUMN fournisseur_id INTEGER REFERENCES fournisseurs(id);
ALTER TABLE evenement_depenses ADD COLUMN mode_paiement TEXT;
ALTER TABLE evenement_depenses ADD COLUMN tresorerie_id INTEGER;
ALTER TABLE evenement_depenses ADD COLUMN created_at TEXT DEFAULT (datetime('now'));

-- Bénévoles affectés à un événement
CREATE TABLE IF NOT EXISTS evenement_benevoles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evenement_id INTEGER NOT NULL REFERENCES evenements(id),
    membre_id INTEGER REFERENCES membres(id),
    nom_externe TEXT,
    prenom_externe TEXT,
    role TEXT,
    heure_debut TEXT,
    heure_fin TEXT,
    statut TEXT NOT NULL DEFAULT 'confirme'
        CHECK(statut IN ('confirme','desiste','remplace')),
    remplacant_id INTEGER REFERENCES evenement_benevoles(id),
    commentaire TEXT
);

-- Paramètres globaux
CREATE TABLE IF NOT EXISTS parametres (
    cle TEXT PRIMARY KEY,
    valeur TEXT NOT NULL,
    description TEXT
);

INSERT OR IGNORE INTO parametres (cle, valeur, description)
VALUES ('taux_sumup', '1.75', 'Taux de commission SumUp en pourcentage');
