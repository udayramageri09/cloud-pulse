#!/usr/bin/env bash
# One-command CloudPulse demo against the Docker failure lab.
# Usage: scripts/demo.sh            (pauses between steps)
#        scripts/demo.sh --no-pause (runs straight through)
# Port: 18080 by default; override with CLOUDPULSE_LAB_PORT=9090 scripts/demo.sh
set -u
cd "$(dirname "$0")/.."

PAUSE=1; [ "${1:-}" = "--no-pause" ] && PAUSE=0
export CLOUDPULSE_LAB_PORT="${CLOUDPULSE_LAB_PORT:-18080}"
PORT="$CLOUDPULSE_LAB_PORT"
URL="http://127.0.0.1:$PORT"
step()  { [ "$PAUSE" = 1 ] && clear; echo "=== CloudPulse demo - Step $1: $2 ==="; }
run()   { echo; echo "\$ $*"; echo; "$@"; }
code()  { echo; echo "Exit code: $1   (0 OK, 1 warning, 2 critical, 3 unknown)"; }
pause() { if [ "$PAUSE" = 1 ]; then echo; read -rp "[Enter] next step " _; fi; }

command -v docker >/dev/null 2>&1 || { echo "Docker is required (Docker Desktop or Docker Engine)."; exit 1; }
docker info >/dev/null 2>&1 || { echo "Docker is installed but not running. Start it and try again."; exit 1; }
if ! command -v cloudpulse >/dev/null 2>&1; then
  if [ ! -x .venv/bin/cloudpulse ]; then
    echo "Installing CloudPulse into .venv (first run only)..."
    python3 -m venv .venv && .venv/bin/pip install -q -e . \
      || { echo "Install failed. Needs Python 3.10+ with venv (Ubuntu: sudo apt-get install -y python3-venv)."; exit 1; }
  fi
  export PATH="$PWD/.venv/bin:$PATH"
fi

step 1 "Start the lab: Nginx in front of a small app, in Docker (port $PORT)"
run ./simulation/lab.sh up
./simulation/lab.sh healthy >/dev/null 2>&1; sleep 4
run docker compose ps
pause

step 2 "Healthy service"
run cloudpulse --tcp "127.0.0.1:$PORT" --url "$URL/health"; code $?
pause

step 3 "The app fails (HTTP 500)"
run cloudpulse --url "$URL/fail"; code $?
pause

step 4 "The app is running but not ready (HTTP 503)"
./simulation/lab.sh unhealthy >/dev/null 2>&1; sleep 3
run cloudpulse --url "$URL/health"; code $?
pause

step 5 "The app is down, the proxy is still up (TCP OK, HTTP 502/504)"
./simulation/lab.sh stop-app >/dev/null 2>&1
run cloudpulse --tcp "127.0.0.1:$PORT" --url "$URL/health"; code $?
pause

step 6 "Recovery"
./simulation/lab.sh start-app >/dev/null 2>&1; ./simulation/lab.sh healthy >/dev/null 2>&1; sleep 4
run cloudpulse --tcp "127.0.0.1:$PORT" --url "$URL/health"; code $?
pause

step 7 "The same report as JSON, for other tools to read"
cloudpulse --url "$URL/health" --format json | head -n 30
echo; echo "=== End of CloudPulse demo. Stop the lab with: ./simulation/lab.sh down ==="
