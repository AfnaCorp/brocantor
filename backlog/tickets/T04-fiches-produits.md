# T04 — Fiches produits (liste, détail, édition, validation)

> Prompt pour agent IA dev. Lire `CLAUDE.md` et `docs/cahier-des-charges.md` (§3.1 étape 3, §3.2) avant de coder. Prérequis : T01 fait. Travaille sur les données du seed (`python -m app.seed`) — n'attends ni T02 ni T03.

## Contexte

L'écran de validation humaine : l'utilisateur relit ce que l'IA a produit, corrige, fixe le prix, valide. Utilisé au téléphone depuis le canapé. La preview doit montrer la fiche **telle qu'elle apparaîtra sur Leboncoin**.

## Périmètre de fichiers (strict — d'autres agents travaillent en parallèle)

`app/routers/produits.py`, `app/templates/produits*.html` (liste + détail + fragments HTMX), `app/static/produits.css` si besoin. Ne touche PAS à `main.py`, `db.py`, `models.py`, ni aux autres routers/templates.

## Spécifications

1. **Liste `/produits`** — grille de cartes : vignette (photo 1), titre (ou « En cours d'analyse… »), prix choisi ou fourchette, badge d'état coloré. Filtre par état via une rangée de puces cliquables en haut (Tous / À valider / Prêtes / Publiées / Vendues / Erreur). Tri : plus récent d'abord. Les produits `a_valider` en premier par défaut (c'est là qu'on attend l'humain).
2. **Détail `/produits/{id}` — preview d'annonce** — présentation par blocs dans l'ordre Leboncoin : carrousel photos (versions LBC si dispo, sinon originales), titre, prix, description, catégorie. Chaque bloc a un bouton crayon → édition inline HTMX (le bloc devient un champ, Enregistrer/Annuler, sauvegarde immédiate en base).
3. **Bloc prix** — affiche la fourchette IA (`prix_min`–`prix_max` €), le niveau de confiance, et un champ « Prix choisi » pré-rempli avec une valeur ronde proche de la fourchette haute. Bouton « Voir les annonces comparables » → ouvre `https://www.leboncoin.fr/recherche?text=<titre urlencodé>` dans un nouvel onglet.
4. **Bloc contexte IA** — repliable, sous la fiche : `hypotheses_ia` (« L'IA a supposé… »), `questions_ia` (« Infos qui amélioreraient la fiche »), note utilisateur d'origine. But : l'utilisateur voit ce qui est incertain avant de valider.
5. **Validation** — bouton principal « Valider la fiche » (visible seulement en état `a_valider`) : exige titre, description, catégorie et prix choisi non vides, puis `changer_etat(id, "prete")`. Si l'utilisateur modifie un champ d'une fiche déjà `prete`, elle reste `prete` (pas de retour arrière automatique).
6. **Actions secondaires** — sur le détail : « Abandonner » (→ `abandonnee`, avec confirmation), champ `notes` libre toujours éditable, historique des événements du produit (repliable, depuis la table `evenements`).

## Critères d'acceptation

- Sur les données du seed : la liste s'affiche avec états et filtres corrects ; le produit `a_valider` du seed peut être entièrement relu, corrigé (titre + prix), puis validé → `prete`, événement journalisé.
- Tenter de valider une fiche sans prix → message d'erreur clair, pas de changement d'état.
- Édition inline fluide au téléphone (mode responsive) : cibles tactiles ≥ 48 px, pas de zoom involontaire.
- Le lien comparables ouvre la recherche Leboncoin avec le bon titre.

## Contraintes

- Toute transition d'état passe par `changer_etat` de `models.py`. HTMX pour l'édition inline, JS minimal.
- Pas de bouton « Publier » ici — c'est T06 (juste un lien vers `/produits/{id}/publier` si l'état est `prete`, la page existera plus tard).
