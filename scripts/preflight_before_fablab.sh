#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

ok=0
ko=0
warn=0

pass() {
  echo "✅ $1"
  ok=$((ok + 1))
}

fail() {
  echo "❌ $1"
  ko=$((ko + 1))
}

warning() {
  echo "⚠️  $1"
  warn=$((warn + 1))
}

check_file() {
  local f="$1"
  if [[ -f "$f" ]]; then
    pass "Présent: ${f#$ROOT_DIR/}"
  else
    fail "Manquant: ${f#$ROOT_DIR/}"
  fi
}

echo "=== SmartMonitoring preflight (avant FabLab) ==="
echo "Root: $ROOT_DIR"

# 1) Fichiers indispensables
check_file "$ROOT_DIR/.env"
check_file "$ROOT_DIR/web_interface/public/config.local.js"
check_file "$ROOT_DIR/scripts/setup_raspberry_tailscale.sh"
check_file "$ROOT_DIR/scripts/install_raspberry_services.sh"
check_file "$ROOT_DIR/scripts/healthcheck_raspberry.sh"
check_file "$ROOT_DIR/scripts/smartmonitoring.env.example"
check_file "$ROOT_DIR/docker-compose.yml"
check_file "$ROOT_DIR/bridge/main.py"
check_file "$ROOT_DIR/bridge/api_mqtt.py"
check_file "$ROOT_DIR/bridge/e2e_smoke_test.py"

# 2) Syntaxe scripts bash
if bash -n "$ROOT_DIR/scripts/setup_raspberry_tailscale.sh" \
          "$ROOT_DIR/scripts/install_raspberry_services.sh" \
          "$ROOT_DIR/scripts/healthcheck_raspberry.sh" \
          "$ROOT_DIR/scripts/start_local_demo.sh"; then
  pass "Syntaxe Bash OK"
else
  fail "Erreur syntaxe Bash"
fi

# 3) Syntaxe Python bridge
if python3 -m py_compile "$ROOT_DIR/bridge/main.py" \
                      "$ROOT_DIR/bridge/api_mqtt.py" \
                      "$ROOT_DIR/bridge/e2e_smoke_test.py" \
                      "$ROOT_DIR/bridge/test_sensor_stream.py"; then
  pass "Syntaxe Python OK"
else
  fail "Erreur syntaxe Python"
fi

# 4) Syntaxe Node API web
if command -v node >/dev/null 2>&1; then
  if node --check "$ROOT_DIR/web_interface/server.js"; then
    pass "Syntaxe Node OK"
  else
    fail "Erreur syntaxe Node"
  fi
else
  warning "Node non installé (check server.js ignoré)"
fi

# 5) Validation compose (sans lancer)
if command -v docker >/dev/null 2>&1; then
  if (cd "$ROOT_DIR" && docker compose config >/dev/null); then
    pass "docker-compose.yml valide"
  else
    fail "docker-compose.yml invalide ou docker indisponible"
  fi
else
  warning "Docker non installé (validation compose ignorée)"
fi

# 6) Etat git local
if command -v git >/dev/null 2>&1; then
  if (cd "$ROOT_DIR" && git diff --quiet && git diff --cached --quiet); then
    pass "Arbre git propre (pas de modifs non commit)"
  else
    warning "Modifications git en attente (à commit avant déplacement)"
  fi
else
  warning "Git non disponible"
fi

echo
echo "=== Résumé ==="
echo "OK      : $ok"
echo "Warnings: $warn"
echo "KO      : $ko"

if [[ "$ko" -gt 0 ]]; then
  exit 1
fi

exit 0
