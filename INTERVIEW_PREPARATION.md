# CloudPulse interview preparation

Run every demo yourself before discussing it -- everything below reflects commands that were
actually executed against a live Docker lab while building this project, not assumed behavior.

## Feature deep-dives

For each feature: why it exists, how it works, the trade-offs made, what happens when it fails,
and what a "v2" would add.

### Host checks (CPU, memory, disk, uptime, processes)

- **Why:** These are the first four things anyone checks when a host "seems unhealthy" -- it made
  sense to automate asking them consistently rather than running four separate ad-hoc commands.
- **How:** CPU reads two snapshots of `/proc/stat` 0.1s apart and computes utilization from the
  delta (a single snapshot is meaningless -- `/proc/stat` is a cumulative counter since boot).
  Memory and total-vs-available come from `/proc/meminfo`. Disk uses `shutil.disk_usage`, which is
  cross-platform. Processes are enumerated by iterating `/proc/<pid>/status` for `VmRSS`.
- **Trade-offs:** No `psutil` dependency, at the cost of CPU/memory/process checks only working on
  Linux. The CPU check also costs 0.1s of wall-clock time per run (two snapshots).
- **Failure scenarios:** A process can exit between `iterdir()` listing it and reading its
  `/proc/<pid>/status` -- handled by catching `OSError`/`AttributeError`/`ValueError` around that
  read and skipping it, rather than aborting the whole report over one vanished process. An invalid
  `--disk-path` now returns a structured `error` check result instead of an uncaught
  `FileNotFoundError` crashing the CLI.
- **v2:** A `psutil`-backed fallback (optional extra, not a hard dependency) for cross-platform
  CPU/memory/process support; a configurable warning threshold instead of a fixed 90%.

### Network checks (DNS, TCP, HTTP)

- **Why:** TCP reachability and HTTP success are different facts, and conflating them hides where
  a failure actually sits (network vs. proxy vs. application).
- **How:** DNS uses `socket.getaddrinfo`; TCP uses `socket.create_connection` with a 3s timeout;
  HTTP uses `urllib.request.urlopen` with a 5s timeout and a descriptive `User-Agent`.
- **Trade-offs:** Fixed default timeouts (not yet configurable via a flag) and no retry logic --
  intentional, since this is a single-shot diagnostic snapshot, not a monitoring probe that needs
  to tolerate transient blips.
- **Failure scenarios:** `check_dns` catches `socket.gaierror`/`OSError`; `check_tcp` catches
  `OSError`; `check_http` separately catches `urllib.error.HTTPError` (to capture the status code
  on a 4xx/5xx) versus `URLError`/`TimeoutError`/`OSError` (no response at all, no status code).
- **v2:** A configurable `--timeout`; a latency warning threshold (currently only CPU/memory/disk
  have thresholds, not HTTP/TCP response time).

### Incident report (severity, symptom, next steps)

- **Why:** A bare list of check results makes the reader do the "so what" work every time. An
  incident ID, overall status, and per-check severity make a report skimmable and comparable
  across runs.
- **How:** `checks.py` stays fact-only (`status`, measured values). `report.py`'s `classify()`
  maps `status` to `severity` (`ok`/`unsupported` -> `info`, `warning` -> `warning`, `error` ->
  `critical`) and, for anything not plain-`ok`, generates a `symptom` string from the check's own
  fields and a static `next_steps` list keyed by check name.
- **Trade-offs:** `next_steps` are static per check-name, not dynamically generated from the
  specific failure -- deliberately, to avoid ever implying a diagnosis the tool hasn't actually
  verified.
- **Failure scenarios:** N/A for this feature itself, but its own tests (`test_reports.py`) verify
  that an `ok` check gets no symptom, a `warning`/`error` check does, and an `unsupported` check
  gets its existing `detail` text rather than a fabricated one.
- **v2:** Historical comparison between two incident reports (did this get worse since the last
  run) is the natural next step, but was explicitly out of scope to keep this a single-shot tool.

