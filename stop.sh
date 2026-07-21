#!/usr/bin/env bash
# Arrête proprement l'instance Brocantor locale.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="8377"
[ -f "$SCRIPT_DIR/.env" ] && PORT="$(grep -E '^PORT=' "$SCRIPT_DIR/.env" | cut -d= -f2)"
PORT="${PORT:-8377}"

# -sTCP:LISTEN uniquement — ne jamais toucher aux clients (navigateur) connectés au port.
PID=$(lsof -ti "tcp:$PORT" -sTCP:LISTEN 2>/dev/null || true)
if [ -z "$PID" ]; then
  echo "Rien ne tourne sur le port $PORT."
  exit 0
fi
echo "$PID" | xargs -r kill 2>/dev/null || echo "$PID" | xargs -r kill -9 2>/dev/null || true
echo "✓ Brocantor arrêté (pid $PID)."
