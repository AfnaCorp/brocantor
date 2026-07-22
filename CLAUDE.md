# Brocantor

Pipeline personnel de mise en vente sur Leboncoin : photo depuis le téléphone → fiche produit générée par IA → validation humaine → publication semi-automatique → suivi des ventes. Usage strictement personnel (un seul utilisateur), hébergé 100 % en local sur un Mac mini. C'est un POC : privilégier le fonctionnel et la vitesse de livraison sur l'élégance.

## Objectif produit

Permettre un gros déstockage ponctuel (des dizaines d'objets) avec le minimum de friction humaine :

1. **Capture** (mobile, < 45 s/objet) : 1 à 5 photos + note texte optionnelle par produit.
2. **Analyse** (auto) : appel API Claude vision → titre, description, catégorie Leboncoin, fourchette de prix, hypothèses.
3. **Validation** (humain) : édition de la fiche, choix du prix final.
4. **Publication** (semi-auto) : userscript qui pré-remplit le formulaire Leboncoin dans le vrai Chrome de l'utilisateur ; le clic « Publier » reste humain. Fallback : boutons copier-coller.
5. **Suivi** (dashboard) : états, compteurs, marquer vendu.

Le cahier des charges complet est dans `docs/cahier-des-charges.md` — le lire avant toute décision d'architecture.

## Décisions techniques actées (ne pas remettre en cause sans demander)

- **Stack** : Python 3.12+, FastAPI, Jinja2 + HTMX (vendorisé dans `app/static/`), SQLite (fichier `data/app.db`), Pillow pour les images, SDK `anthropic` pour l'analyse. Une seule app, un seul process, worker asyncio intégré.
- **Pas de front séparé** (pas de React/Next), pas de Firebase, pas de cloud : tout vit sur le Mac mini.
- **Accès** : uniquement via Tailscale (réseau privé). Aucune authentification applicative — la sécurité EST Tailscale. Ne jamais exposer l'app sur Internet public.
- **Photos** : sur le filesystem (`data/photos/<id_produit>/`), chemins en base, jamais de blobs en base. Versions redimensionnées pour Leboncoin générées à l'analyse.
- **Publication** : JAMAIS d'automatisation de navigateur pilotée (Playwright/Puppeteer/CDP) — détectable par DataDome, risque de bannissement du compte Leboncoin. Le userscript Tampermonkey injecte du texte dans le formulaire mais n'automatise aucun clic. C'est une ligne rouge.
- **IA** : un appel Claude par produit, sortie JSON structurée (schéma dans le ticket T03). L'IA propose, l'humain dispose : jamais de prix publié sans validation humaine.

## Machine à états produit

```
déposé → en_traitement → à_valider → prête → publiée → vendue
              ↓                                  ↓
           erreur (relançable)              abandonnée
```

Transitions automatiques : `déposé → en_traitement → à_valider` (worker). Tout le reste est manuel. Chaque transition est journalisée dans la table `evenements`.

## Structure du repo

```
brocantor/
├── CLAUDE.md              ← ce fichier
├── docs/cahier-des-charges.md
├── backlog/
│   ├── backlog.md         ← liste des tickets + statuts (à tenir à jour !)
│   ├── tickets/           ← un prompt par ticket (T01…T08)
│   └── planning/plan-execution.md  ← ordre d'exécution et parallélisation
├── app/                   ← code applicatif (créé par T01)
│   ├── main.py            ← FastAPI, montage des routers
│   ├── db.py, models.py
│   ├── routers/           ← un router par domaine (depot, produits, dashboard, publication, api)
│   ├── templates/, static/
│   └── worker.py          ← file d'analyse IA (T03)
├── userscript/            ← script Tampermonkey (T07)
├── deploy/                ← launchd, doc Tailscale (T08)
└── data/                  ← app.db + photos/ (gitignoré)
```

## Conventions de travail

- **Langue** : UI et textes en français. Code (noms de variables/fonctions) en anglais, commentaires libres.
- **Mobile-first** : les écrans dépôt/fiches/dashboard sont d'abord utilisés depuis un téléphone. Gros boutons, peu de texte.
- **Un ticket = un périmètre de fichiers** : chaque ticket précise ses fichiers ; ne pas toucher aux fichiers des autres tickets (les routers vides créés en T01 délimitent les territoires — indispensable au travail en parallèle des subagents).
- **Backlog** : quand un ticket est terminé, mettre à jour son statut dans `backlog/backlog.md` (À faire → En cours → Fait) avec une ligne de commentaire.
- **Secrets** : `ANTHROPIC_API_KEY` dans `.env` (jamais commité). `.env.example` à jour.
- **Tests** : POC — pas de suite de tests exigée ; en revanche chaque ticket a des critères d'acceptation manuels à vérifier réellement avant de se déclarer Fait.
- **Dépendances** : gérées par **uv** (`pyproject.toml` + `uv.lock` figé) ; ajouter une dépendance = `uv add <paquet>` et la justifier dans le commit.

## Commandes

```bash
uv sync                           # installer (crée .venv/ aux versions de uv.lock)
cp .env.example .env              # puis renseigner la clé du provider visé par AI_MODEL
uv run uvicorn app.main:app --host 0.0.0.0 --port 8377 --reload   # dev
uv run python -m app.seed         # ⚠️ données de démo — EFFACE les données existantes
```

Gestion des dépendances : **uv**. `uv add <paquet>` pour en ajouter une (met à
jour `pyproject.toml` + `uv.lock`), `uv sync` pour réaligner le venv sur le lock.
Ne pas éditer `uv.lock` à la main. `requirements.txt` est conservé en export de
compatibilité — le régénérer avec `uv export` après tout changement.
