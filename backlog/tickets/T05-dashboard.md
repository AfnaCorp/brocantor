# T05 — Dashboard de suivi (compteurs, filtres, actions d'état)

> Prompt pour agent IA dev. Lire `CLAUDE.md` et `docs/cahier-des-charges.md` (§3.2, §3.3) avant de coder. Prérequis : T01 fait. Travaille sur les données du seed — n'attends ni T02 ni T04.

## Contexte

La tour de contrôle du déstockage : où en est le stock, qu'est-ce qui attend une action humaine, combien ça a rapporté. Consulté au téléphone plusieurs fois par jour pendant le déstockage.

## Périmètre de fichiers (strict — d'autres agents travaillent en parallèle)

`app/routers/dashboard.py`, `app/templates/dashboard*.html`. Ne touche PAS à `main.py`, `db.py`, `models.py`, ni aux autres routers/templates.

## Spécifications

1. **Bandeau compteurs** — une tuile par état (En traitement / À valider / Prêtes / Publiées / Vendues / Erreur) avec le nombre ; tuile cliquable → liste filtrée en dessous (HTMX). Les tuiles « À valider » et « Erreur » visuellement saillantes quand > 0 (c'est là qu'on attend l'humain).
2. **Tuiles argent** — « Valeur estimée en vente » (somme des `prix_choisi` des publiées + prêtes) et « Total vendu » (somme des `prix_vente_reel`). Chiffres gros et lisibles.
3. **Liste d'action** — sous les compteurs, liste compacte des produits (vignette, titre, prix, état, ancienneté dans l'état) avec **actions rapides en un tap selon l'état** :
   - `prete` → « Publier » (lien vers `/produits/{id}/publier`, page de T06 — le lien peut être mort tant que T06 n'est pas fait, c'est accepté)
   - `publiee` → « Vendu ! » (ouvre un mini-formulaire HTMX : prix de vente réel pré-rempli avec `prix_choisi`, valide → `changer_etat(id, "vendue")` + `vendu_le` + `prix_vente_reel`) et « Retirer » (→ `abandonnee`, confirmation)
   - `erreur` → « Relancer » (POST `/api/produits/{id}/relancer` — endpoint de T03 ; si 404 car T03 pas encore fait, afficher un toast « bientôt »)
   - tous → lien vers le détail `/produits/{id}`
4. **Ancienneté** — pour les `publiee` : afficher « en ligne depuis X j » ; au-delà de 10 jours, badge discret « prix à revoir ? ». (Pas de notification — juste visuel.)
5. **Rafraîchissement** — la page se recharge d'elle-même toutes les 60 s (HTMX polling léger sur le bandeau) pour voir avancer le worker pendant un batch.

## Critères d'acceptation

- Sur le seed : compteurs exacts, tuiles filtrantes fonctionnelles, sommes d'argent justes.
- Marquer le produit `publiee` du seed comme vendu à 25 € → compteurs et « Total vendu » mis à jour, événement journalisé, `vendu_le` renseigné.
- Le badge « prix à revoir ? » apparaît sur un produit publié artificiellement vieilli (modifier la date en base pour tester).
- Lisible et actionnable au pouce sur téléphone.

## Contraintes

- Toute transition passe par `changer_etat`. Aucune logique métier dupliquée : les sommes se calculent en SQL dans le router.
