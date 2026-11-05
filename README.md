# CloudPulse

**Linux & Network Diagnostics Toolkit** — a small Python CLI that gathers host health signals and checks DNS, TCP ports, and HTTP endpoints, then writes a text or JSON incident report.

## Current scope

- Linux CPU utilization, memory, disk usage, uptime/platform, and top processes by memory use.
- DNS lookup, TCP connection, and HTTP/HTTPS status and latency checks.
- Text and JSON reports; nonzero exit status when a check reports an issue.
- Docker Compose lab with a sample HTTP app behind Nginx for safe local failure exercises.
- Automated unit tests and GitHub Actions CI.

This is a diagnostic aid, not an agent or a production monitoring system. It does not collect logs from arbitrary hosts, make root-cause claims, monitor continuously, or deploy to a cloud provider.

## Install and run

Python 3.10+ is required. CloudPulse uses the Python standard library and Linux `/proc` for host metrics. On Linux, macOS, or WSL:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
cloudpulse --dns example.com --tcp example.com:443 --url https://example.com
cloudpulse --format json --output incident.json --dns example.com --url https://example.com
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`. Disk checks use the system root path by default. CPU and memory utilization and process listing are currently Linux `/proc` checks; on other systems these checks report `unsupported` rather than inventing measurements.

The command exits `0` when all selected checks are okay and `1` when at least one check reports an issue. DNS/TCP/HTTP checks are opt-in so a basic host report needs no external network access.

## Failure simulation lab

Requires Docker Engine and the Compose plugin. From this directory:

```bash
docker compose up --build -d
cloudpulse --url http://localhost:8080/health --tcp localhost:8080
```

Exercise these cases:

1. **Healthy:** `docker compose up -d`; `/health` returns HTTP 200 through Nginx.
2. **Application unavailable / proxy 502:** `docker compose stop app`; run CloudPulse against the URL again. The proxy reports an upstream connection failure.
3. **Application error:** keep the app running and check `http://localhost:8080/fail`; CloudPulse records HTTP 500.
4. **Unhealthy endpoint:** `APP_MODE=unhealthy docker compose up -d --force-recreate app`; the app health route returns 503. Reset with `docker compose down` then `docker compose up --build -d`.

Use `docker compose logs app proxy` to compare the observed symptom with service output. Lab-only services bind to localhost through the host port mapping; do not expose this demo service to an untrusted network.

## Architecture

```text
CLI (argparse)
  ├── host checks (/proc, shutil, platform)
  ├── network checks (socket / urllib)
  └── report renderer (text / JSON)

Docker Compose lab: CloudPulse CLI -> localhost:8080 -> Nginx -> demo app
```

Checks return structured dictionaries, so the CLI and report formatter remain separate. Network calls have timeouts and expected operating-system/network failures are recorded as check results rather than stack traces.

## Troubleshooting notes

| Symptom | First checks | Likely next step |
|---|---|---|
| DNS error | Check hostname spelling and resolver configuration (`resolvectl status` on systemd Linux) | Compare with `getent hosts <name>`; determine whether one name or the resolver is affected |
| TCP error | Confirm host/port and route; run `ss -tn` and `nc -vz <host> <port>` | Check listener, firewall rules, and whether the service binds to the expected interface |
| HTTP 5xx | Compare the HTTP status with TCP reachability; inspect `docker compose logs app proxy` in the lab | Distinguish proxy/upstream failure from an application response |
| High memory/disk | Inspect CloudPulse process list; use `ps aux --sort=-%mem` or `df -h` | Identify growth or a full filesystem before restarting services |

These commands are investigation aids; output depends on operating system, permissions, resolver, and network policy.

## Development

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
```

The tests isolate expected network failures with mocks and validate report rendering. Live Docker failure exercises are manual and require Docker; CI runs the Python test suite and a host-only CLI smoke check.
