# Screenshots

Every image here is a styled render of genuinely captured output from CloudPulse 0.1.0 -- the
text inside each one is exactly what the real CLI, test suite, or Docker lab printed.

| File | What it shows |
|---|---|
| `test-suite.png` | `python -m unittest discover -s tests -v` -- all 13 tests passing |
| `healthy-report.png` | Full `--verbose` incident report against the healthy lab baseline |
| `scenario-500.png` | The `/fail` route -- a clean application-level HTTP 500 |
| `scenario-504-upstream-down.png` | App container stopped -- Nginx's own connect-timeout firing as a 504 |
| `scenario-503-unhealthy.png` | `APP_MODE=unhealthy` -- the app reporting itself not ready |
| `docker-compose-ps.png` | `docker compose ps` -- both lab containers healthy |
| `nginx-logs.png` | Real Nginx access/error log lines, including the `upstream timed out` error for the 504 scenario |
| `sample-incident-json.png` | A full JSON incident report (healthy run, with DNS/TCP/HTTP checks included) |
