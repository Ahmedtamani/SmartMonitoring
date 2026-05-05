#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

export DOCKER_HOST="${DOCKER_HOST:-unix:///Users/$USER/.rd/docker.sock}"

if [[ -f "$ROOT_DIR/.env" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ROOT_DIR/.env"
  set +a
fi

log() {
  echo "[$(date +%H:%M:%S)] $*"
}

log "[1/4] Docker services..."
cd "$ROOT_DIR"
docker compose up -d

tail -n 2 docker-compose.yml >/dev/null || true

log "[2/4] Python deps (bridge) via venv..."
cd "$ROOT_DIR/bridge"
VENV_DIR="$ROOT_DIR/.venv"
if [[ ! -d "$VENV_DIR" ]]; then
  python3 -m venv "$VENV_DIR"
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
python -m pip install -r requirements.txt >/dev/null

log "[3/4] Start MQTT->MySQL bridge (main.py)..."
pkill -f "bridge/main.py" >/dev/null 2>&1 || true
pkill -f "bridge/api_mqtt.py" >/dev/null 2>&1 || true
nohup env PYTHONUNBUFFERED=1 "$VENV_DIR/bin/python" -u main.py > "$ROOT_DIR/bridge/main.out" 2>&1 &

log "[4/4] Start API MQTT (api_mqtt.py) + Web server..."
nohup env PYTHONUNBUFFERED=1 "$VENV_DIR/bin/python" -u api_mqtt.py > "$ROOT_DIR/bridge/api_mqtt.out" 2>&1 &
pkill -f "web_interface/server.js" >/dev/null 2>&1 || true
nohup node "$ROOT_DIR/web_interface/server.js" > "$ROOT_DIR/web_interface/web.out" 2>&1 &

log "✅ Tout est lancé."
log "- Web: http://localhost:3000"
log "- Logs: bridge/main.out | bridge/api_mqtt.out | web_interface/web.out"
