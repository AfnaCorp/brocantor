# Déploiement Brocantor (Mac mini)

App toujours dispo : démarre au boot, accessible en HTTPS depuis le téléphone
partout via Tailscale, données sauvegardées. Jamais exposée sur Internet public.

## Prérequis (à installer une fois, manuellement)

- **Python 3.12+** (`python3 --version`). Sinon : `brew install python@3.14`.
- **Tailscale** sur Mac mini + iPhone + desktop : https://tailscale.com/download
- Optionnel : une **clé API Anthropic** (sinon l'app tourne, sans analyse IA).

## 1. Installer l'app (launchd)

```bash
cd /chemin/vers/brocantor
./deploy/install.sh
```

Le script (idempotent, relançable) : crée le venv, installe les dépendances,
crée `.env` si absent, installe le LaunchAgent `com.brocantor.app`
(`RunAtLoad` + `KeepAlive` : démarre au boot, redémarre si crash), et vérifie
`http://localhost:8377/api/sante`.

Renseigne ensuite ta clé dans `.env` (`ANTHROPIC_API_KEY=…`) puis recharge :

```bash
launchctl kickstart -k gui/$(id -u)/com.brocantor.app
```

Reboot du Mac → l'app revient seule. Logs dans `deploy/logs/`.

## 2. Accès mobile HTTPS via Tailscale

Checklist (opérations interactives, pas de script) :

1. **Installer + connecter** Tailscale sur les 3 appareils, même tailnet
   (même compte).
2. Console admin Tailscale → **activer MagicDNS** et **HTTPS Certificates**
   (section DNS).
3. Sur le Mac mini, générer le certificat :
   ```bash
   tailscale cert "$(tailscale status --json | python3 -c 'import sys,json;print(json.load(sys.stdin)["Self"]["DNSName"].rstrip("."))')"
   ```
4. **Servir en HTTPS — option recommandée** (zéro config dans l'app) :
   ```bash
   tailscale serve --bg https / http://localhost:8377
   ```
   L'app est alors sur `https://<machine>.<tailnet>.ts.net`.
   *Alternative* : passer le cert à uvicorn
   (`--ssl-certfile <machine>.crt --ssl-keyfile <machine>.key`) au lieu de
   `tailscale serve` — ne pas faire les deux.
5. **Test** : depuis le téléphone **en 4G** (Wi-Fi coupé), ouvre
   `https://<machine>.<tailnet>.ts.net` → l'écran Dépôt s'affiche.
   Safari/Chrome → « Ajouter à l'écran d'accueil » installe la PWA.

> L'app écoute sur `0.0.0.0:8377` mais n'est joignable que par les appareils de
> ton tailnet (Tailscale gère l'accès). **N'ouvre aucun port sur la box / le
> pare-feu**, ne fais pas de port forwarding.

## 3. Sauvegarde

Tout l'état du projet = `data/app.db` + `data/photos/`.

- **Time Machine** : vérifie que le dossier projet n'est pas exclu
  (Réglages → Time Machine → Options).
- **Ou rsync quotidien** vers un disque externe :
  ```bash
  rsync -a --delete "/chemin/vers/brocantor/data/" "/Volumes/Backup/brocantor-data/"
  ```
  Exemple de LaunchAgent quotidien (à adapter, `~/Library/LaunchAgents/com.brocantor.backup.plist`) :
  ```xml
  <!-- ProgramArguments : rsync -a --delete <data> <backup> ;
       StartCalendarInterval : Hour 3 Minute 0 -->
  ```

## Dépannage

- `launchctl print gui/$(id -u)/com.brocantor.app` → état du service.
- Logs : `deploy/logs/brocantor.err.log`.
- Santé : `curl http://localhost:8377/api/sante`
  → `{"ok":true,"produits":N,"worker":"actif|inactif"}`.
