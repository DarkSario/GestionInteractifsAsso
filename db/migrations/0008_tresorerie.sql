-- Trésorerie Phase 6a

-- Comptes bancaires (N comptes configurables)
CREATE TABLE IF NOT EXISTS comptes_bancaires (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    type_compte TEXT NOT NULL DEFAULT 'bancaire'
        CHECK(type_compte IN ('bancaire','livret','sumup','caisse','autre')),
    solde_initial REAL NOT NULL DEFAULT 0,
    est_principal INTEGER DEFAULT 0,
    est_caisse INTEGER DEFAULT 0,
    iban TEXT,
    banque TEXT,
    actif INTEGER DEFAULT 1,
    ordre INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Catégories d'opérations
CREATE TABLE IF NOT EXISTS tresorerie_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    type_categorie TEXT NOT NULL
        CHECK(type_categorie IN ('recette','depense','les_deux')),
    est_systeme INTEGER DEFAULT 0,
    ordre INTEGER DEFAULT 0
);

-- Remises de chèques
CREATE TABLE IF NOT EXISTS remises_cheques (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    compte_id INTEGER NOT NULL REFERENCES comptes_bancaires(id),
    date_remise TEXT NOT NULL,
    reference TEXT,
    montant_total REAL NOT NULL DEFAULT 0,
    nombre_cheques INTEGER DEFAULT 0,
    statut TEXT NOT NULL DEFAULT 'en_attente'
        CHECK(statut IN ('en_attente','remis','encaisse')),
    commentaire TEXT,
    operation_id INTEGER REFERENCES tresorerie_operations(id),
    created_at TEXT DEFAULT (datetime('now'))
);

-- Opérations de trésorerie
CREATE TABLE IF NOT EXISTS tresorerie_operations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    compte_id INTEGER NOT NULL REFERENCES comptes_bancaires(id),
    type_operation TEXT NOT NULL
        CHECK(type_operation IN ('recette','depense','virement_interne')),
    libelle TEXT NOT NULL,
    montant REAL NOT NULL DEFAULT 0,
    date_operation TEXT NOT NULL,
    categorie_id INTEGER REFERENCES tresorerie_categories(id),
    mode_paiement TEXT
        CHECK(mode_paiement IN ('especes','cheque','carte','sumup','virement','prelevement','autre')),
    numero_facture TEXT,
    evenement_id INTEGER REFERENCES evenements(id),
    fournisseur_id INTEGER REFERENCES fournisseurs(id),
    statut TEXT NOT NULL DEFAULT 'valide'
        CHECK(statut IN ('valide','en_attente','rapproche','annule')),
    est_automatique INTEGER DEFAULT 0,
    source_module TEXT,
    source_id INTEGER,
    remise_cheque_id INTEGER REFERENCES remises_cheques(id),
    compte_destination_id INTEGER REFERENCES comptes_bancaires(id),
    commentaire TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Chèques individuels dans une remise
CREATE TABLE IF NOT EXISTS remises_cheques_detail (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    remise_id INTEGER NOT NULL REFERENCES remises_cheques(id),
    nom_tireur TEXT NOT NULL,
    montant REAL NOT NULL DEFAULT 0,
    evenement_id INTEGER REFERENCES evenements(id),
    commentaire TEXT
);

-- Subventions
CREATE TABLE IF NOT EXISTS subventions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organisme TEXT NOT NULL,
    type_organisme TEXT NOT NULL DEFAULT 'autre'
        CHECK(type_organisme IN ('mairie','departement','region','entreprise','autre')),
    annee INTEGER NOT NULL,
    objet TEXT,
    montant_demande REAL DEFAULT 0,
    montant_obtenu REAL DEFAULT 0,
    statut TEXT NOT NULL DEFAULT 'en_attente'
        CHECK(statut IN ('en_attente','accordee','refusee','annulee')),
    date_demande TEXT,
    date_decision TEXT,
    date_versement TEXT,
    compte_id INTEGER REFERENCES comptes_bancaires(id),
    operation_id INTEGER REFERENCES tresorerie_operations(id),
    commentaire TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Catégories prédéfinies
INSERT OR IGNORE INTO tresorerie_categories (nom, type_categorie, est_systeme, ordre) VALUES
    ('Cotisations', 'recette', 1, 1),
    ('Billetterie', 'recette', 1, 2),
    ('Buvette', 'recette', 1, 3),
    ('Tombola', 'recette', 1, 4),
    ('Stands / Locations', 'recette', 1, 5),
    ('Subvention', 'recette', 1, 6),
    ('Don', 'recette', 1, 7),
    ('Autre recette', 'recette', 1, 8),
    ('Location salle / matériel', 'depense', 1, 10),
    ('Fournitures / Matériel', 'depense', 1, 11),
    ('Alimentation / Boissons', 'depense', 1, 12),
    ('Communication / Impression', 'depense', 1, 13),
    ('Frais bancaires', 'depense', 1, 14),
    ('Frais SumUp', 'depense', 1, 15),
    ('Prestataires / Artistes', 'depense', 1, 16),
    ('Remboursements membres', 'depense', 1, 17),
    ('Autre dépense', 'depense', 1, 18);

-- Comptes par défaut
INSERT OR IGNORE INTO comptes_bancaires (id, nom, type_compte, solde_initial, est_principal, est_caisse, actif, ordre)
VALUES (1, 'Compte courant', 'bancaire', 0, 1, 0, 1, 1);

INSERT OR IGNORE INTO comptes_bancaires (id, nom, type_compte, solde_initial, est_principal, est_caisse, actif, ordre)
VALUES (2, 'Caisse espèces', 'caisse', 0, 0, 1, 1, 2);

-- Migration du solde initial historique vers le compte principal
UPDATE comptes_bancaires
SET solde_initial = (
    SELECT COALESCE(solde_ouverture, 0)
    FROM config
    ORDER BY id ASC
    LIMIT 1
)
WHERE id = 1
  AND COALESCE(solde_initial, 0) = 0
  AND EXISTS (SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'config')
  AND EXISTS (SELECT 1 FROM config);

-- Paramètres supplémentaires
INSERT OR IGNORE INTO parametres (cle, valeur, description) VALUES
    (
        'compte_principal_id',
        COALESCE(
            (
                SELECT CAST(id AS TEXT)
                FROM comptes_bancaires
                WHERE est_principal = 1
                ORDER BY ordre ASC, id ASC
                LIMIT 1
            ),
            '1'
        ),
        'ID du compte bancaire principal'
    ),
    (
        'compte_caisse_id',
        COALESCE(
            (
                SELECT CAST(id AS TEXT)
                FROM comptes_bancaires
                WHERE est_caisse = 1
                ORDER BY ordre ASC, id ASC
                LIMIT 1
            ),
            '2'
        ),
        'ID de la caisse espèces principale'
    );
