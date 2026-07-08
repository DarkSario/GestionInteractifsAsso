-- Configuration de l'en-tête PDF (infos asso)
INSERT OR IGNORE INTO parametres (cle, valeur, description)
VALUES
    ('asso_nom',      '',  'Nom de l''association'),
    ('asso_adresse',  '',  'Adresse de l''association'),
    ('asso_telephone','',  'Téléphone de l''association'),
    ('asso_email',    '',  'Email de l''association'),
    ('asso_logo_path','',  'Chemin vers le logo de l''association (PNG/JPG)');
