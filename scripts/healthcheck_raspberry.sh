#!/usr/bin/env bash
set -euo pipefail

# Healthcheck rapide Raspberry pour SmartMonitoring
# Vérifie:
# - Tailscale connecté
# - Services systemd actifs
# - Accès TCP MQTT
# - Accès MySQL

ENV_FILE="${ENV_FILE:-/etc/smartmonitoring.env}"
MQTT_BROKER="${MQTT_BROKER:-mqtt.univ-cotedazur.fr}"
MQTT_PORT="${MQTT_PORT:-443}"
DB_HOST="${DB_HOST:-127.0.0.1}"
DB_USER="${DB_USER:-fablab_user}"
DB_PASS="${DB_PASS:-}"
DB_NAME="${DB_NAME:-fablab_monitoring}"

if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$ENV_FILE"
fi

ok=0
ko=0

pass() {
  echo "✅ $1"
  ok=$((ok+1))
}

fail() {
  echo "❌ $1"
  ko=$((ko+1))
}

check_cmd() {
  command -v "$1" >/dev/null 2>&1
}

echo "=== SmartMonitoring Raspberry Healthcheck ==="

echo
echo "[1] Tailscale"
if check_cmd tailscale; then
  if tailscale status >/dev/null 2>&1; then
    TS_IP="$(tailscale ip -4 2>/dev/null | head -n1 || true)"
    pass "Tailscale actif${TS_IP:+ (IP: $TS_IP)}"
  else
    fail "Tailscale installé mais non connecté"
  fi
else
  fail "Commande tailscale introuvable"
fi

echo
echo "[2] Services systemd"
if check_cmd systemctl; then
  if systemctl is-active --quiet smartmonitoring-main.service; then
    pass "smartmonitoring-main.service actif"
  else
    fail "smartmonitoring-main.service inactif"
  fi

  if systemctl is-active --quiet smartmonitoring-api.service; then
    pass "smartmonitoring-api.service actif"
  else
    fail "smartmonitoring-api.service inactif"
  fi
else
  fail "systemctl indisponible"
fi

echo
echo "[3] Connectivité MQTT (${MQTT_BROKER}:${MQTT_PORT})"
if check_cmd python3; then
  if python3 - <<PY
import socket
import sys
host = ${MQTT_BROKER@Q}
port = int(${MQTT_PORT@Q})
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(4)
try:
    s.connect((host, port))
except Exception:
    sys.exit(1)
finally:
    s.close()
sys.exit(0)
PY
  then
    pass "Port MQTT joignable"
  else
    fail "MQTT non joignable"
  fi
else
  fail "python3 indisponible pour test MQTT"
fi

echo
echo "[4] Connectivité MySQL (${DB_HOST}/${DB_NAME})"
if check_cmd python3; then
  if python3 - <<PY
import os
import sys
try:
    import mysql.connector
except Exception:
    sys.exit(2)

cfg = {
    "host": ${DB_HOST@Q},
    "user": ${DB_USER@Q},
    "password": ${DB_PASS@Q},
    "database": ${DB_NAME@Q},
}
try:
    conn = mysql.connector.connect(**cfg)
    cur = conn.cursor()
    cur.execute("SELECT 1")
    cur.fetchone()
    cur.close()
    conn.close()
except Exception:
    sys.exit(1)
sys.exit(0)
PY
  then
    pass "MySQL joignable"
  else
    fail "MySQL non joignable"
  fi
else
  fail "python3 indisponible pour test MySQL"
fi

echo
echo "=== Résumé ==="
echo "Checks OK : $ok"
echo "Checks KO : $ko"

if [[ "$ko" -gt 0 ]]; then
  exit 1
fi

exit 0
