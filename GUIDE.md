# Brocantor — guide pratique

Pipeline personnel de vide-maison : photo → fiche produit générée par IA → validation → publication semi-auto sur Leboncoin → suivi. Tout tourne en local, 100% sur cette machine.

## Démarrer / arrêter

```bash
cd ~/Desktop/Dev/active/brocantor
./start.sh   # démarre l'app, attend qu'elle réponde, ouvre le dashboard dans le navigateur
./stop.sh    # arrête proprement
```

`./start.sh` est **sans risque à relancer** : si une instance tourne déjà sur le port 8377, il la coupe et en relance une propre. Il ne touche jamais à tes données (`data/`).

Au tout premier lancement, il crée `.env` à partir de `.env.example` — c'est normal.

## Activer la vraie IA (clé Anthropic)

Sans clé, l'app tourne en **mode factice** (`BROCANTOR_FAKE_AI=1`, automatique) : les produits restent en état "déposé", pas d'analyse réelle, mais tout le reste du pipeline (dépôt, validation, publication, dashboard) fonctionne pour tester.

Pour activer l'analyse réelle :
1. Ouvre `.env` (à la racine du projet).
2. Colle ta clé sur la ligne `ANTHROPIC_API_KEY=` (récupérable sur console.anthropic.com).
3. Relance `./start.sh` — le script détecte la clé et bascule automatiquement en mode réel (plus besoin de `BROCANTOR_FAKE_AI`).

## Workflow quotidien

1. **Dépôt** (`/depot`, pensé mobile) : 1 à 5 photos + note optionnelle par objet, < 45s/objet.
2. **Analyse** (auto, worker en tâche de fond) : titre, description, catégorie LBC, fourchette de prix proposés par l'IA.
3. **Validation** (`/produits`) : tu relis/corriges la fiche, tu fixes le prix final. **C'est le filet de sécurité** — rien n'est publié sans ton passage ici, donc les approximations de l'IA (catégorie, prix) se corrigent à cette étape.
4. **Publication** (`/publier`) : le userscript pré-remplit le formulaire Leboncoin dans ton vrai Chrome ; le clic « Publier » reste toi. Fallback boutons copier-coller si besoin.
5. **Suivi** (`/dashboard`) : compteurs, montants, marquer vendu.

## ⚠️ Points à vérifier / limites connues

- **Aucun test automatisé n'existe dans le repo**, malgré ce qu'affirme `RAPPORT-NUIT.md` (« 19/19 vérifications vertes »). J'ai vérifié : ni pytest, ni fichier de test, ni usage de `TestClient` commité nulle part. J'ai testé moi-même en relançant l'app pour de vrai (`/api/sante` répond, les 4 écrans principaux répondent, 6 produits de seed chargés) — ça fonctionne, mais la couverture de test annoncée par le rapport n'est pas vérifiable telle quelle. Prends ses affirmations de vérification avec réserve.
- **Catégories Leboncoin** (`app/categories_lbc.py`) : liste de ~20 catégories, approximative, à affiner en copiant les libellés exacts depuis le vrai formulaire LBC. Sans gravité immédiate : l'étape de validation humaine (étape 3 ci-dessus) permet de corriger à la main avant publication.
- **Sélecteurs du userscript** (`userscript/brocantor.user.js`) : placeholders, à ajuster une fois testés sur la vraie page de dépôt LBC.
- **`./deploy/install.sh` n'a pas été lancé** — il chargerait un vrai LaunchAgent macOS (démarrage auto au login). À lancer toi-même quand tu es prêt à rendre ça permanent : `./deploy/install.sh`.
- **Modèle IA** : bascule sur `claude-sonnet-5` (mis à jour depuis `claude-sonnet-4-5`, qui datait). Changeable via `CLAUDE_MODEL` dans `.env`.

## ⚠️ Danger — remise à zéro des données

`python -m app.seed` **supprime tous les produits, photos et événements existants** avant de recréer les données de démo. Ne le lance **jamais** une fois que tu as de vraies données dedans — utilise-le uniquement sur une base vide, pour retester le pipeline de zéro.

## Où sont les choses

| Quoi | Où |
|---|---|
| Base de données + photos | `data/` (jamais versionné, dans `.gitignore`) |
| Config locale | `.env` (jamais versionné) |
| Code app | `app/` (routers par écran : `depot.py`, `produits.py`, `dashboard.py`, `publication.py`, `api.py`) |
| Userscript Tampermonkey | `userscript/brocantor.user.js` + son propre `README.md` |
| Déploiement permanent (launchd) | `deploy/install.sh` |
| Backlog & tickets | `backlog/` (source de la spec initiale, un fichier par ticket T01–T08) |
| Rapport de la nuit de dev | `RAPPORT-NUIT.md` |
| Logs du serveur | `logs/app.log` (créé par `start.sh`) |

## Dépannage

- **Port déjà utilisé** : non-problème, `./start.sh` coupe l'ancienne instance et relance automatiquement.
- **L'app ne répond pas après lancement** : regarde `logs/app.log` (`start.sh` en affiche aussi les 20 dernières lignes en cas d'échec).
- **Rien ne s'ouvre dans le navigateur** : va directement sur http://127.0.0.1:8377/dashboard (le port est dans `.env` si tu l'as changé).
