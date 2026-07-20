# T08 — Déploiement Mac mini (launchd, Tailscale HTTPS, sauvegarde)

> Prompt pour agent IA dev. Lire `CLAUDE.md` et `docs/cahier-des-charges.md` (§4, §8) avant de coder. Prérequis : T01 fait (déployable dès le socle, à refaire tourner en fin de projet).

## Contexte

Rendre Brocantor toujours disponible : démarre au boot du Mac mini, accessible en HTTPS depuis le téléphone n'importe où via Tailscale, données sauvegardées. Ce ticket produit surtout des scripts et de la doc — une partie (installation Tailscale, login) sera exécutée par l'utilisateur en suivant ta doc.

## Périmètre de fichiers (strict)

`deploy/` uniquement : `deploy/com.brocantor.app.plist`, `deploy/install.sh`, `deploy/README.md`.

## Spécifications

1. **launchd** (`com.brocantor.app.plist`) — LaunchAgent utilisateur : lance `uvicorn app.main:app --host 0.0.0.0 --port 8377` (via le python du venv, chemin en variable), `RunAtLoad` + `KeepAlive` (redémarre si crash), logs stdout/stderr dans `deploy/logs/`. Chemins paramétrés en tête de fichier.
2. **Script d'installation** (`install.sh`) — idempotent, safe à relancer : crée le venv si absent, `pip install -r requirements.txt`, copie `.env.example → .env` si absent (et le dit), substitue les chemins dans le plist, `launchctl bootstrap`/`bootout` proprement, vérifie que l'app répond en local (curl santé), affiche un récap final avec l'URL Tailscale à utiliser.
3. **Doc Tailscale** (`README.md`) — pas de script (opérations interactives), une checklist claire : installer Tailscale sur Mac mini + iPhone + desktop (liens), se connecter au même tailnet, activer MagicDNS + HTTPS dans la console admin, générer le certificat (`tailscale cert <machine>.<tailnet>.ts.net`), et les deux options pour servir en HTTPS — recommandée : `tailscale serve https / http://localhost:8377` (zéro config dans l'app) ; alternative : passer cert/clé à uvicorn. Finir par le test : ouvrir l'URL depuis le téléphone en 4G, installer la PWA.
4. **Sauvegarde** — section du README : vérifier que le dossier projet est couvert par Time Machine ; sinon, ligne `rsync` quotidienne de `data/` vers un disque externe (exemple de LaunchAgent fourni en commentaire). Rappel : `data/app.db` + `data/photos/` = tout l'état du projet.
5. **Endpoint santé** — ajouter `GET /api/sante` (section `# T08` dans `routers/api.py` — seule sortie de périmètre autorisée) : `{ok: true, produits: N, worker: "actif|inactif"}`. Utilisé par `install.sh` et pratique pour vérifier depuis le téléphone.

## Critères d'acceptation

- `./deploy/install.sh` sur un clone frais : venv créé, service chargé, `curl localhost:8377/api/sante` OK. Relançable sans casse.
- Reboot du Mac (ou `launchctl kickstart`) → l'app revient toute seule, logs écrits.
- En suivant le README, l'URL `https://<machine>.<tailnet>.ts.net` répond depuis le téléphone en 4G et la PWA s'installe (vérifié par l'utilisateur).
- Le README tient sur une page et est exécutable par quelqu'un qui découvre Tailscale.

## Contraintes

- macOS uniquement (zsh/bash), pas de Docker, pas de brew dans le script (documenter les prérequis à la place). Ne jamais écouter sur une interface publique autre que via Tailscale — pas de règle de pare-feu ouvrante, pas de port forwarding.
