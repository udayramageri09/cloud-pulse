#!/usr/bin/env bash
# End-to-end test: drive the failure lab through every scenario and check that
# CloudPulse reports the HTTP status a responder would actually see.
#
#   scripts/e2e_lab.sh                 uses simulation/lab.sh (Docker Compose)
#   LAB=path/to/driver scripts/...     any driver with the same verbs
#                                      (up, down, healthy, unhealthy, stop-app, logs)
set -euo pipefail
cd "$(dirname "$0")/.."

LAB="${LAB:-simulation/lab.sh}"
export CLOUDPULSE_LAB_PORT="${CLOUDPULSE_LAB_PORT:-8080}"
BASE="http://127.0.0.1:${CLOUDPULSE_LAB_PORT}"
TIMEOUT="${E2E_TIMEOUT:-60}"   # seconds to wait for each scenario to settle
failures=0

http_status() {  # print the HTTP status CloudPulse saw for URL ("none" if no response)
    PYTHONPATH=src python3 -m cloudpulse.cli --url "$1" --format json 2>/dev/null |
        python3 -c 'import json, sys
check = next(c for c in json.load(sys.stdin)["checks"] if c["name"] == "http")
print(check.get("http_status", "none"))' || true
}

scenario() {  # scenario "description" URL EXPECTED-REGEX
    local what=$1 url=$2 want=$3 got="" deadline=$((SECONDS + TIMEOUT))
    while ((SECONDS < deadline)); do
        got=$(http_status "$url")
        if [[ "$got" =~ ^(${want})$ ]]; then
            printf 'PASS  %-28s HTTP %s\n' "$what" "$got"
            return 0
        fi
        sleep 1
    done
    printf 'FAIL  %-28s expected %s, last saw %s\n' "$what" "$want" "${got:-nothing}"
    failures=$((failures + 1))
}

trap '"$LAB" down >/dev/null 2>&1 || true' EXIT

"$LAB" up
scenario "healthy service" "$BASE/health" "200"
scenario "application error" "$BASE/fail" "500"

"$LAB" unhealthy
scenario "app reports not ready" "$BASE/health" "503"

"$LAB" stop-app
scenario "upstream down" "$BASE/health" "502|504"

"$LAB" healthy
scenario "recovery" "$BASE/health" "200"

echo
if ((failures)); then
    echo "$failures scenario(s) failed - lab logs follow"
    "$LAB" logs || true
    exit 1
fi
echo "all scenarios passed"
