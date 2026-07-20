# Rapport de nuit — Brocantor (21 juillet 2026)

**Bilan : les 8 tickets (T01→T08) sont terminés, testés et commités.** Chemin
critique du POC (T01→T02→T03→T04) atteint et vérifié de bout en bout, puis
T05→T08 finis avec du temps en rab. Un commit par ticket. Aucun blocage.

## Lancer l'app au réveil

```bash
cd /Users/bourbiawassim/Desktop/Dev/active/brocantor

# Le venv est déjà créé : .venv (Python 3.14, car le python système est 3.9 < 3.12 requis)
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8377
# → http://localhost:8377  (redirige vers /dashboard)

# (Optionnel) réinjecter les 6 produits de démo :
.venv/bin/python -m app.seed
```

- **Sans clé API** : l'app tourne, le worker démarre mais laisse les produits en
  `depose` (avertissement clair dans les logs). Normal.
- **Tester le pipeline IA sans clé** : préfixer la commande par
  `BROCANTOR_FAKE_AI=1` → fiches factices déterministes, **aucun appel réseau**.
- **Avec clé réelle** : renseigner `.env` (`cp .env.example .env` puis
  `ANTHROPIC_API_KEY=…` et éventuellement `CLAUDE_MODEL=…`).

## Preuves de vérification (par ticket)

Tous les tests ont été exécutés via le vrai stack ASGI (Starlette `TestClient`,
qui déclenche le lifespan/worker) et, en fin de nuit, via un **vrai serveur
uvicorn** lancé en sous-processus.

- **T01 Socle** : `uvicorn` démarre pour de vrai (`/api/sante` → 200) ; `/`→`/dashboard`
  (307) ; `/depot /produits /dashboard` → 200 avec layout + nav 3 onglets + HTMX ;
  `app.db` créée avec les 3 tables ; `python -m app.seed` crée 6 produits + 12 photos,
  relançable ; `changer_etat` refuse `depose→vendue` (TransitionIllegale) et un état
  inconnu, accepte `depose→en_traitement` en journalisant l'événement.
- **T02 Dépôt** : `POST /depot` (3 photos + note) → produit `depose`, fichiers
  `photo_<pos>.jpg` aux bonnes positions, note en base ; refus 0 photo et >5 (400).
  Compression/PWA/reprise réseau = côté client (à valider sur téléphone).
- **T03 Worker IA** (mode factice) : dépôt → `a_valider` avec versions LBC + champs
  remplis + catégorie valide ; chemin d'erreur → `erreur` + message + `tentatives++` ;
  `POST /api/produits/{id}/relancer` → repart et aboutit ; reprise après crash
  (`en_traitement`→`depose` au boot) ; 8 produits d'un coup tous traités, **concurrence
  max mesurée = 2** ; sans clé, worker idle sans crash.
- **T04 Fiches** : liste + 6 filtres ; détail (carrousel, bloc prix, comparables) ;
  édition inline (titre/prix/description) persistée ; validation sans prix refusée
  (message), complète → `prete` + événement ; édition d'une fiche `prete` la laisse
  `prete` ; abandon → `abandonnee`.
- **T05 Dashboard** : 6 tuiles + sommes SQL exactes (274 € estimé, 110 € vendu) ;
  « Vendu ! » à 25 € → `vendue` + `prix_vente_reel` + `vendu_le` + total 135 € ;
  badge « prix à revoir ? » sur produit vieilli 15 j ; « Retirer » → `abandonnee`.
- **T06 Publication** : blocs dans l'ordre LBC ; `photos.zip` = `['1.jpg','2.jpg']` ;
  non-`prete` → redirection 303 ; « Marquer publiée » (+URL) → `publiee` + événement +
  **chaînage vers la fiche suivante** ; file `/publier`.
- **T07 Userscript** : `GET /api/publication/next` (fiche + `restantes`, 204 si vide),
  `POST .../publiee` (409 si non prête), **CORS accepté pour `leboncoin.fr` / refusé
  pour toute autre origine**, preflight OPTIONS ; `brocantor.user.js` passe `node --check`.
- **T08 Déploiement** : `bash -n install.sh` OK ; plist généré validé par `plutil -lint`
  (4 substitutions de chemin) ; `GET /api/sante` → `{ok:true, produits:6, worker:"actif"}`.
