# T01 — Socle applicatif (FastAPI, SQLite, layout, routers vides, seed)

> Prompt pour agent IA dev. Lire `CLAUDE.md` et `docs/cahier-des-charges.md` (§3, §4) avant de coder.

## Contexte

Tu poses les fondations de Brocantor. Tous les autres tickets (T02–T08) seront développés en parallèle par d'autres agents sur la base de ton travail : ta mission est de créer un squelette **stable et cloisonné** pour qu'ils ne se marchent pas dessus. Tu es le seul ticket autorisé à créer `app/main.py`, `app/db.py`, `app/models.py` et le layout — les suivants n'y toucheront plus.

## Objectif

Une app FastAPI qui démarre, sert un layout HTMX commun, initialise la base SQLite avec le schéma complet, et fournit des données de démo.

## Spécifications

1. **Structure** — créer exactement l'arborescence décrite dans `CLAUDE.md` §Structure. Routers à créer VIDES (une route placeholder chacun qui rend un template « à venir ») : `routers/depot.py` (préfixe `/depot`), `routers/produits.py` (`/produits`), `routers/dashboard.py` (`/dashboard`), `routers/publication.py` (préfixe `/produits`, routes `/{id}/publier`), `routers/api.py` (`/api`). Tous montés dans `main.py`. La racine `/` redirige vers `/dashboard`.
2. **Base de données** — `app/db.py` : connexion SQLite (`data/app.db`), exécution de `app/schema.sql` au démarrage (CREATE TABLE IF NOT EXISTS). Tables :
   - `produits` : id (uuid texte), cree_le, etat (défaut `depose`), note_utilisateur, titre, description, categorie_lbc, prix_min_estime, prix_max_estime, prix_choisi, confiance_estimation, hypotheses_ia (JSON texte), questions_ia (JSON texte), url_annonce, prix_vente_reel, vendu_le, notes, erreur_derniere, tentatives (int défaut 0).
   - `photos` : id, produit_id (FK), chemin_original, chemin_lbc (nullable), position (int).
   - `evenements` : id, produit_id, horodatage, ancien_etat, nouvel_etat, commentaire.
3. **Modèles & états** — `app/models.py` : dataclasses/pydantic des entités + fonction `changer_etat(produit_id, nouvel_etat, commentaire=None)` qui valide la transition contre la machine à états de `CLAUDE.md` (lever une erreur si transition illégale) et journalise dans `evenements`. C'est LA porte d'entrée unique des changements d'état — les autres tickets l'utiliseront.
4. **Layout** — `templates/base.html` : mobile-first, `<meta viewport>`, barre de navigation basse 3 onglets (Dépôt / Fiches / Dashboard), HTMX vendorisé dans `static/htmx.min.js` (télécharge-le), CSS maison minimal dans `static/style.css` (sombre, gros boutons tactiles ≥ 48 px, pas de framework CSS).
5. **Config** — `.env` via `python-dotenv` : `ANTHROPIC_API_KEY`, `DATA_DIR` (défaut `./data`), `PORT` (défaut 8377). Fournir `.env.example`. `.gitignore` : `data/`, `.env`, `__pycache__`.
6. **Seed** — `python -m app.seed` : crée 6 produits factices couvrant tous les états (depose, a_valider avec fiche remplie, prete, publiee, vendue, erreur), avec 2 images JPEG factices générées par Pillow (rectangles colorés + texte) par produit, placées dans `data/photos/<id>/`. Idempotent (purge et recrée).
7. **Dépendances** — `requirements.txt` : fastapi, uvicorn[standard], jinja2, python-multipart, python-dotenv, pillow, anthropic. Rien d'autre.

## Critères d'acceptation

- `pip install -r requirements.txt` puis `uvicorn app.main:app --port 8377` démarre sans erreur, `data/app.db` créée avec les 3 tables.
- `/` redirige vers `/dashboard` ; `/depot`, `/produits`, `/dashboard` répondent 200 avec le layout et la nav.
- `python -m app.seed` crée les 6 produits et leurs photos ; relançable sans erreur.
- `changer_etat` refuse une transition illégale (ex. `depose → vendue`) avec une erreur explicite.
- Rendu lisible sur un écran de téléphone (tester avec le mode responsive).

## Contraintes

- Python 3.12+, pas de dépendance hors liste. Pas d'ORM lourd (SQLAlchemy interdit) : SQL brut paramétré dans `db.py`.
- Ne rien implémenter des tickets suivants (pas d'upload, pas d'appel IA) — placeholders uniquement.
