# Backlog — Brocantor

Chaque ticket a son prompt agent dans `tickets/T0X-*.md`. L'ordre d'exécution et la parallélisation sont dans `planning/plan-execution.md`. **Tenir la colonne Statut à jour** (À faire / En cours / Fait) — c'est la source de vérité de l'avancement.

| ID | Titre | Dépend de | Parallélisable avec | Effort | Statut |
|----|-------|-----------|---------------------|--------|--------|
| T01 | Socle applicatif : FastAPI, SQLite, layout, routers vides, seed | — | rien (bloquant) | ½ j | Fait |
| T02 | Dépôt mobile : PWA de capture photos + note | T01 | T04, T05 | 1 j | À faire |
| T03 | Worker d'analyse IA : file async, appel Claude vision, images LBC | T01, T02 | T06 | 1–1,5 j | À faire |
| T04 | Fiches produits : liste, détail, édition, validation | T01 | T02, T05 | 1 j | À faire |
| T05 | Dashboard de suivi : compteurs, filtres, actions d'état | T01 | T02, T04 | ½ j | À faire |
| T06 | Pack de publication : page publier, boutons copier, photos prêtes | T01, T04 | T03 | ½ j | À faire |
| T07 | Userscript remplisseur : API next/publiee + script Tampermonkey | T06 | T08 | ½–1 j | À faire |
| T08 | Déploiement Mac mini : launchd, Tailscale HTTPS, sauvegarde | T01 | T07 | ½ j | À faire |

## Journal de nuit (2026-07-21)

- **T01 Fait** : socle FastAPI + SQLite complet. App démarre (lifespan `init_db`), `/` → `/dashboard` (307), routes `/depot|/produits|/dashboard|/api/health` en 200, layout mobile + nav 3 onglets + HTMX vendorisé, seed 6 produits (tous états) idempotent, `changer_etat` refuse les transitions illégales. Env : venv Python 3.14 (`.venv/`), Starlette `TemplateResponse(request, name, ctx)` (nouvelle signature). Photos servies via `/photos`.

## Chemin critique POC

`T01 → T02 → T03 → T04` donne un POC de bout en bout (photographier → fiche IA → valider). T05/T06/T07/T08 transforment le POC en outil de déstockage complet.

## Définition de « Fait »

Un ticket est Fait quand : ses critères d'acceptation ont été vérifiés pour de vrai (pas « ça devrait marcher »), le backlog est mis à jour, et rien n'est cassé dans ce qui marchait avant (`uvicorn` démarre, les pages existantes répondent).

## Hors périmètre (rappel — ne pas implémenter)

Automatisation de navigateur pilotée (CDP/Playwright), lecture de la messagerie Leboncoin, scraping des comparables, authentification applicative, multi-utilisateurs, Whisper auto-hébergé, multi-plateformes (Vinted, etc.).