- **Intégration finale** : 19/19 vérifications vertes, cycle complet
  `dépôt → IA → valider → publier → vendu` rejoué sans erreur ; toutes les pages
  coexistent (aucune collision de routes).

## Décisions & écarts par rapport à la spec (à connaître)

1. **Python 3.14 (Homebrew)** pour le venv : le python système est 3.9.6, or CLAUDE.md
   exige 3.12+. `install.sh` cherche automatiquement un 3.12+ (surchargeable via
   `PYTHON_BIN`).
2. **Mode factice `BROCANTOR_FAKE_AI`** ajouté dans `analyse.py` : sans clé API,
   permet de tester tout le pipeline sans réseau. Le **vrai appel Claude
   (`_appel_reel`) n'a donc PAS pu être exécuté cette nuit** (aucune clé). Le code
   (tool-use, schéma JSON forcé, retry) est écrit mais non éprouvé en conditions réelles.
3. **`analyse.py` — Starlette** : la nouvelle signature `TemplateResponse(request, name, ctx)`
   est utilisée (l'ancienne est dépréciée et cassait le rendu). Centralisé dans
   `app/templating.py`.
4. **T06 — router publication sans préfixe** : pour servir à la fois `/publier` (file)
   et `/produits/{id}/publier` (pack) sans toucher `main.py`. Les URL externes sont
   identiques à ce que prévoyait T01.
5. **T07 — CORS au niveau des routes** (helper `_cors` + handler OPTIONS) plutôt qu'un
   middleware global : reste dans le périmètre `api.py` et n'ouvre le CORS que pour
   `https://www.leboncoin.fr` sur ces 2 routes.
6. **Worker — reprise après crash** (`en_traitement`→`depose`) faite en SQL direct avec
   journalisation manuelle, car ce n'est pas une transition métier de la machine à états
   (donc pas via `changer_etat`, à dessein).
7. **CSS** : styles propres à Dépôt (T02) et Dashboard (T05) mis en `<style>` inline dans
   leurs templates pour ne pas toucher `style.css` (territoire T01). `produits.css` créé
   (autorisé par T04), `publication` idem via `<style>`.
8. **Lien dashboard → `/publier`** non ajouté (dashboard = territoire T05 déjà commité au
   moment de T06). L'accès direct `/publier` fonctionne ; à câbler si souhaité.

## À vérifier / décider par Wassim

- [ ] **Clé API + qualité réelle des fiches** : renseigner `ANTHROPIC_API_KEY`, déposer
      2-3 vrais objets, juger titre/description/prix/catégorie. Ajuster le prompt dans
      `app/analyse.py` (constante `SYSTEME`) si besoin.
- [ ] **`CLAUDE_MODEL`** : défaut mis à `claude-sonnet-4-5` (`.env.example` + `analyse.py`).
      Confirmer l'ID exact du modèle vision voulu.
- [ ] **Catégories Leboncoin** : liste dans `app/categories_lbc.py` = première approximation
      (`# TODO utilisateur`). À affiner depuis le vrai formulaire de dépôt LBC.
- [ ] **Dépôt mobile réel** (T02) : compression < 800 Ko, install PWA plein écran,
      < 45 s/objet, reprise après coupure réseau — testable seulement sur téléphone.
- [ ] **Userscript (T07)** : les **sélecteurs CSS du formulaire LBC sont des placeholders**
      (`CONFIG.selectors` en tête de `brocantor.user.js`). À ajuster sur la vraie page de
      dépôt (procédure dans `userscript/README.md`). Le fallback copier-coller (T06) marche
      quoi qu'il arrive.
- [ ] **Déploiement (T08)** : lancer `./deploy/install.sh` **soi-même** (non exécuté cette
      nuit car il charge un vrai LaunchAgent). Puis les étapes Tailscale/HTTPS/PWA du
      `deploy/README.md` (reboot, test 4G).
- [ ] **Tactile ≥ 48 px / zoom** sur les écrans (fiches, dashboard) : contrôle visuel mobile.

## État du dépôt git

`git init` fait ; 8 commits, un par ticket, plus ce rapport. `data/` et `.venv/`
sont gitignorés. Branche `main`.
