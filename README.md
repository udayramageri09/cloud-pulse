<p align="center">
  <img src="assets/banner.svg" alt="CloudPulse - Linux & Network Diagnostics Toolkit" width="100%"/>
</p>

<p align="center">
  <a href="https://github.com/udayramageri09/cloud-pulse/actions/workflows/ci.yml"><img src="https://github.com/udayramageri09/cloud-pulse/actions/workflows/ci.yml/badge.svg" alt="CI status"></a>
  <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python 3.10+">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-informational" alt="MIT License"></a>
</p>

CloudPulse is a dependency-free Python CLI for the first minutes of an incident: it checks the host
(straight from Linux `/proc`) and the network path to a service (DNS, TCP, HTTP, TLS), then writes a
structured incident report with severities, symptoms and next steps. It ships with a Docker Compose
failure lab that reproduces real 500/503/502/504 errors, tested end to end in CI.

## Demo

<p align="center">
  <video src="docs/media/cloudpulse-demo.mp4" controls width="720">
  </video>
</p>

<p align="center"><a href="docs/media/cloudpulse-demo.mp4">cloudpulse-demo.mp4</a> -- 2:27, walks through the CLI, the Docker failure lab and the incident report format (recorded on 0.1.0).</p>

## Features

- **Host checks from `/proc`, no psutil:** CPU (two-sample delta of `/proc/stat`), load average per
  core, memory (`MemAvailable`), disk, uptime, top processes by resident memory.
- **Network checks, run concurrently:** DNS resolution, TCP connect, HTTP status and latency, and for
  `https://` URLs a verified TLS handshake with days until the certificate expires.
- **Incident reports:** each check gets a severity, an observed symptom and suggested next steps;
  text for humans, JSON for tools.
- **Monitoring-friendly exit codes:** Nagios convention (0 healthy, 1 degraded, 2 critical,
  3 unknown), with configurable warning thresholds.
- **A real failure lab:** Nginx in front of a small app, switchable between healthy, failing, not
  ready and down.
- **Tested at every level:** 39 unit and integration tests (92% coverage), a real local TLS server
  for certificate tests, and an end-to-end run of every lab scenario in CI.

## Quick start

Run the published container image (no install needed):

```bash
docker run --rm ghcr.io/udayramageri09/cloud-pulse:0.2.0 --dns github.com --url https://github.com
```

Or install from source:

```bash
python -m pip install -e .
cloudpulse --dns github.com --url https://github.com
```

Example output (the container run above, on a WSL2 laptop):

```text
CloudPulse Incident Report
Overall status: HEALTHY
Checks: 9 total - 9 info, 0 warning, 0 critical

[INFO] cpu - usage_percent=0.5, logical_cores=18
[INFO] load - load_1m=0.51, load_5m=0.22, load_15m=0.2, per_core_1m=0.03, logical_cores=18
[INFO] memory - usage_percent=20.3, available_bytes=6398054400, total_bytes=8026116096
[INFO] dns (github.com) - addresses=['20.207.73.82'], duration_ms=48.89
[INFO] http (https://github.com) - http_status=200, duration_ms=142.12
[INFO] tls (github.com:443) - expires_at=2027-01-27T23:59:59+00:00, days_remaining=67, duration_ms=117.12
```

(Trimmed. `--format json --output report.json` writes the full report as JSON; `--verbose` adds symptoms
and next steps for every check. A failing check is reported as `[CRITICAL]` with its symptom and next steps.)

### Options

| Flag | Purpose |
|---|---|
| `--dns HOST`, `--tcp HOST:PORT`, `--url URL` | network checks to run (an `https://` URL also checks TLS) |
| `--cpu-warn`, `--mem-warn`, `--disk-warn PCT` | warning thresholds (default 90%) |
| `--tls-warn-days DAYS` | warn when the certificate expires sooner (default 14) |
| `--format text\|json`, `--output FILE` | report format and destination |
| `--verbose` | show symptoms and next steps for every check |

### Exit codes

| Code | Meaning |
|---|---|
| 0 | healthy: every check passed |
| 1 | degraded: at least one warning |
| 2 | critical: at least one check failed |
| 3 | unknown: invalid arguments |

## Failure lab

```mermaid
flowchart LR
    CP[cloudpulse] -->|TCP / HTTP| NGINX["Nginx :8080"]
    NGINX -->|"proxy_pass (Docker DNS)"| APP["demo app\n/health  /fail"]
```

| Scenario | Command | CloudPulse sees |
|---|---|---|
| Healthy | `./simulation/lab.sh up` | `/health` 200 |
| Application error | (none, request `/fail`) | 500 |
| App not ready | `./simulation/lab.sh unhealthy` | 503 |
| Upstream down | `./simulation/lab.sh stop-app` | TCP ok, HTTP 502 or 504 |
| Recovery | `./simulation/lab.sh healthy` | 200 |

`scripts/e2e_lab.sh` runs all five scenarios and checks each status; CI runs it on every push.
[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) explains what each failure means and how to
investigate it.

## Limitations

- Host metrics come from Linux `/proc`; on Windows and macOS those checks report `unsupported`
  rather than guessing.
- Inside a container, CloudPulse sees only the container's own processes (its PID namespace), but
  `/proc/meminfo` and `/proc/loadavg` are not namespaced, so memory and load describe the whole host,
  not the container's cgroup limits. Reading `/sys/fs/cgroup` (`memory.max`, `cpu.max`) is the
  planned fix.
- One report per run: no continuous monitoring or alerting (the exit codes let a scheduler or
  monitoring system do that).

## Development

```bash
python -m pip install -e ".[dev]"
python -m pytest --cov=cloudpulse      # unit + integration tests
ruff check src tests && ruff format --check src tests
scripts/e2e_lab.sh                     # end-to-end against the Docker lab
```

```text
src/cloudpulse/   checks.py (host + network checks), report.py (incident model), cli.py
tests/            pytest suite; fixtures/proc is a fake /proc tree
simulation/       failure lab: demo app, nginx.conf, lab.sh / lab.ps1
scripts/          e2e_lab.sh
docs/             architecture, troubleshooting, deployment, screenshots, demo video
```

## Learn more

| | |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Design decisions: /proc parsing, concurrency, TLS checks, testing strategy |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Every lab scenario, with real logs |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Docker image, GHCR, Codespaces, releases |
| [docs/images/](docs/images/) | Captured CLI, lab and test output |
| [CHANGELOG.md](CHANGELOG.md) | What has shipped |

## License

[MIT](LICENSE)

## One-command demo

```bash
git clone https://github.com/udayramageri09/cloud-pulse.git && cd cloud-pulse
scripts/demo.sh              # starts the Docker lab and walks through 7 steps
```

Needs Docker (running) and Python 3.10+. CloudPulse installs itself into `.venv` on the first run.
The lab uses port 18080; change it with `CLOUDPULSE_LAB_PORT=9090 scripts/demo.sh`.
Press Enter between steps, or run `scripts/demo.sh --no-pause`.
