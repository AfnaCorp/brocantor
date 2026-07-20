# Userscript Brocantor — remplisseur Leboncoin

Injecte la prochaine fiche **prête** dans le formulaire de dépôt Leboncoin, dans
ton vrai Chrome. **Injection de texte uniquement** : le script ne clique sur
rien, ne soumet rien. Tu glisses les photos et cliques « Publier » toi-même.

C'est le mode nominal desktop ; le fallback copier-coller reste la page
`/produits/{id}/publier` de l'app (toujours fonctionnelle si le formulaire LBC
change).

## Installation

1. Installe l'extension **Tampermonkey** (Chrome/Edge/Firefox).
2. Tampermonkey → **Créer un nouveau script** → colle le contenu de
   `brocantor.user.js` → **Enregistrer** (Ctrl/Cmd+S).
3. **Configure** (2 endroits, même valeur) :
   - En-tête `// @connect  CHANGE-ME.ts.net` → ton hôte Tailscale
     (ex. `macmini.tail1234.ts.net`).
   - Bloc `CONFIG.appUrl` → `https://macmini.tail1234.ts.net` (sans `/` final).
4. Recharge la page de dépôt Leboncoin. Un panneau « 🜂 Brocantor » apparaît en
   bas à droite.

## Utilisation

1. Va sur `https://www.leboncoin.fr/deposer-une-annonce`.
2. Panneau → **Remplir la prochaine fiche** : titre, description et prix sont
   injectés. La **catégorie** est affichée pour sélection manuelle (bouton
   Copier). Tout champ non trouvé est listé avec sa valeur à copier.
3. **Télécharger les photos (.zip)** → glisse-les dans le formulaire.
4. Vérifie, puis clique **Publier** (bouton Leboncoin, par toi).
5. Panneau → **Annonce publiée ✓** : saisis l'URL (pré-remplie), l'app marque la
   fiche `publiee` et passe à la suivante.

## Le formulaire a changé ? (maintenance en 10 min)

Si le remplissage échoue (champs listés « à coller » au lieu d'être remplis) :

1. Sur la page de dépôt, clic droit sur le champ concerné → **Inspecter**.
2. Repère un sélecteur stable : `name`, `id`, ou un attribut `data-*`.
3. Mets à jour la valeur correspondante dans **`CONFIG.selectors`** en tête de
   `brocantor.user.js` (c'est la seule zone à toucher).
4. Enregistre le script, recharge la page.

Le script ne plante jamais sur un sélecteur manquant : il bascule en mode
« copier à la main » pour ce champ.

## Sécurité & garde-fous

- Aucune requête du **serveur** vers leboncoin.fr : tout part de ton navigateur.
- CORS côté app limité à l'origine `https://www.leboncoin.fr`.
- Pas d'authentification : l'app n'est joignable que via **Tailscale**.
- Le script ne stocke rien (pas de `localStorage`) ; l'état vit dans l'app.
- Interdits par conception : `.click()`, `.submit()`, navigation automatique.

## Test local rapide (sans Leboncoin)

Pour vérifier le remplissage sans toucher Leboncoin, crée une page HTML locale
avec `<input name="subject">`, `<textarea name="body">`, `<input name="price">`,
change temporairement `@match` vers `file:///…` et l'`appUrl` vers ton app :
le panneau doit remplir les trois champs et déclencher les événements `input`.
