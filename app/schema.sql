-- Schéma Brocantor — SQLite. Exécuté au démarrage (CREATE TABLE IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS produits (
    id                   TEXT PRIMARY KEY,
    cree_le              TEXT NOT NULL,
    etat                 TEXT NOT NULL DEFAULT 'depose',
    note_utilisateur     TEXT,
    titre                TEXT,
    description          TEXT,
    categorie_lbc        TEXT,
    prix_min_estime      INTEGER,
    prix_max_estime      INTEGER,
    prix_choisi          INTEGER,
    confiance_estimation TEXT,
    hypotheses_ia        TEXT,   -- JSON (liste de chaînes)
    questions_ia         TEXT,   -- JSON (liste de chaînes)
    url_annonce          TEXT,
    prix_vente_reel      INTEGER,
    vendu_le             TEXT,
    notes                TEXT,
    erreur_derniere      TEXT,
    tentatives           INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS photos (
    id              TEXT PRIMARY KEY,
    produit_id      TEXT NOT NULL,
    chemin_original TEXT NOT NULL,
    chemin_lbc      TEXT,
    position        INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (produit_id) REFERENCES produits(id)
);

CREATE TABLE IF NOT EXISTS evenements (
    id          TEXT PRIMARY KEY,
    produit_id  TEXT NOT NULL,
    horodatage  TEXT NOT NULL,
    ancien_etat TEXT,
    nouvel_etat TEXT NOT NULL,
    commentaire TEXT,
    FOREIGN KEY (produit_id) REFERENCES produits(id)
);

CREATE INDEX IF NOT EXISTS idx_produits_etat ON produits(etat);
CREATE INDEX IF NOT EXISTS idx_photos_produit ON photos(produit_id);
CREATE INDEX IF NOT EXISTS idx_evenements_produit ON evenements(produit_id);
