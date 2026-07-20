# T02 — Dépôt mobile (PWA de capture photos + note)

> Prompt pour agent IA dev. Lire `CLAUDE.md` et `docs/cahier-des-charges.md` (§3.1 étape 1) avant de coder. Prérequis : T01 fait.

## Contexte

C'est l'écran le plus utilisé en phase de déstockage : l'utilisateur enchaîne 30 objets debout dans un garage, au téléphone, parfois en 4G via Tailscale. Chaque seconde de friction compte. Objectif : **moins de 45 secondes par objet**.

## Périmètre de fichiers (strict — d'autres agents travaillent en parallèle)

`app/routers/depot.py`, `app/templates/depot*.html`, `app/static/depot.js`, `app/static/manifest.json` + icônes. Tu peux ajouter un lien vers le manifest dans `base.html` (seule modification autorisée hors périmètre, une ligne). Ne touche PAS à `main.py`, `db.py`, `models.py`, ni aux autres routers/templates.

## Spécifications

1. **Page `/depot`** — un seul écran : zone « Ajouter des photos » (`<input type="file" accept="image/*" capture="environment" multiple>`), aperçu vignettes des photos choisies avec suppression individuelle, champ note (`<textarea>` avec placeholder incitant à dicter : prix d'achat, défauts, marque/modèle), gros bouton « Envoyer ». Limite 1 à 5 photos, ordre de sélection conservé (= position).
2. **Compression côté client** — `depot.js` : avant upload, redimensionner chaque photo via canvas (côté max 1600 px, JPEG qualité 0,85). Les originaux pleine résolution ne quittent pas le téléphone — la version compressée EST l'original côté serveur.
3. **Upload robuste** — POST `/depot` en `multipart/form-data`, une requête par produit (photos + note ensemble, taille raisonnable après compression). Barre de progression, gestion d'échec avec bouton « Réessayer » sans perdre les photos sélectionnées. Timeout généreux (4G).
4. **Côté serveur** — créer le produit directement à l'état initial `depose` (pas de transition à journaliser pour la création), enregistrer les photos dans `data/photos/<id_produit>/photo_<position>.jpg`, lignes en table `photos`, note en `note_utilisateur`.
5. **Enchaînement** — après envoi réussi : toast « Produit #N envoyé ✓ » et retour immédiat à un formulaire vierge, prêt pour l'objet suivant. Compteur de la session visible (« 7 envoyés »).
6. **PWA minimale** — `manifest.json` (nom Brocantor, icône générée simple, display standalone, start_url `/depot`), lien dans le layout. PAS de service worker (le cache offline n'apporte rien ici et complique tout).

## Critères d'acceptation

- Depuis un vrai téléphone (ou simulateur mobile) : créer un produit avec 3 photos + note en < 45 s.
- Les fichiers arrivent compressés (< 800 Ko/photo typique), bien nommés, positions correctes en base.
- Un échec réseau simulé (couper le serveur pendant l'upload) affiche l'erreur et permet de réessayer sans re-sélectionner les photos.
- « Ajouter à l'écran d'accueil » fonctionne et ouvre l'app en plein écran sur `/depot`.
- Enchaîner 3 produits d'affilée sans recharger la page.

## Contraintes

- JS vanilla (pas de framework, pas de build). HTMX autorisé pour ce qui est simple, mais la compression canvas est du JS pur.
- Ne pas déclencher l'analyse IA (c'est T03 qui consomme l'état `depose`).
