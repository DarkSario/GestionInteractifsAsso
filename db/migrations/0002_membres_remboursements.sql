-- Ajout colonne statut_archive dans membres
ALTER TABLE membres ADD COLUMN statut_archive INTEGER DEFAULT 0;

-- Ajout colonne membre_id dans dons_subventions
ALTER TABLE dons_subventions ADD COLUMN membre_id INTEGER REFERENCES membres(id);

-- Ajout colonnes dans depenses_regulieres
ALTER TABLE depenses_regulieres ADD COLUMN membre_id INTEGER REFERENCES membres(id);
ALTER TABLE depenses_regulieres ADD COLUMN statut_remboursement TEXT DEFAULT 'non concerné';

-- Ajout colonnes dans depenses_diverses
ALTER TABLE depenses_diverses ADD COLUMN membre_id INTEGER REFERENCES membres(id);
ALTER TABLE depenses_diverses ADD COLUMN statut_remboursement TEXT DEFAULT 'non concerné';

-- Nouvelle table remboursements
CREATE TABLE IF NOT EXISTS remboursements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    depense_type TEXT NOT NULL CHECK(depense_type IN ('reguliere', 'diverse', 'evenement')),
    depense_id INTEGER NOT NULL,
    membre_id INTEGER NOT NULL,
    date_remboursement TEXT,
    montant REAL NOT NULL,
    moyen_paiement TEXT CHECK(moyen_paiement IN ('chèque', 'virement', 'espèces')),
    reference TEXT,
    commentaire TEXT,
    FOREIGN KEY (membre_id) REFERENCES membres(id)
);
