#!/usr/bin/env bash
set -euo pipefail

# Installe les services systemd pour lancer automatiquement:
# - bridge/main.py
# - bridge/api_mqtt.py
#
# Usage:
#   ./scripts/install_raspberry_services.sh
#
# Variables optionnelles:
#   PROJECT_DIR=/home/pi/SmartMonitoring
#   SERVICE_USER=pi
#   PYTHON_BIN=/usr/bin/python3
#   INSTALL_DEPS=true

PROJECT_DIR="${PROJECT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
SERVICE_USER="${SERVICE_USER:-${SUDO_USER:-$USER}}"
PYTHON_BIN="${PYTHON_BIN:-/usr/bin/python3}"
INSTALL_DEPS="${INSTALL_DEPS:-true}"

MAIN_UNIT="/etc/systemd/system/smartmonitoring-main.service"
API_UNIT="/etc/systemd/system/smartmonitoring-api.service"
ENV_FILE="/etc/smartmonitoring.env"

if [[ "$EUID" -ne 0 ]]; then
  SUDO="sudo"
else
  SUDO=""
fi

BRIDGE_DIR="$PROJECT_DIR/bridge"
REQ_FILE="$BRIDGE_DIR/requirements.txt"
MAIN_FILE="$BRIDGE_DIR/main.py"
API_FILE="$BRIDGE_DIR/api_mqtt.py"

if [[ ! -f "$MAIN_FILE" || ! -f "$API_FILE" || ! -f "$REQ_FILE" ]]; then
  echo "❌ Projet incomplet dans: $PROJECT_DIR"
  echo "Attendu: bridge/main.py, bridge/api_mqtt.py, bridge/requirements.txt"
  exit 1
fi

echo "[1/5] Préparation dépendances..."
if [[ "$INSTALL_DEPS" == "true" ]]; then
  $SUDO apt-get update -y
  $SUDO apt-get install -y python3 python3-pip
  $SUDO "$PYTHON_BIN" -m pip install -r "$REQ_FILE"
fi

echo "[2/5] Création fichier d'environnement (si absent)..."
if [[ ! -f "$ENV_FILE" ]]; then
  $SUDO cp "$PROJECT_DIR/scripts/smartmonitoring.env.example" "$ENV_FILE"
  $SUDO chown root:root "$ENV_FILE"
  $SUDO chmod 600 "$ENV_FILE"
  echo "ℹ️ Fichier créé: $ENV_FILE"
  echo "   Pense à renseigner MQTT_USER/MQTT_PASS et variables DB."
fi

echo "[3/5] Installation service smartmonitoring-main..."
$SUDO tee "$MAIN_UNIT" >/dev/null <<EOF
[Unit]
Description=SmartMonitoring MQTT -> MySQL bridge
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$BRIDGE_DIR
EnvironmentFile=-$ENV_FILE
ExecStart=$PYTHON_BIN $MAIN_FILE
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

echo "[4/5] Installation service smartmonitoring-api..."
$SUDO tee "$API_UNIT" >/dev/null <<EOF
[Unit]
Description=SmartMonitoring WEB/REQUETE -> WEB/REPONSE API
After=network-online.target smartmonitoring-main.service
Wants=network-online.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$BRIDGE_DIR
EnvironmentFile=-$ENV_FILE
ExecStart=$PYTHON_BIN $API_FILE
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

echo "[5/5] Activation et démarrage..."
$SUDO systemctl daemon-reload
$SUDO systemctl enable smartmonitoring-main.service smartmonitoring-api.service
$SUDO systemctl restart smartmonitoring-main.service smartmonitoring-api.service

echo
echo "✅ Services installés et démarrés."
echo "Vérification:"
echo "  sudo systemctl status smartmonitoring-main.service --no-pager"
echo "  sudo systemctl status smartmonitoring-api.service --no-pager"
echo "  sudo journalctl -u smartmonitoring-main.service -f"
