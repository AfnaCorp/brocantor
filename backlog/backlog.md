# Backlog — Brocantor

Chaque ticket a son prompt agent dans `tickets/T0X-*.md`. L'ordre d'exécution et la parallélisation sont dans `planning/plan-execution.md`. **Tenir la colonne Statut à jour** (À faire / En cours / Fait) — c'est la source de vérité de l'avancement.

| ID | Titre | Dépend de | Parallélisable avec | Effort | Statut |
|----|-------|-----------|---------------------|--------|--------|
| T01 | Socle applicatif : FastAPI, SQLite, layout, routers vides, seed | — | rien (bloquant) | ½ j | Fait |
| T02 | Dépôt mobile : PWA de capture photos + note | T01 | T04, T05 | 1 j | Fait |
| T03 | Worker d'analyse IA : file async, appel Claude vision, images LBC | T01, T02 | T06 | 1–1,5 j | Fait |
| T04 | Fiches produits : liste, détail, édition, validation | T01 | T02, T05 | 1 j | Fait |
| T05 | Dashboard de suivi : compteurs, filtres, actions d'état | T01 | T02, T04 | ½ j | Fait |
| T06 | Pack de publication : page publier, boutons copier, photos prêtes | T01, T04 | T03 | ½ j | Fait |
| T07 | Userscript remplisseur : API next/publiee + script Tampermonkey | T06 | T08 | ½–1 j | À faire |
| T08 | Déploiement Mac mini : launchd, Tailscale HTTPS, sauvegarde | T01 | T07 | ½ j | À faire |

## Journal de nuit (2026-07-21)

- **T01 Fait** : socle FastAPI + SQLite complet. App démarre (lifespan `init_db`), `/` → `/dashboard` (307), routes `/depot|/produits|/dashboard|/api/health` en 200, layout mobile + nav 3 onglets + HTMX vendorisé, seed 6 produits (tous états) idempotent, `changer_etat` refuse les transitions illégales. Env : venv Python 3.14 (`.venv/`), Starlette `TemplateResponse(request, name, ctx)` (nouvelle signature). Photos servies via `/photos`.

- **T02 Fait** : dépôt mobile. `GET /depot` (formulaire capture + note), `POST /depot` multipart crée un produit à `depose`, photos nommées `photo_<pos>.jpg`, note en base. Compression canvas côté client (max 1600px, JPEG 0,85), upload XHR avec barre de progression + bouton Réessayer (sélection conservée), toast + compteur de session, reset sans rechargement. PWA : `manifest.json` (start_url `/depot`, standalone) + icônes 192/512 générées, lien déjà dans `base.html`. Pas de service worker (choix ticket). Vérifié serveur : POST 3 photos → produit `depose` + fichiers/positions OK, refus 0 photo et >5. **À vérifier par Wassim (téléphone réel)** : compression effective <800Ko, install PWA plein écran, <45s/objet, reprise après coupure réseau.

- **T03 Fait** : worker IA. Boucle asyncio (scan 3s, semaphore concurrence=2), `depose→en_traitement→a_valider|erreur`, reprise crash (`en_traitement→depose` au boot). `images.py` génère versions LBC (max 1200px, q85, <500Ko), `analyse.py` appel Claude vision en tool-use (schéma JSON forcé, retry ×3 backoff 2/8/30s, note utilisateur prioritaire), `categories_lbc.py` (16 catégories + validation → « Autres »). Route `POST /api/produits/{id}/relancer` (erreur→depose). Câblage : 3 lignes dans `main.py` (lifespan). **IMPORTANT** — sans clé API, mode factice `BROCANTOR_FAKE_AI=1` : fiche déterministe SANS réseau, utilisé pour tous les tests de cette nuit. Vérifié (fake) : dépôt→a_valider + LBC + champs remplis ; chemin erreur→`erreur`+message+tentatives++ ; relance→a_valider ; reprise crash ; 8 produits d'un coup tous traités, concurrence max observée = 2 ; sans clé le worker idle sans crash. **À vérifier par Wassim (nécessite ANTHROPIC_API_KEY)** : qualité réelle des fiches, respect du schéma tool-use, coût/tokens — le chemin `_appel_reel` n'a PAS pu être exécuté (aucune clé cette nuit).

