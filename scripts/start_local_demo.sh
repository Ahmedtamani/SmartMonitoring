#!/usr/bin/env zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "[1/5] Docker services..."
cd "$ROOT_DIR"
docker compose up -d

echo "[2/5] Python deps (bridge)..."
cd "$ROOT_DIR/bridge"
python3 -m pip install -r requirements.txt >/dev/null

echo "[3/5] Start MQTT->MySQL bridge (main.py) in new terminal..."
osascript -e 'tell application "Terminal" to do script "cd '"$ROOT_DIR"'/bridge && python3 main.py"'

echo "[4/5] Start WEB API bridge (api_mqtt.py) in new terminal..."
osascript -e 'tell application "Terminal" to do script "cd '"$ROOT_DIR"'/bridge && python3 api_mqtt.py"'

echo "[5/5] Start local web server on http://localhost:8080 ..."
cd "$ROOT_DIR/web_interface/public"
python3 -m http.server 8080