### Docker image & CI/CD

- **Why:** A CLI someone can run via `docker run` without installing Python locally lowers the
  barrier to trying it, and a non-root, dependency-free image is what you'd actually want in a
  real pipeline.
- **How:** A two-stage `Dockerfile` -- `builder` installs into a venv, final stage copies just
  that venv onto `python:3.12-slim` and runs as uid 10001. `.github/workflows/docker-image.yml`
  builds and validates (runs `--help`, checks the container's `id -u` is non-zero) on every
  push/PR, and only publishes to GHCR on a `v*.*.*` tag.
- **Trade-offs:** Publishing requires the repository owner to enable package-write permissions
  manually (a one-time repo setting) -- this project never claims an image is published without
  that workflow run actually succeeding.
- **Failure scenarios:** If GHCR permissions aren't enabled, the `publish` job fails with 403 --
  documented in [DEPLOYMENT.md](DEPLOYMENT.md) rather than silently assumed to work.
- **v2:** Multi-arch builds (`arm64`/`amd64`) via buildx platform flags.

## 20+ interview questions

### Linux, processes, and system metrics

**Q: How does `/proc/stat` let you compute CPU usage, given it's a cumulative counter?**
A: Each field (user/nice/system/idle/...) is a running total of jiffies since boot, not an
instantaneous rate. Taking two snapshots a short interval apart and computing
`(delta_total - delta_idle) / delta_total` gives the fraction of that interval spent non-idle --
which is what "CPU usage" actually means.

**Q: Why does the process list use `VmRSS` and not `VmSize`?**
A: `VmSize` is a process's total virtual address space, which can be far larger than what it
actually has resident in physical RAM (e.g. memory-mapped files, reserved-but-unused heap).
`VmRSS` (Resident Set Size) is what is actually occupying physical memory, which is what you care
about when asking "what is using up the host's RAM."

**Q: A process disappears between listing `/proc` and reading its status file. What happens?**
A: `check_processes` catches `OSError` (file gone), `AttributeError` (the regex search on its
`status` content returns `None` if the file was empty/truncated mid-exit), and `ValueError`
(malformed integer), and simply skips that one process rather than letting the exception abort the
whole report.

**Q: How would you investigate a host reporting high memory usage?**
A: Compare `MemTotal` vs `MemAvailable` (not `MemFree` -- available accounts for reclaimable
cache/buffers, free does not, so free alone overstates the problem). Then check the process list
for the actual consumer, and take a second reading later to tell a leak (steadily growing) from
steady-but-high usage (one large, stable workload).

### Disk

**Q: Why catch `OSError` around `shutil.disk_usage` instead of validating the path first?**
A: Validating "does this path exist" and then calling `disk_usage` has a race (TOCTOU) and
duplicates logic `disk_usage` already has to do internally. Catching the `OSError` it already
raises for a bad path is simpler and just as correct.

**Q: Disk usage is at 95%. What's the next step, concretely?**
A: `du` on the mounted path to find what's actually large, not just that it's full. Distinguish
log/temp growth (safe to clean after checking it isn't needed for the current investigation) from
a genuinely full data volume, which usually means the real fix is elsewhere (retention policy,
undersized volume).

### DNS

**Q: What's the difference between a `socket.gaierror` and a generic `OSError` in `check_dns`?**
A: `gaierror` is `getaddrinfo`'s own specific exception for resolution failures (NXDOMAIN, no
such host); a bare `OSError` can also surface for other failures (e.g. a resolver timeout at the
OS level). Catching both means any resolution failure becomes a clean `error` result instead of an
uncaught exception, without needing to enumerate every possible errno.

**Q: DNS resolves to an IP, but TCP to that IP fails. What does that tell you?**
A: Name resolution and the actual network path are two independent layers. Name resolution working
only proves the resolver (and whatever it's authoritative/cached from) is fine -- it says nothing
about routing, firewalling, or whether anything is actually listening at that address.

### TCP

**Q: Walk through what `socket.create_connection` actually does.**
A: It resolves the address if needed, opens a socket, and performs the TCP three-way handshake
(SYN, SYN-ACK, ACK) within the given timeout. If the handshake completes, the check succeeds
before any application data is exchanged -- which is exactly why a successful TCP check says
nothing about the application layer.

**Q: TCP succeeds but HTTP fails. Narrow down the cause.**
A: The listener accepted the connection (something is bound to that port and the network path
works), but whatever responded over it isn't behaving as an HTTP server/the expected app --
could be the wrong service on that port, a proxy that accepted the connection but can't reach its
own upstream, or an application that accepted the connection and then errored/timed out.

### HTTP status codes and Nginx

**Q: Explain the difference between 500, 502, 503, and 504, concretely, not from memory.**
A: From this project's own lab: 500 means the request reached the application and *it* decided to
fail (its own handler raised/returned an error). 503 means the application is up and responding,
but is deliberately reporting itself not ready. 502/504 mean the *proxy* couldn't get a valid
response from its upstream at all -- 502 if the upstream actively refused/reset the connection,
504 if the proxy's own attempt to reach the upstream timed out. In this project's own lab, stopping
the app container produced a 504, not a 502, because Docker's bridge network silently dropped
packets to the stopped container's address rather than actively refusing them -- so Nginx's
connect timeout, not a refused connection, was what actually fired. That is also why this project's
`simulation/nginx.conf` sets a short `proxy_connect_timeout` (3s) deliberately: with Nginx's 60s
default, the symptom would have been a very slow hang rather than a fast, legible failure.

**Q: Why does restarting the Nginx container (not the app) make an outage worse in this lab?**
A: Nginx resolves the `proxy_pass` upstream hostname (`app`) once at startup/reload. If the `app`
container is stopped when Nginx starts, Docker's DNS can't resolve `app` at all, and Nginx fails to
start entirely (`host not found in upstream`) instead of just failing individual requests. The fix
is ordering: bring the app back up before restarting (or reloading) the proxy.

**Q: What does `proxy_connect_timeout` actually bound, vs `proxy_read_timeout`?**
A: `proxy_connect_timeout` bounds how long Nginx waits to establish the TCP connection to the
upstream. `proxy_read_timeout` bounds how long it waits for the upstream to send a response (or
the next chunk of one) once connected. A dead/unreachable upstream hits the first; a slow-but-alive
upstream hits the second.

### Docker networking and health checks

**Q: Why does `docker compose stop app` not immediately produce a TCP-level connection refused to Nginx?**
A: It depends on the network driver and platform -- on this Docker Desktop/WSL2 setup, packets to
a stopped container's address were silently dropped rather than answered with a TCP RST, so the
failure surfaced as a connect timeout (504 via Nginx), not an immediate refusal (which would have
looked like a 502). Both are "the upstream is unreachable"; which one you see depends on exactly
how the network layer reports that unreachability.

**Q: What does a Docker Compose `healthcheck` actually change?**
A: It gives `docker compose ps`/`docker inspect` a judgment about container readiness beyond "the
process is running," and lets `depends_on: condition: service_healthy` (not used here, but
available) gate startup ordering on real readiness rather than just process start. In this lab,
the app's healthcheck hits its own `/health` route from inside the container.

**Q: Why bind the lab's port to `127.0.0.1` explicitly instead of leaving it as `8080:80`?**
A: Compose's default binds to all interfaces (`0.0.0.0`), which on a machine without a restrictive
firewall means the demo app (deliberately running error/unhealthy modes) is reachable from the
local network, not just the machine itself. Binding to `127.0.0.1:8080:80` makes "local only" true
regardless of the host's firewall configuration.

### Timeouts and structured error handling

**Q: Why does every network check have its own explicit timeout instead of relying on a default?**
A: Without one, a hung TCP handshake or an HTTP server that accepts the connection but never
responds would block the CLI indefinitely -- unacceptable for a diagnostic tool whose entire point
is to run quickly and tell you something within seconds.

**Q: Why return structured `{"status": "error", "error": "..."}` dicts instead of raising?**
A: An exception propagating out of one check would abort the entire report over a single expected
failure (a DNS lookup failing is not a bug in CloudPulse). Catching the specific expected exception
types and returning them as data keeps one failing check from taking down the rest of the report,
and keeps "the report has an error in it" distinct from "the program crashed."

**Q: What's the actual Windows portability bug that was found and fixed in this project?**
A: The text report used a Unicode em dash (`—`). `print()` on Windows, when stdout is
redirected to a file rather than a real console, defaults to the system codepage (cp1252) rather
than UTF-8. cp1252 happens to have a byte for em dash (`0x97`), so it didn't crash here, but on any
character cp1252 doesn't support, or on a genuinely different codepage, it would raise
`UnicodeEncodeError`. It was replaced with a plain ASCII `-` -- the simplest fix that removes the
platform dependency entirely rather than special-casing encoding.

### Python architecture and testing strategy

**Q: Why are `checks.py` and `report.py` separate modules instead of one file?**
A: `checks.py` answers "what happened" (a fact, independently verifiable -- did the socket
connect, yes or no). `report.py` answers "how bad is that, and what should you look at next" (a
judgment built on top of the fact). Keeping them separate means the judgment logic (severity
mapping, symptom text, next-step suggestions) can change without touching -- or needing to
re-test -- the fact-gathering logic, and vice versa.

**Q: How do the tests avoid depending on real network access or real failures?**
A: `unittest.mock.patch` replaces `socket.getaddrinfo`/`socket.create_connection` with functions
that raise the specific exception being tested, so the test exercises CloudPulse's error-handling
branch deterministically, without depending on an actual flaky network condition existing.

**Q: What would you add to the test suite next?**
A: Property-style tests for `classify()` ensuring every `(name, status)` combination that appears
in `checks.py` has a sensible `severity`, and an integration test that runs the real CLI against
the Docker lab in CI (currently the lab is validated manually/locally, not in CI, since CI runners
don't reliably have Docker-in-Docker networking parity with a local Docker Desktop setup).

### Incident investigation methodology

**Q: Why structure next-step suggestions instead of trying to state a root cause?**
A: A root cause requires context CloudPulse doesn't have (what changed recently, what's normal for
this host, what the on-call engineer already knows). Suggesting *where to look next*, grounded in
what was actually observed, is something the tool can respect that limit by not overstating what
it was actually able to check.

**Q: Walk through how you'd use this tool in an actual incident.**
A: Run it with no network flags first (host-only, no external dependency) to rule out the local
machine being the problem. Then add `--tcp`/`--url` against the specific target reported down, to
place the failure at the network/proxy/application boundary. Use `--verbose` once something is
already flagged, to get the full symptom + next-steps text rather than just the status line.

## Scope boundary -- be ready to say this plainly

CloudPulse is a single-shot diagnostic CLI, not a monitoring platform. It does not run
continuously, does not alert anyone, does not collect logs from remote hosts, and does not
determine root cause -- it reports what it actually observed, classifies how severe that is, and
suggests where to look next. A tool like Datadog/Prometheus/CloudWatch does continuous collection,
alerting, and historical trend analysis across a fleet; this does none of that, on purpose, to stay
small enough to fully understand and verify end to end.

## Before claiming anything about this project

- Run the automated tests and the host-only CLI locally, yourself, right before the interview.
- If discussing the Docker lab, actually run all four scenarios and read the real Nginx/app logs
  -- the exact status codes observed here (504, not 502, for a stopped upstream) depend on the
  Docker network driver and are worth being able to explain, not just recite.
- Be ready to explain timeout choices, exit codes, the checks/report module split, and why the
  tool reports symptoms and next steps rather than root causes.
