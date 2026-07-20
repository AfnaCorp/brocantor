# T03 — Worker d'analyse IA (file async, appel Claude vision, images LBC)

> Prompt pour agent IA dev. Lire `CLAUDE.md` et `docs/cahier-des-charges.md` (§4.2) avant de coder. Prérequis : T01 et T02 faits.

## Contexte

Le cœur de la valeur : transformer photos + note en fiche produit publiable. Doit encaisser un batch de 30 produits déposés d'affilée sans intervention, et rendre les échecs visibles et relançables.

## Périmètre de fichiers (strict)

`app/worker.py`, `app/analyse.py` (appel IA + prompt), `app/images.py` (redimensionnement), `app/categories_lbc.py` (taxonomie statique). Une seule modification hors périmètre autorisée : 3 lignes dans `main.py` pour démarrer/arrêter le worker via le lifespan FastAPI.

## Spécifications

1. **Worker** (`worker.py`) — tâche asyncio lancée au startup : boucle qui, toutes les 3 s, prend les produits en état `depose` (max 2 en parallèle via semaphore), passe chacun à `en_traitement` (via `changer_etat`), traite, puis `a_valider` ou `erreur`. Redémarrage propre : au boot, les produits bloqués en `en_traitement` (crash précédent) repassent à `depose`.
2. **Images** (`images.py`) — pour chaque photo du produit : générer la version Leboncoin (JPEG, côté max 1200 px, qualité 85, poids < 500 Ko) dans `data/photos/<id>/lbc_<position>.jpg`, renseigner `chemin_lbc` en base.
3. **Analyse** (`analyse.py`) — un appel API Claude (SDK `anthropic`, modèle vision courant — le lire depuis `.env`, clé `CLAUDE_MODEL`, avec un défaut raisonnable) avec : les photos versions LBC (base64), la `note_utilisateur`, et un prompt système qui impose la sortie JSON stricte suivante (utiliser le tool-use / structured output du SDK pour forcer le schéma) :

```json
{
  "titre": "≤ 50 caractères, style annonce Leboncoin",
  "description": "3 à 6 phrases honnêtes : ce que c'est, état, défauts visibles, dimensions estimées si pertinent",
  "categorie_lbc": "un libellé EXACT de la liste fournie",
  "prix_min": 0, "prix_max": 0,
  "confiance": "haute|moyenne|basse",
  "hypotheses": ["suppositions faites (modèle exact, année, fonctionnement non vérifiable sur photo)"],
  "questions": ["infos manquantes qui amélioreraient la fiche"]
}
```

   Consignes de ton dans le prompt : honnête sur les défauts (évite les litiges, augmente la confiance acheteur), pas de superlatifs creux, prix pour de l'occasion entre particuliers en France. La note utilisateur prime sur les suppositions visuelles (si la note dit « acheté 300 € en 2021 », s'en servir pour la fourchette).
4. **Catégories** (`categories_lbc.py`) — liste Python statique des catégories/sous-catégories Leboncoin pertinentes pour un vide-maison (Ameublement, Électroménager, Image & Son, Informatique, Téléphonie, Vêtements, Sport & Plein air, Bricolage, Jardin, Puériculture, Jeux & Jouets, Livres/CD/DVD, Décoration, Vélos, Collection, Autres). Le libellé retourné par l'IA DOIT appartenir à cette liste (valider ; sinon « Autres » + hypothèse ajoutée). Marquer un `# TODO utilisateur : affiner depuis le formulaire réel de dépôt LBC`.
5. **Robustesse** — retry ×3 avec backoff exponentiel (2 s/8 s/30 s) sur erreurs API ; au-delà : état `erreur`, message dans `erreur_derniere`, `tentatives` incrémenté. Réponse JSON invalide malgré le schéma forcé = erreur aussi. Route POST `/api/produits/{id}/relancer` (dans ton périmètre : l'ajouter à `routers/api.py` est autorisé, section commentée `# T03`) qui repasse un produit `erreur` en `depose`.
6. **Coût & logs** — logger par produit : durée, tokens in/out si dispo, résultat. Ne jamais re-analyser un produit déjà `a_valider` ou plus loin.

## Critères d'acceptation

- Seed + 2 produits réels déposés via `/depot` → fiches complètes en `a_valider` sans intervention, versions LBC générées, champs remplis et catégorie valide.
- Couper le réseau pendant une analyse → le produit finit en `erreur` avec message lisible ; `/api/produits/{id}/relancer` le fait repartir et aboutir.
- Tuer l'app pendant un traitement puis redémarrer → aucun produit ne reste coincé en `en_traitement`.
- 6 produits déposés d'un coup → tous traités, jamais plus de 2 appels API simultanés.

## Contraintes

- L'IA ne décide jamais seule d'un état au-delà de `a_valider`. Pas d'appel réseau autre que l'API Anthropic.
- Si `ANTHROPIC_API_KEY` absente : le worker démarre, log un avertissement clair, et laisse les produits en `depose` (pas de crash).
