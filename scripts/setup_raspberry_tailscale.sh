#!/usr/bin/env bash
set -euo pipefail

# Setup Tailscale sur Raspberry Pi (Debian/Raspberry Pi OS)
# Usage minimal:
#   TS_AUTHKEY="tskey-xxxx" ./scripts/setup_raspberry_tailscale.sh
#
# Options facultatives:
#   TS_HOSTNAME="fablab-rpi"
#   TS_ACCEPT_ROUTES="false"
#   TS_ADVERTISE_TAGS="tag:fablab"

TS_AUTHKEY="${TS_AUTHKEY:-}"
TS_HOSTNAME="${TS_HOSTNAME:-fablab-rpi}"
TS_ACCEPT_ROUTES="${TS_ACCEPT_ROUTES:-true}"
TS_ADVERTISE_TAGS="${TS_ADVERTISE_TAGS:-}"

if [[ -z "$TS_AUTHKEY" ]]; then
  echo "❌ Variable TS_AUTHKEY manquante."
  echo "Exemple: TS_AUTHKEY=\"tskey-xxxx\" ./scripts/setup_raspberry_tailscale.sh"
  exit 1
fi

if [[ "$EUID" -ne 0 ]]; then
  SUDO="sudo"
else
  SUDO=""
fi

echo "[1/5] Vérification OS..."
if ! command -v apt-get >/dev/null 2>&1; then
  echo "❌ Ce script cible Debian/Raspberry Pi OS (apt-get requis)."
  exit 1
fi

echo "[2/5] Installation Tailscale..."
$SUDO apt-get update -y
$SUDO apt-get install -y curl ca-certificates
curl -fsSL https://tailscale.com/install.sh | $SUDO sh

echo "[3/5] Activation service tailscaled..."
$SUDO systemctl enable tailscaled
$SUDO systemctl restart tailscaled

echo "[4/5] Connexion au tailnet..."
UP_ARGS=(
  --authkey "$TS_AUTHKEY"
  --hostname "$TS_HOSTNAME"
  --accept-routes="$TS_ACCEPT_ROUTES"
  --reset
)

if [[ -n "$TS_ADVERTISE_TAGS" ]]; then
  UP_ARGS+=(--advertise-tags="$TS_ADVERTISE_TAGS")
fi

$SUDO tailscale up "${UP_ARGS[@]}"

echo "[5/5] État Tailscale"
$SUDO tailscale status || true
$SUDO tailscale ip -4 || true

echo "✅ Raspberry connecté via Tailscale."
