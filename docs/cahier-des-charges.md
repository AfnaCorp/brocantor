# Cahier des charges — « Vide-Grenier Pipeline »

**Application locale de mise en vente assistée sur Leboncoin**
Version 1.1 — 20 juillet 2026 — Usage personnel unique (wassim)

---

## 1. Vision et contexte

Transformer la corvée « photographier → décrire → estimer → publier → suivre » en un pipeline où l'humain n'intervient que là où il a de la valeur : prendre la photo, valider la fiche, cliquer sur publier, négocier.

**Contexte d'usage retenu : gros déstockage ponctuel.** Beaucoup d'objets d'un coup (dizaines), puis usage résiduel. Conséquence structurante : on optimise le **débit en batch** (photographier 30 objets à la chaîne, traiter en lot, publier en série), pas la maintenance long terme. Tout ce qui n'accélère pas le déstockage est hors périmètre v1.

**Décisions actées :**

| Sujet | Décision |
|---|---|
| Publication Leboncoin | **Semi-automatique** : fiche 100 % préparée, injection dans le formulaire via userscript dans ton vrai Chrome, clic « Publier » humain |
| Accès mobile | **Partout**, via tunnel privé (Tailscale) vers le Mac mini |
| Backend | **100 % local Mac mini** : SQLite + système de fichiers, zéro cloud |
| Volume | Déstockage ponctuel → priorité au batch, pas à la robustesse industrielle |

---

## 2. Challenge du concept initial

Ce qui est retiré, simplifié ou déplacé par rapport au schéma de départ, et pourquoi.

### 2.1 La publication full-auto est un piège — abandonnée à raison

Leboncoin n'offre **aucune API publique de dépôt d'annonces aux particuliers**. La « diffusion automatique » officielle est réservée aux professionnels passant par des passerelles d'import partenaires. Le site est protégé par DataDome, un anti-bot agressif qui détecte les navigateurs automatisés (headless, Playwright/Selenium non maquillés), et l'automatisation du dépôt viole les CGU — le risque concret est le **bannissement du compte**, c'est-à-dire la perte de l'actif principal du projet en plein déstockage. Les bots tiers qui existent (lebondeal-bot, scripts growth hacking) vivent dans un jeu du chat et de la souris permanent : maintenance constante pour un projet censé être jetable.

**Verdict :** le semi-auto choisi est le bon compromis. La fiche est prête à 100 % (titre, description, prix, catégorie, photos redimensionnées), et la publication devient un geste de 60–90 secondes par objet au lieu de 10 minutes. Sur 30 objets, on économise ~4h30 sur ~5h — le full-auto n'aurait gagné que les 30 dernières minutes, contre un risque disproportionné.

### 2.2 OpenClaw est surdimensionné pour ce pipeline

Le schéma initial hésite entre OpenClaw et « juste des appels simples à Claude ». Réponse : **appels simples à l'API Claude**. Le pipeline est déterministe (photo → analyse → fiche), sans décision ouverte ni orchestration multi-outils. Un framework d'agent ajoute de la surface de panne, de la latence et de la complexité de déploiement pour zéro gain ici. Un seul appel à l'API Claude en mode vision, avec sortie structurée JSON, fait tout le travail d'analyse. OpenClaw resterait pertinent uniquement pour l'option « publication navigateur supervisée » (v2, §7).

### 2.3 Firebase contredit l'objectif — écartée

L'option 1 du schéma (Firebase Firestore + Storage, requêté depuis le Mac mini) fait transiter les photos par Google pour les rapatrier ensuite en local : c'est l'inverse de l'objectif « stocker en local l'info », ça ajoute un compte, un SDK, des règles de sécurité et une facture potentielle. L'option 2 (tout local + tunnel) couvre le même besoin avec moins de pièces. **Tailscale plutôt qu'un tunnel public** (Cloudflare Tunnel/ngrok) : le service n'est joignable que depuis tes propres appareils authentifiés, donc aucune surface exposée sur Internet, aucun login à coder — ce qui autorise une app volontairement brouillonne côté sécurité applicative.

### 2.4 L'estimation de prix par IA seule n'est pas fiable — humain dans la boucle

