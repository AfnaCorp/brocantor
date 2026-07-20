#!/usr/bin/env bash
# Installation / mise à jour de Brocantor sur le Mac mini (macOS, launchd).
# Idempotent : relançable sans casse. Ne touche à rien hors du projet et du
# LaunchAgent utilisateur com.brocantor.app.
set -euo pipefail

# --- Chemins & config --------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
VENV_PYTHON="$VENV_DIR/bin/python"
LABEL="com.brocantor.app"
PLIST_SRC="$SCRIPT_DIR/$LABEL.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/$LABEL.plist"
PORT="8377"
LOGS_DIR="$SCRIPT_DIR/logs"

# Python pour créer le venv : surchargé par $PYTHON_BIN, sinon on cherche 3.12+.
PYTHON_BIN="${PYTHON_BIN:-}"
if [ -z "$PYTHON_BIN" ]; then
  for cand in python3.14 python3.13 python3.12 /opt/homebrew/bin/python3.14 python3; do
    if command -v "$cand" >/dev/null 2>&1; then PYTHON_BIN="$(command -v "$cand")"; break; fi
  done
fi

echo "▶ Projet   : $PROJECT_DIR"
echo "▶ Python   : ${PYTHON_BIN:-INTROUVABLE}"

if [ -z "$PYTHON_BIN" ]; then
  echo "✗ Aucun Python trouvé. Installe Python 3.12+ (voir deploy/README.md)." >&2
  exit 1
fi
# Vérifie la version (>= 3.12).
"$PYTHON_BIN" - <<'PY' || { echo "✗ Python < 3.12. Installe 3.12+." >&2; exit 1; }
import sys
raise SystemExit(0 if sys.version_info[:2] >= (3, 12) else 1)
PY

# --- Venv + dépendances ------------------------------------------------------
if [ ! -x "$VENV_PYTHON" ]; then
  echo "▶ Création du venv…"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi
echo "▶ Dépendances (pip install)…"
"$VENV_PYTHON" -m pip install --quiet --upgrade pip
"$VENV_PYTHON" -m pip install --quiet -r "$PROJECT_DIR/requirements.txt"

# --- .env --------------------------------------------------------------------
if [ ! -f "$PROJECT_DIR/.env" ]; then
  cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
  echo "▶ .env créé depuis .env.example — PENSE À RENSEIGNER ANTHROPIC_API_KEY."
else
  echo "▶ .env déjà présent (inchangé)."
fi

# --- Logs --------------------------------------------------------------------
mkdir -p "$LOGS_DIR"

# --- Génération du plist (substitution des chemins) --------------------------
echo "▶ Installation du LaunchAgent…"
mkdir -p "$HOME/Library/LaunchAgents"
sed -e "s#__VENV_PYTHON__#$VENV_PYTHON#g" \
    -e "s#__PROJECT_DIR__#$PROJECT_DIR#g" \
    "$PLIST_SRC" > "$PLIST_DEST"

# Validation du plist généré.
if command -v plutil >/dev/null 2>&1; then
  plutil -lint "$PLIST_DEST" >/dev/null
fi

# --- (Re)chargement launchd --------------------------------------------------
DOMAIN="gui/$(id -u)"
launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
launchctl bootstrap "$DOMAIN" "$PLIST_DEST"
launchctl enable "$DOMAIN/$LABEL" 2>/dev/null || true
launchctl kickstart -k "$DOMAIN/$LABEL" 2>/dev/null || true

# --- Vérification santé ------------------------------------------------------
echo -n "▶ Attente de l'app "
OK=""
for _ in $(seq 1 20); do
  if curl -fsS "http://localhost:$PORT/api/sante" >/dev/null 2>&1; then OK="1"; break; fi
  echo -n "."
  sleep 1
done
echo

if [ -n "$OK" ]; then
  echo "✓ App en ligne : $(curl -fsS "http://localhost:$PORT/api/sante")"
else
  echo "✗ L'app ne répond pas sur le port $PORT. Voir $LOGS_DIR/brocantor.err.log" >&2
  exit 1
fi

# --- Récap -------------------------------------------------------------------
cat <<EOF

──────────────────────────────────────────────
✓ Brocantor installé et démarré (LaunchAgent $LABEL).
  Local        : http://localhost:$PORT/
  Logs         : $LOGS_DIR/
  Recharger    : launchctl kickstart -k $DOMAIN/$LABEL
  Désinstaller : launchctl bootout $DOMAIN/$LABEL

  Pour l'accès mobile HTTPS via Tailscale, suis deploy/README.md :
    tailscale serve https / http://localhost:$PORT
  puis ouvre https://<machine>.<tailnet>.ts.net depuis le téléphone.
──────────────────────────────────────────────
EOF
