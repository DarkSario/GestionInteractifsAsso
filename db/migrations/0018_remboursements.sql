-- Migration Phase 17 : suivi des remboursements de frais
ALTER TABLE evenement_depenses ADD COLUMN avance_par_membre_id INTEGER REFERENCES membres(id) ON DELETE SET NULL;
ALTER TABLE evenement_depenses ADD COLUMN remboursement_statut TEXT NOT NULL DEFAULT 'non_applicable' CHECK(remboursement_statut IN ('non_applicable','en_attente','rembourse'));
ALTER TABLE evenement_depenses ADD COLUMN remboursement_date TEXT;
ALTER TABLE evenement_depenses ADD COLUMN remboursement_mode TEXT;
ALTER TABLE evenement_depenses ADD COLUMN remboursement_reference TEXT;

ALTER TABLE tresorerie_operations ADD COLUMN avance_par_membre_id INTEGER REFERENCES membres(id) ON DELETE SET NULL;
ALTER TABLE tresorerie_operations ADD COLUMN remboursement_statut TEXT NOT NULL DEFAULT 'non_applicable' CHECK(remboursement_statut IN ('non_applicable','en_attente','rembourse'));
ALTER TABLE tresorerie_operations ADD COLUMN remboursement_date TEXT;
ALTER TABLE tresorerie_operations ADD COLUMN remboursement_mode TEXT;
ALTER TABLE tresorerie_operations ADD COLUMN remboursement_reference TEXT;