Un LLM donne un **ordre de grandeur** correct (il reconnaît l'objet, sa gamme, son état apparent) mais pas un prix de marché : il ne voit pas les annonces comparables du moment ni la cote locale. Deux garde-fous : (1) l'IA rend une **fourchette + niveau de confiance + hypothèses** (« si c'est bien le modèle X de 2019… »), jamais un prix sec ; (2) la fiche affiche un lien de recherche Leboncoin pré-rempli sur l'objet pour vérifier les comparables en 10 secondes avant de valider. Le prix final est toujours édité/confirmé par toi. Un scraping automatique des comparables est possible mais repose sur du scraping DataDome — reporté en option v2, pas dans le chemin critique.

### 2.5 Le « dashboard client » (qui t'a contacté) — coupé de la v1

Suivre les contacts nécessiterait de lire la messagerie Leboncoin, donc du scraping authentifié derrière DataDome : la partie la plus fragile du projet pour la moins utile — l'app Leboncoin sur ton téléphone notifie déjà les messages. En v1, le suivi se fait par **changement d'état manuel en un tap** (« marquer vendu », « contact en cours »), ce qui donne le dashboard de suivi voulu sans scraping. Le champ `notes` libre par produit absorbe le reste (« RDV samedi », « négocié 25 € »).

### 2.6 Le vocal Whisper — utile mais pas prioritaire

Bonne idée pour donner du contexte (« c'est un vélo Décathlon acheté 300 € en 2021, pneu avant à changer »), mais la **dictée native du clavier iOS/Android dans un champ texte** rend le même service sans héberger Whisper. V1 : champ texte + dictée native. V2 : upload audio + Whisper local si le besoin est réel à l'usage.

### 2.7 Points aveugles du schéma initial (ajoutés au périmètre)

- **Plusieurs photos par produit** : une annonce crédible en a 3 à 5. L'upload « en vrac, 1 item = 1 produit » doit permettre de grouper des photos par produit au moment du dépôt (mode rafale par objet), sinon tri pénible a posteriori.
- **Contraintes photos Leboncoin** : redimensionnement/compression automatique (format accepté, poids raisonnable) pour que la publication ne bute pas dessus.
- **Catégorie Leboncoin** : le dépôt d'annonce exige une catégorie ; l'IA doit la proposer dans la taxonomie réelle de Leboncoin, sinon tu la cherches à chaque fois.
- **File d'attente et reprise** : en batch de 30 objets, l'analyse IA doit être une file asynchrone avec retry — pas un appel bloquant à l'upload.
- **Sauvegarde** : tout est sur un seul Mac mini ; un `rsync`/Time Machine du dossier data suffit, mais il faut le dire.

---

## 3. Périmètre fonctionnel v1

### 3.1 Parcours nominal

1. **Capture (téléphone)** — Ouvrir la PWA → « Nouveau produit » → prendre/sélectionner 1 à 5 photos → optionnel : note texte ou dictée (contexte, prix d'achat, défauts) → « Envoyer ». Enchaîner immédiatement sur l'objet suivant. Objectif : **moins de 45 secondes par objet**.
2. **Traitement (Mac mini, automatique)** — Le produit entre en file. Un worker appelle l'API Claude (vision) avec photos + note et produit : titre, description, catégorie Leboncoin, fourchette de prix, état estimé, hypothèses/incertitudes. Le produit passe à l'état « à valider ».
3. **Validation (téléphone ou desktop)** — La fiche s'affiche telle qu'elle sera publiée (preview par blocs). Édition libre de chaque champ, prix fixé à partir de la fourchette + lien comparables. « Valider » → état « prête ».
4. **Publication (desktop, semi-auto via userscript)** — Sur la page de dépôt Leboncoin, dans ton vrai Chrome, un userscript (Tampermonkey) affiche un bouton « Remplir depuis la fiche » : il récupère la prochaine fiche « prête » auprès de l'app (via Tailscale) et injecte titre, description, prix, catégorie dans le formulaire. Tu glisses les photos, tu cliques « Publier », le script marque la fiche « publiée ». Fallback toujours disponible : la page « Publier » de l'app avec boutons copier par champ (utile aussi pour publier depuis le téléphone, photos déjà dans la pellicule).
5. **Suivi (dashboard)** — Vue d'ensemble par état, tap pour changer d'état, « Marquer vendu » avec prix de vente réel.

### 3.2 Écrans

| Écran | Contenu |
|---|---|
| **Dépôt** (mobile d'abord) | Capture multi-photos par produit, note texte/dictée, envoi, enchaînement rapide |
| **Fiches produits** | Liste/grille des produits avec vignette, titre, prix, état du pipeline ; détail = preview de l'annonce, édition par bloc |
| **Publication** | Fiche « prête » → pack de publication (photos + boutons copier + lien dépôt LBC) ; côté Leboncoin, le userscript injecte les champs en un clic |
| **Dashboard** | Compteurs par état (en traitement / à valider / prête / publiée / vendue / erreur), total estimé vs total vendu, liste filtrable, actions d'état en un tap |

### 3.3 Machine à états produit

```
déposé → en_traitement → à_valider → prête → publiée → vendue
                 ↓                                ↓
              erreur (retry)                   retirée/abandonnée
```

Tout changement d'état est manuel sauf `déposé → en_traitement → à_valider` (automatique). Champ `notes` libre à tous les stades.

### 3.4 Hors périmètre v1 (explicitement)

Publication automatisée sans humain (navigateur piloté par CDP type Playwright/Puppeteer — détectable par DataDome, le userscript n'en relève pas : il tourne dans ton Chrome réel et c'est toi qui cliques « Publier ») ; lecture de la messagerie Leboncoin ; scraping des comparables ; Whisper auto-hébergé ; multi-utilisateurs, authentification applicative (couverte par Tailscale) ; renouvellement automatique des annonces ; multi-plateformes (Vinted, Facebook Marketplace).

---

## 4. Architecture technique

```
[Téléphone]  ──PWA (navigateur)──┐
                                 │  réseau privé Tailscale (HTTPS)
[Desktop]    ──navigateur────────┤
                                 ▼
                        [Mac mini]
                        ├─ App web : FastAPI (Python) + templates HTMX
                        │   (une seule app : UI + API + worker)
                        ├─ Worker asynchrone : file de traitement IA (retry, statuts)
                        ├─ SQLite : produits, états, historique
                        ├─ Dossiers : data/photos/<id_produit>/ (originaux + versions LBC)
                        ├─ API JSON pour le userscript (GET fiche prête / POST marquer publiée)
                        └─ API Claude (seul appel sortant du système)

[Chrome desktop] ── userscript Tampermonkey sur leboncoin.fr
                    └─ appelle l'API de l'app via Tailscale, injecte les champs du formulaire
```

**Choix et justifications :**

- **FastAPI + HTMX, une seule app** : pas de front séparé à builder, pas de synchro d'API ; adapté à un outil personnel jetable. (Alternative équivalente si préférence JS : Next.js seul. Ne pas faire les deux.)
- **SQLite** : une table principale, un seul process, zéro administration. Largement suffisant pour < 1 000 produits.
- **Photos sur le filesystem**, chemin en base — pas de blobs en base. Génération à l'analyse : versions compressées conformes aux contraintes Leboncoin.
- **Tailscale** : installé sur Mac mini + téléphone + desktop. L'app écoute uniquement sur l'IP Tailscale. HTTPS via certificat Tailscale (`tailscale cert`) pour que la PWA (caméra, installation) fonctionne proprement.
- **PWA** : simple page web installée sur l'écran d'accueil, `<input type="file" capture>` pour la caméra. Pas d'app native, pas de store.
- **Worker** : boucle asynchrone dans le même process (asyncio) qui consomme les produits `déposé`, 2–3 analyses en parallèle max, retry ×3 avec backoff, état `erreur` visible au dashboard au-delà.
- **Userscript** : Tampermonkey/Violentmonkey sur le Chrome desktop, actif uniquement sur la page de dépôt `leboncoin.fr`. Il parle à l'app par deux endpoints JSON (`GET /api/publication/next` → fiche prête suivante ; `POST /api/publication/{id}/publiee` avec l'URL de l'annonce). Prévoir les en-têtes CORS pour l'origine leboncoin.fr côté FastAPI — l'accès reste privé puisque l'app n'est joignable que via Tailscale. Aucun clic n'est automatisé : injection de texte dans les champs uniquement, photos et bouton « Publier » restent manuels.
- **Lancement** : service `launchd` sur le Mac mini (démarre au boot, redémarre si crash).
- **Sauvegarde** : le dossier projet (`data/` + `app.db`) inclus dans Time Machine ou rsync quotidien vers un disque externe.

### 4.1 Modèle de données (table `produits`)

`id, créé_le, état, photos[] (chemins), note_utilisateur, titre, description, catégorie_lbc, prix_min_estimé, prix_max_estimé, prix_choisi, confiance_estimation, hypothèses_ia, url_annonce, prix_vente_réel, vendu_le, notes, erreur_dernière`

Plus une table `événements` (id_produit, horodatage, ancien_état, nouvel_état) pour l'historique du dashboard.

### 4.2 Contrat de l'appel IA

Un appel API Claude par produit, images + note utilisateur, avec sortie structurée (JSON forcé) :

```json
{
  "titre": "≤ 50 caractères, style annonce LBC",
  "description": "3–6 phrases honnêtes : état, défauts visibles, dimensions si estimables",
  "categorie_lbc": "libellé exact de la taxonomie Leboncoin",
  "prix_min": 0, "prix_max": 0,
  "confiance": "haute|moyenne|basse",
  "hypotheses": ["modèle supposé…", "état supposé…"],
  "questions": ["info manquante qui améliorerait la fiche"]
}
```

Le prompt embarque la liste des catégories Leboncoin (fichier statique dans le repo) et des consignes de ton (honnête sur les défauts — ça vend mieux et évite les litiges).

---

## 5. Lots de développement

Chaque lot est livrable et utile seul ; on peut s'arrêter à n'importe quel lot avec un outil fonctionnel.

| Lot | Contenu | Critère de réception | Effort indicatif |
|---|---|---|---|
| **0 — Socle** | Repo, FastAPI hello, SQLite + schéma, Tailscale + HTTPS, launchd | La page d'accueil s'ouvre depuis le téléphone en 4G | ½ journée |
| **1 — Dépôt & stockage** | PWA de capture multi-photos + note, écriture disque + base, liste brute des produits | 10 objets photographiés depuis le canapé, visibles avec photos dans la liste | 1 journée |
| **2 — Analyse IA** | Worker + appel Claude structuré, redimensionnement photos, états auto, gestion erreurs | Les 10 objets ont une fiche complète sans intervention ; un produit en erreur est visible et relançable | 1–1,5 journée |
| **3 — Validation & dashboard** | Preview d'annonce, édition par champ, choix du prix (+ lien comparables), dashboard états/compteurs, actions d'état | Cycle complet déposé→vendue jouable au doigt sur mobile | 1–1,5 journée |
| **4 — Pack de publication** | Page « publier » : photos prêtes, boutons copier, lien dépôt LBC, marquage publiée + URL | Publier une vraie annonce en < 2 min chrono à partir d'une fiche prête | ½–1 journée |
| **4 bis — Userscript remplisseur** | Endpoints JSON `next`/`publiee` + CORS, script Tampermonkey : bouton « Remplir depuis la fiche », injection titre/description/prix/catégorie, marquage publiée | Publier une annonce en < 1 min ; si Leboncoin change son formulaire, le fallback copier-coller du lot 4 fonctionne toujours | ½–1 journée |

**Total v1 : ~4,5 à 6 jours de développement.** Ordre de test grandeur nature : dès la fin du lot 2, lancer un vrai batch de 10 objets pour valider la qualité des fiches avant de polir le reste.

---

## 6. Risques et parades

| Risque | Impact | Parade |
|---|---|---|
| Qualité des fiches IA décevante (mauvaise catégorie, prix fantaisistes) | Perte de temps en corrections | Test réel dès le lot 2 ; itérer sur le prompt ; champ note utilisateur pour guider l'IA |
| Upload mobile peu fiable (photos lourdes, 4G) | Friction à la capture | Compression côté client avant envoi ; upload photo par photo avec reprise |
| Tentation du full-auto en cours de route | Bannissement du compte LBC | Décision actée ici : le userscript injecte du texte mais n'automatise jamais un clic ; pas de pilotage CDP |
| Leboncoin change son formulaire de dépôt | Userscript cassé (sélecteurs obsolètes) | Fallback copier-coller du lot 4 toujours fonctionnel ; sélecteurs regroupés en tête de script pour correction en 10 min |
| Coût API Claude | Marginal | ~30 produits × 1 appel vision ≈ quelques euros au total |
| Panne/perte du Mac mini | Perte des données | Sauvegarde Time Machine/rsync du dossier data + base |
| Estimation de prix trop optimiste → invendus | Annonces qui stagnent | Fourchette + comparables + toi qui tranches ; baisser le prix est une action à un tap (v2 : rappel après X jours) |

---

## 7. Pistes v2 (si l'usage le justifie)

- **Comparables automatiques** : recherche des annonces similaires pour ancrer le prix (scraping fragile — à n'aborder que si le besoin est fort).
- **Whisper local** pour les notes vocales longues.
- **Relances** : notification si une annonce publiée n'est pas vendue après X jours → suggérer une baisse de prix.
- **Multi-plateformes** : générer des variantes de fiche pour Vinted / Facebook Marketplace (la fiche produit est déjà agnostique, seul le pack de publication change).

---

## 8. Prérequis avant le premier commit

1. Compte Tailscale (gratuit) + app installée sur Mac mini, téléphone, desktop.
2. Clé API Claude (console Anthropic) avec un petit budget.
3. Python 3.12+ sur le Mac mini.
4. Récupérer/figer la liste des catégories Leboncoin (copie manuelle depuis le formulaire de dépôt — 10 min).
5. Un carton de 10 objets tests pour le premier batch réel.
