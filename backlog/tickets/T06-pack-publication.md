# T06 — Pack de publication (page publier, boutons copier, photos prêtes)

> Prompt pour agent IA dev. Lire `CLAUDE.md` et `docs/cahier-des-charges.md` (§3.1 étape 4) avant de coder. Prérequis : T01 et T04 faits.

## Contexte

Le mode de publication fallback (et mobile) : tout ce qu'il faut pour publier une annonce Leboncoin en copier-coller, dans l'ordre exact du formulaire de dépôt. Doit rester fonctionnel même si le userscript (T07) casse — c'est le filet de sécurité permanent du projet.

## Périmètre de fichiers (strict)

`app/routers/publication.py`, `app/templates/publication*.html`, `app/static/publication.js`. Ne touche PAS aux autres routers/templates.

## Spécifications

1. **Page `/produits/{id}/publier`** — accessible seulement si état `prete` (sinon redirection vers le détail avec message). Blocs empilés **dans l'ordre du formulaire Leboncoin** : ① Titre ② Catégorie ③ Description ④ Prix ⑤ Photos. Les blocs ①–④ : valeur affichée + gros bouton « Copier » (API clipboard, feedback visuel « Copié ✓ » 2 s, marquer visuellement les blocs déjà copiés pour suivre où on en est).
2. **Bloc photos** — vignettes des versions LBC dans l'ordre, bouton « Tout télécharger (.zip) » (zip généré à la volée côté serveur, noms `1.jpg`…`5.jpg`) + téléchargement individuel. Note affichée si consultation mobile : « Tes photos sont déjà dans la pellicule du téléphone — publie depuis l'app Leboncoin, c'est encore plus rapide. »
3. **Lien dépôt** — gros bouton « Ouvrir le dépôt d'annonce Leboncoin » → `https://www.leboncoin.fr/deposer-une-annonce` dans un nouvel onglet.
4. **Clôture** — bloc final : champ « URL de l'annonce publiée » (optionnel) + bouton « Marquer publiée » → `changer_etat(id, "publiee")`, enregistre `url_annonce`, puis redirige vers la fiche prête suivante s'il y en a une (« Suivante : Vélo enfant → ») sinon vers le dashboard. C'est ce chaînage qui rend le batch fluide.
5. **File de publication `/publier`** — petite page listant les fiches `prete` dans l'ordre (plus ancienne d'abord) avec « Commencer » → première fiche. Lien depuis le dashboard déjà prévu par T05.

## Critères d'acceptation

- Sur le seed : la fiche `prete` affiche ses blocs dans le bon ordre ; chaque bouton copie la bonne valeur (vérifier au collage) ; le zip contient les bonnes photos aux bons noms.
- « Marquer publiée » avec URL → état `publiee`, URL en base, événement journalisé, redirection vers la suivante ou le dashboard.
- Un produit non-`prete` ne peut pas accéder à la page (redirection propre).
- Chrono réel sur une fiche du seed : publication simulée (copier chaque champ + télécharger zip) en < 2 min.

## Contraintes

- Toute transition passe par `changer_etat`. Aucune requête vers leboncoin.fr depuis le serveur — le navigateur de l'utilisateur fait tout.
- Le zip se génère en mémoire (pas de fichiers temporaires qui traînent).
