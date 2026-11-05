# Troubleshooting guide: the failure-simulation lab

This walks through each scenario in the Docker Compose lab: what was done to the system,
what CloudPulse observed, what the underlying infrastructure symptom actually was, how an
engineer would investigate it for real, and how it was resolved. All ports are bound to
`127.0.0.1` only; nothing here is exposed beyond your own machine.

Start from a clean baseline before each scenario:

```bash
./simulation/lab.sh reset        # bash/WSL/macOS/Linux
./simulation/lab.ps1 reset       # Windows PowerShell
```

## Scenario 1 — Healthy baseline

**What was done:** `./simulation/lab.sh up` (or `reset`) — Nginx proxies to the app, `APP_MODE=healthy`.

**What CloudPulse detected:**
```bash
cloudpulse --url http://127.0.0.1:8080/health --tcp 127.0.0.1:8080
```
`tcp` and `http` both report `status: ok`, `http_status: 200`, `overall_status: healthy`.

**Actual symptom:** None — this is the control case, confirming the lab itself works before
introducing a fault.

**How an engineer would investigate:** Nothing to investigate; this is the expected-good state
used as a baseline for comparison against the scenarios below.

**Resolution:** N/A.

## Scenario 2 — Application down (Nginx upstream failure)

**What was done:** `./simulation/lab.sh stop-app` stops the `app` container while `proxy` keeps running.

**What CloudPulse detected (actually run, not assumed):**
```bash
cloudpulse --url http://127.0.0.1:8080/health --tcp 127.0.0.1:8080
```
`tcp` still reports `ok` — Nginx is listening and accepts the connection. `http` reports
`status: error`, `http_status: 504` (Gateway Time-out), after roughly 3 seconds.

**Actual symptom:** The reverse proxy is up and reachable, but it cannot reach its upstream
(`app:8000`) — the container is stopped, so there is no listener on that address. In this Docker
network, a connection attempt to a stopped container's address is silently dropped rather than
actively refused, so Nginx's own `proxy_connect_timeout` (tuned down to 3s in
[`simulation/nginx.conf`](simulation/nginx.conf) specifically so this surfaces quickly instead of
hanging on Nginx's 60s default) is what actually fires, producing 504 rather than an immediate 502.
A 502 can still occur on other Docker network drivers/platforms where a stopped container's
address *is* actively refused at the TCP level — both are "proxy reached, upstream did not
respond," just via a different failure path at the network layer.

**How an engineer would investigate:** TCP succeeding but HTTP failing immediately narrows the
problem to the application/proxy layer, not the network path. Check `docker compose ps` for the
app container's state, then `docker compose logs proxy`, which names the exact upstream address
and the real cause:
```
2026/11/05 12:35:00 [error] 21#21: *86 upstream timed out (110: Operation timed out) while
connecting to upstream, client: 127.0.0.1, server: , request: "GET /health HTTP/1.1",
upstream: "http://172.21.0.2:8000/health", host: "127.0.0.1:80"
```
This points directly at the upstream (`172.21.0.2:8000`, the stopped app container), not at
Nginx's own listener or the client's network path.

**Resolution:** `./simulation/lab.sh start-app`, then re-run the check to confirm `http_status: 200`.
Note: restarting `proxy` itself (not just `app`) while `app` is stopped will make Nginx fail to
start at all (`host not found in upstream "app"`), because Nginx resolves the upstream hostname at
startup. If you need to restart the proxy, bring `app` up first.

## Scenario 3 — Application error (HTTP 500)

**What was done:** Nothing stopped — the app is healthy, but the check targets its `/fail` route,
which always returns HTTP 500.

**What CloudPulse detected:**
```bash
cloudpulse --url http://127.0.0.1:8080/fail
```
`http` reports `status: error`, `http_status: 500`.

**Actual symptom:** The application is running and the proxy reached it successfully — the
application itself returned an error response for this specific route.

**How an engineer would investigate:** A clean 500 (as opposed to a 502/504 from the proxy) means
the request reached the application and it chose to fail. Check `docker compose logs app` for a
traceback or error log tied to the request, and compare the failing route against others that
return 200 to scope whether the issue is route-specific or systemic.

**Resolution:** This route is intentionally always-failing for the demo; in a real incident, the
fix depends on what the application log shows (a bug in that handler, a bad dependency, etc.) and
is deployed as a code fix, not a lab reset.

## Scenario 4 — Unhealthy endpoint (HTTP 503)

**What was done:** `./simulation/lab.sh unhealthy` sets `APP_MODE=unhealthy` and recreates the app.

**What CloudPulse detected:**
```bash
cloudpulse --url http://127.0.0.1:8080/health
```
`http` reports `status: error`, `http_status: 503` (Service Unavailable).

**Actual symptom:** The application process is running and responds, but it is deliberately
reporting itself as not ready to serve traffic — distinct from scenario 2, where there was no
process to respond at all, and from scenario 3, where the route itself errored.

**How an engineer would investigate:** 503 from the application (not the proxy) usually means a
dependency or readiness check inside the app is failing — a database connection, a warm-up step, or
an explicit maintenance flag. `docker compose logs app` and the app's own health-check logic are the
next places to look; compare with 502 (proxy cannot reach upstream at all) to avoid conflating the
two.

**Resolution:** `./simulation/lab.sh healthy` restores the baseline. In production this would be
whatever restores the dependency the health check depends on.

## Summary table

| Observed HTTP status | TCP check | What it tells you |
|---|---|---|
| 200 | ok | Healthy, end to end |
| 502 / 504 | ok | Proxy is up, upstream app is unreachable (stopped, crashed, wrong address). 502 = actively refused; 504 = the proxy's own connection attempt timed out (what this lab actually produces — see Scenario 2) |
| 500 | ok | Request reached the app; the app's own code/logic failed for that route |
| 503 | ok | The app is running but reports itself not ready (dependency/health-check failure) |
| any | error | The network path itself (DNS, routing, firewall, listener) is the problem — check that before looking at the application at all |

CloudPulse reports these as observed facts (status codes, reachability, latency), not as a root
cause — the "how an engineer would investigate" notes above are the suggested next steps, not a
diagnosis.
