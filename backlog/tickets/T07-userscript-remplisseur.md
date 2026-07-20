# T07 — Userscript remplisseur (API next/publiee + script Tampermonkey)

> Prompt pour agent IA dev. Lire `CLAUDE.md` (ligne rouge sur l'automatisation) et `docs/cahier-des-charges.md` (§2.1, §4) avant de coder. Prérequis : T06 fait.

## Contexte

Le mode de publication nominal desktop : sur la page de dépôt Leboncoin, dans le vrai Chrome de l'utilisateur, un bouton injecte les champs de la prochaine fiche prête. **Ligne rouge absolue** : injection de TEXTE uniquement — aucun clic automatisé, aucune soumission, aucune navigation déclenchée par le script. L'utilisateur glisse les photos et clique « Publier » lui-même. Ne jamais utiliser ni suggérer Playwright/Puppeteer/CDP.

## Périmètre de fichiers (strict)

`app/routers/api.py` (section commentée `# T07`), `userscript/brocantor.user.js`, `userscript/README.md`. Ne touche PAS aux autres fichiers.

## Spécifications

1. **API** — deux endpoints JSON dans `routers/api.py` :
   - `GET /api/publication/next` → la fiche `prete` la plus ancienne : `{id, titre, description, categorie_lbc, prix_choisi, photos_zip_url, restantes: N}` ou `204` si aucune.
   - `POST /api/publication/{id}/publiee` (body : `{url_annonce?}`) → `changer_etat(id, "publiee")` + URL. `409` si le produit n'est pas `prete`.
   - **CORS** : autoriser uniquement l'origine `https://www.leboncoin.fr` sur ces deux routes (middleware ciblé, pas un CORS global `*`). Pas d'authentification : l'app n'est joignable que via Tailscale, c'est le modèle de sécurité assumé du projet.
2. **Userscript** (`brocantor.user.js`) — en-tête Tampermonkey : `@match https://www.leboncoin.fr/deposer-une-annonce*`, `@grant GM_xmlhttpRequest`, `@connect` sur l'hôte Tailscale. **L'URL de l'app et TOUS les sélecteurs CSS du formulaire regroupés dans un bloc `CONFIG` en tête de fichier** avec commentaire « à ajuster si Leboncoin change son formulaire » — c'est la seule zone de maintenance prévue.
3. **UI du script** — panneau flottant discret en coin de page : « Brocantor — N fiches prêtes », bouton « Remplir la prochaine fiche ». Au clic : fetch `next`, remplissage des champs titre/description/prix (renseigner la valeur PUIS déclencher les événements `input`/`change` pour que le framework front de Leboncoin enregistre la saisie), affichage dans le panneau de la catégorie à sélectionner à la main et d'un lien « télécharger les photos » (`photos_zip_url`). Les sélecteurs introuvables ne font pas planter le script : le panneau liste ce qui a été rempli et ce qui reste à faire à la main, avec la valeur à copier en un clic.
4. **Clôture depuis le panneau** — bouton « Annonce publiée ✓ » (l'utilisateur clique APRÈS avoir soumis lui-même) : demande l'URL de l'annonce (pré-remplie avec l'URL courante si on est sur la page de confirmation), POST `publiee`, le panneau passe à la fiche suivante.
5. **Doc** (`userscript/README.md`) — installation Tampermonkey, import du script, configuration de l'URL Tailscale, procédure « le formulaire a changé : comment retrouver les sélecteurs en 10 min » (inspecteur → mettre à jour CONFIG).

## Critères d'acceptation

- Endpoints testables au curl : `next` renvoie la bonne fiche du seed, `publiee` change l'état, `409` sur un produit non prêt, CORS refusé pour une autre origine.
- Script chargé dans Tampermonkey sans erreur ; sur une page de test locale reproduisant des champs de formulaire, le remplissage + événements `input` fonctionnent.
- Test réel sur la page de dépôt Leboncoin (fait par l'utilisateur) : champs remplis, aucune action automatique, publication humaine, clôture OK.
- Sélecteur volontairement cassé → le panneau le signale proprement avec fallback copier, sans casser le reste.

## Contraintes

- Aucune dépendance externe dans le userscript (vanilla JS, un seul fichier).
- Le script ne stocke rien (pas de localStorage) : l'état vit côté app.
- Interdiction formelle de `.click()`, `.submit()`, ou de toute simulation d'interaction au-delà des événements de saisie sur les champs remplis.
