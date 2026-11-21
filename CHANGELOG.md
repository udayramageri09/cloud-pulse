# Changelog

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows
[Semantic Versioning](https://semver.org/). See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md#cutting-a-release)
for what a tag push triggers.

## [0.2.0] - 2026-11-22

### Added
- TLS check for `https://` URLs: verified handshake and days until the certificate expires
  (warning under 14 days); verification failures reported with OpenSSL's reason.
- Load average check (`/proc/loadavg`), reported per logical core.
- `--cpu-warn`, `--mem-warn`, `--disk-warn` and `--tls-warn-days` threshold flags.
- `scripts/e2e_lab.sh`: drives the failure lab through all five scenarios; runs in CI.
- Fixture-based `/proc` tests (`tests/fixtures/proc`), real-TLS-server tests, CLI exit-code tests
  and a concurrency timing test (39 tests, 92% coverage).
- CI: ruff lint and format check, Python 3.10/3.12/3.13 matrix, 85% coverage gate.
- `logs` verb for `simulation/lab.sh` and `lab.ps1`.
- Incident report model: `incident_id`, `host` block, `overall_status`
  (`healthy`/`degraded`/`critical`), and per-check `severity`/`symptom`/`next_steps`.
- CPU usage now has a warning threshold (90%), matching the existing memory/disk thresholds.
- `--verbose` CLI flag to show symptoms and next-step suggestions for every check, not just the
  ones with issues.
- `--url` scheme validation at the CLI layer (`http://`/`https://` only).
- `disk` check now returns a structured `error` result for an invalid path instead of raising.
- Standalone `Dockerfile` for the CloudPulse CLI itself (multi-stage, non-root, no secrets),
  separate from the demo app's `simulation/app/Dockerfile`.
- `.github/workflows/docker-image.yml`: builds and validates the CLI image on every push/PR;
  publishes to GHCR on a `v*.*.*` tag (after the repository owner enables package permissions).
- `.devcontainer/devcontainer.json` for GitHub Codespaces / VS Code Dev Containers.
- `simulation/lab.sh` / `simulation/lab.ps1`: single-command controls for the failure-simulation
  lab (`up`, `down`, `reset`, `healthy`, `unhealthy`, `stop-app`, `start-app`).
- `TROUBLESHOOTING.md`, `DEPLOYMENT.md`, `CHANGELOG.md`.
- `CLOUDPULSE_LAB_PORT` environment variable so the lab's published port is configurable.

### Changed
- Exit codes follow the Nagios plugin convention: 0 healthy, 1 degraded, 2 critical, 3 invalid
  arguments.
- Network checks (DNS, TCP, HTTP, TLS) run concurrently; report order is unchanged.
- Host checks read `/proc` from a configurable root (`CLOUDPULSE_PROC_ROOT`).
- The lab's Nginx resolves `app` through Docker's DNS, so a recreated app container is followed.
- Tests moved to pytest; code formatted with ruff.
- Docs, screenshots and the demo video moved under `docs/`.
- `docker-compose.yml`: the lab's Nginx port now binds to `127.0.0.1` explicitly (previously bound
  to all interfaces); added healthchecks, `no-new-privileges`, and a read-only filesystem for the
  demo app.
- `simulation/nginx.conf`: added a 3s `proxy_connect_timeout` so a stopped upstream surfaces as a
  fast `504` instead of hanging on Nginx's 60s default.

### Fixed
- Text report formatting used a Unicode em dash that Python writes as a Windows-1252 byte (`0x97`)
  rather than UTF-8 when stdout is redirected on Windows -- replaced with a plain ASCII `-` for
  portability.

## [0.1.0] - 2026-11-05

Initial MVP: Linux host checks (CPU, memory, disk, uptime, top processes by memory), DNS/TCP/HTTP
network checks, text and JSON reports, unit tests, GitHub Actions CI, and the original
Docker Compose failure-simulation lab.
