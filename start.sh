#!/usr/bin/env bash
# Lance Brocantor en un clic : vérifie l'environnement, démarre le serveur,
# attend qu'il réponde, ouvre le dashboard dans le navigateur.
# Relançable sans risque (idempotent) — ne touche jamais aux données.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_PY="$SCRIPT_DIR/.venv/bin/python"
VENV_UVICORN="$SCRIPT_DIR/.venv/bin/uvicorn"
LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/app.log"
mkdir -p "$LOG_DIR"

c_ok=$'\033[0;32m'; c_warn=$'\033[0;33m'; c_err=$'\033[0;31m'; c_dim=$'\033[2m'; c_reset=$'\033[0m'

if [ ! -x "$VENV_UVICORN" ]; then
  echo "${c_err}✗ Environnement virtuel introuvable (.venv/).${c_reset}"
  echo "  Crée-le d'abord : python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  exit 1
fi

if [ ! -f "$SCRIPT_DIR/.env" ]; then
  cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
  echo "${c_warn}⚠ .env créé depuis .env.example — pense à y coller ta clé ANTHROPIC_API_KEY.${c_reset}"
fi

# Charge .env (juste pour lire PORT / la présence de la clé, sans écraser un export existant du shell).
set -a
# shellcheck disable=SC1091
source "$SCRIPT_DIR/.env"
set +a

PORT="${PORT:-8377}"

if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
  MODE="réel (clé API détectée)"
else
  export BROCANTOR_FAKE_AI=1
  MODE="${c_warn}factice — BROCANTOR_FAKE_AI=1 (aucune clé ANTHROPIC_API_KEY dans .env)${c_reset}"
fi

# Idempotent : coupe une instance déjà lancée sur ce port.
# -sTCP:LISTEN uniquement — sinon lsof remonte aussi les navigateurs
# connectés en client au dashboard, qu'il ne faut surtout pas tuer.
EXISTING_PID=$(lsof -ti "tcp:$PORT" -sTCP:LISTEN 2>/dev/null || true)
if [ -n "$EXISTING_PID" ]; then
  echo "${c_dim}… instance déjà active sur le port $PORT, redémarrage.${c_reset}"
  echo "$EXISTING_PID" | xargs -r kill -9 2>/dev/null || true
  sleep 0.5
fi

echo "Démarrage de Brocantor sur le port $PORT (mode IA : $MODE)…"
nohup "$VENV_UVICORN" app.main:app --host 127.0.0.1 --port "$PORT" >"$LOG_FILE" 2>&1 &
NEW_PID=$!

ok=0
for _ in $(seq 1 30); do
  if curl -s -o /dev/null "http://127.0.0.1:$PORT/api/sante"; then ok=1; break; fi
  sleep 0.3
done

if [ "$ok" != "1" ]; then
  echo "${c_err}✗ L'app n'a pas répondu après 9s. Dernières lignes du log :${c_reset}"
  tail -20 "$LOG_FILE"
  exit 1
fi

SANTE=$(curl -s "http://127.0.0.1:$PORT/api/sante")
echo "${c_ok}✓ Brocantor tourne (pid $NEW_PID) — $SANTE${c_reset}"
echo "  Dashboard : http://127.0.0.1:$PORT/dashboard"
echo "  Log       : $LOG_FILE"
echo "  Arrêt     : ./stop.sh"

open "http://127.0.0.1:$PORT/dashboard" 2>/dev/null || true
