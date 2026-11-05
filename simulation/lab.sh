#!/usr/bin/env bash
# Single-command controls for the CloudPulse failure-simulation lab.
# Usage: ./simulation/lab.sh <up|down|reset|healthy|unhealthy|stop-app|start-app>
set -euo pipefail
cd "$(dirname "$0")/.."

case "${1:-}" in
  up)
    docker compose up --build -d
    ;;
  down)
    docker compose down --remove-orphans
    ;;
  reset)
    docker compose down --remove-orphans
    docker compose up --build -d
    ;;
  healthy)
    APP_MODE=healthy docker compose up -d --force-recreate app
    ;;
  unhealthy)
    APP_MODE=unhealthy docker compose up -d --force-recreate app
    ;;
  stop-app)
    docker compose stop app
    ;;
  start-app)
    docker compose start app
    ;;
  *)
    echo "Usage: $0 <up|down|reset|healthy|unhealthy|stop-app|start-app>" >&2
    exit 2
    ;;
esac