- **T04 Fait** : fiches produits. Liste grille + puces de filtre (Tous/À valider/Prêtes/Publiées/Vendues/Erreur), a_valider en premier. Détail = preview d'annonce (carrousel LBC, titre, bloc prix fourchette+confiance+prix choisi éditable+lien comparables LBC, description, catégorie). Édition inline HTMX par bloc (crayon → champ → Enregistrer/Annuler, sauvegarde immédiate). Contexte IA repliable (hypothèses/questions/note). Validation : bouton visible en `a_valider`, exige titre+description+catégorie+prix → `prete` (event journalisé) ; édition d'une fiche `prete` la laisse `prete`. Abandonner (confirmation → `abandonnee`), notes libres, historique repliable. **Chemin critique T01→T04 = POC complet vérifié** : dépôt → IA (fake) → a_valider → validation → prete, de bout en bout. **À vérifier par Wassim (mobile réel)** : fluidité tactile ≥48px, absence de zoom involontaire, ouverture du lien comparables.

- **T05 Fait** : dashboard. Bandeau 6 tuiles compteurs (cliquables → liste filtrée HTMX ; À valider/Erreur saillantes si >0), 2 tuiles argent (valeur estimée = Σ prix_choisi prête+publiée ; total vendu = Σ prix_vente_reel, en SQL). Liste d'action avec actions rapides par état : prête→Publier, publiée→« Vendu ! » (mini-form prix pré-rempli → `vendue`+`vendu_le`+`prix_vente_reel`) & Retirer, erreur→Relancer (POST T03), a_valider→Valider, tous→Détail. Ancienneté « en ligne depuis X j » + badge « prix à revoir ? » au-delà de 10 j. Auto-refresh 60s + rafraîchissement immédiat via HX-Trigger `dashboard-maj`. Vérifié (TestClient) : compteurs/sommes exacts (274 € / 110 €), vendu à 25 € → total 135 € + event + vendu_le, badge sur produit vieilli 15 j, retirer → abandonnee.

- **T06 Fait** : pack de publication. Page `/produits/{id}/publier` (prête uniquement, sinon redirect détail), blocs ordre LBC ①Titre ②Catégorie ③Description ④Prix (boutons Copier clipboard + feedback « Copié ✓ » + marquage bloc copié) ⑤Photos (vignettes LBC + zip à la volée en mémoire, noms `1.jpg…`, download individuel, note mobile). Gros bouton lien dépôt LBC. Clôture : URL optionnelle + « Marquer publiée » → `publiee`+url, **chaînage vers la fiche prête suivante** (sinon dashboard). File `/publier` (prêtes, plus ancienne d'abord, « Commencer »). Router sans préfixe (sert `/publier` + `/produits/{id}/publier`), `main.py` inchangé. Vérifié (TestClient) : ordre des blocs, zip `['1.jpg','2.jpg']`, non-prête→303, marquer publiée→publiee+url+event+redirect suivante, file OK. **Note** : lien dashboard→`/publier` non ajouté (territoire T05 déjà commité) — accès direct `/publier` fonctionnel.

## Chemin critique POC

`T01 → T02 → T03 → T04` donne un POC de bout en bout (photographier → fiche IA → valider). T05/T06/T07/T08 transforment le POC en outil de déstockage complet.

## Définition de « Fait »

Un ticket est Fait quand : ses critères d'acceptation ont été vérifiés pour de vrai (pas « ça devrait marcher »), le backlog est mis à jour, et rien n'est cassé dans ce qui marchait avant (`uvicorn` démarre, les pages existantes répondent).

## Hors périmètre (rappel — ne pas implémenter)

Automatisation de navigateur pilotée (CDP/Playwright), lecture de la messagerie Leboncoin, scraping des comparables, authentification applicative, multi-utilisateurs, Whisper auto-hébergé, multi-plateformes (Vinted, etc.).
