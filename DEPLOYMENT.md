# Deployment

CloudPulse is a CLI tool, not a service. "Deployment" here means distributing a way to run
the CLI and, separately, the local failure-simulation lab. Nothing in this project needs or
has a hosted/cloud deployment.

## What is distributed

| Artifact | What it is | Where it runs |
|---|---|---|
| Python package (source) | `cloudpulse` CLI, installed with `pip install -e .` | Any machine with Python 3.10+; Linux (or WSL) for the host-metric checks, any OS for network checks |
| Docker image (`Dockerfile`, root) | The CLI itself, containerized | Any Docker host; always Linux inside the container, so host-metric checks work regardless of the host OS |
| `.devcontainer/` | A ready-to-code environment | GitHub Codespaces or VS Code Dev Containers |
| `docker-compose.yml` + `simulation/` | The failure-simulation lab (demo app + Nginx) | Local Docker only — see [TROUBLESHOOTING.md](TROUBLESHOOTING.md). This is a demo target, not something to deploy anywhere else |

## Prerequisites

- Python 3.10+ for source installs.
- Docker Engine + Compose plugin for the CLI image or the failure-simulation lab.
- No account, API key, or cloud credentials are required for anything in this project.

## Installing and running

### From source

```bash
python -m venv .venv && source .venv/bin/activate   # .venv\Scripts\Activate.ps1 on Windows
python -m pip install -e .
cloudpulse --dns example.com --tcp example.com:443 --url https://example.com
```

### From the Docker image

Build it locally (always works, no registry needed):

```bash
docker build -t cloudpulse:local .
docker run --rm cloudpulse:local --url https://example.com
```

Or, once a release has been published to GHCR (see below):

```bash
docker pull ghcr.io/udayramageri09/cloud-pulse:latest
docker run --rm ghcr.io/udayramageri09/cloud-pulse:latest --url https://example.com
```

The image runs as a non-root user (`cloudpulse`, uid 10001) with no secrets baked in. It has
no network access requirements of its own beyond whatever target you point `--dns`/`--tcp`/`--url`
at.

### GitHub Codespaces / Dev Containers

Open the repository in a Codespace, or "Reopen in Container" in VS Code. `.devcontainer/devcontainer.json`
installs the package and runs the test suite automatically via `postCreateCommand`. The
`docker-in-docker` feature is enabled so the failure-simulation lab (`docker compose up`) can run
inside the Codespace too.

**Limitations:** GitHub Codespaces usage is metered against the account's included free quota and
is not unlimited; nested Docker-in-Docker inside a Codespace works but is slower than a local
Docker Desktop install, and very large compose builds may be constrained by the machine type
assigned to the Codespace. Verify Docker is actually available inside the Codespace (`docker info`)
before relying on the lab there.

## Configuration

CloudPulse takes all configuration as CLI flags (`--dns`, `--tcp`, `--url`, `--disk-path`,
`--format`, `--output`, `--verbose`) -- there is no config file or environment variable it reads
for its own behavior. The failure-simulation lab is configured through `docker-compose.yml`
environment variables:

- `APP_MODE` (`healthy` | `unhealthy`) -- controls the demo app's `/health` route.
- `CLOUDPULSE_LAB_PORT` -- the host port Nginx is published on (default `8080`; override if that
  port is already in use on your machine, e.g. `CLOUDPULSE_LAB_PORT=18080 docker compose up -d`).

## Security considerations

- The CLI image runs as a non-root user and contains no secrets or credentials.
- The failure-simulation lab's ports are bound to `127.0.0.1` only (see `docker-compose.yml`) --
  never exposed beyond the local machine by default.
- The lab's `app` container runs with `read_only: true` and `no-new-privileges`; both lab
  containers avoid running anything beyond the single demo HTTP server / Nginx.
- `--url` is restricted to `http://`/`https://` at the argument-parsing level.
- Nothing in this project collects, stores, or transmits data beyond the single diagnostic run
  requested on the command line.

## Versioning strategy

CloudPulse follows [Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH`.

- **MAJOR** -- incompatible changes to the CLI's flags or the JSON report schema.
- **MINOR** -- new checks, new flags, or additive fields in the JSON report.
- **PATCH** -- bug fixes and documentation with no interface change.

The version lives in `pyproject.toml` (`project.version`) and is tagged in git as `vMAJOR.MINOR.PATCH`
(e.g. `v0.2.0`), which is what triggers a GHCR publish (see below). See [CHANGELOG.md](CHANGELOG.md)
for what has actually shipped.

## Cutting a release

1. Update `project.version` in `pyproject.toml` and add an entry to `CHANGELOG.md`.
2. Commit, merge to `main`.
3. Tag: `git tag v0.2.0 && git push origin v0.2.0`.
4. The `Docker Image` workflow (`.github/workflows/docker-image.yml`) builds and pushes
   `ghcr.io/udayramageri09/cloud-pulse:0.2.0` and `:latest` -- **but only after** GHCR publishing is
   enabled for this repository (see below). Check the Actions tab to confirm the `publish` job
   actually succeeded before treating the image as available; do not assume it from the tag alone.
5. Draft a GitHub Release from the tag using the template below.

### Release notes template

```markdown
## vX.Y.Z

### Added
-

### Changed
-

### Fixed
-

**Docker:** `docker pull ghcr.io/udayramageri09/cloud-pulse:X.Y.Z`
**Source:** `pip install git+https://github.com/udayramageri09/cloud-pulse.git@vX.Y.Z`
```

### Enabling GHCR publishing (manual, one-time, repository owner only)

The `publish` job needs `packages: write` for `GITHUB_TOKEN`. If it fails with a `403`:

1. Repository **Settings -> Actions -> General -> Workflow permissions** -- select "Read and write
   permissions".
2. After the first successful publish, the new package appears under the repository's **Packages**
   tab; its visibility (public/private) is set there and defaults to private.

This project does not claim an image is published until that workflow run is green -- a workflow
file existing is not the same as a published artifact.

## Cleanup

```bash
docker compose down --remove-orphans   # stop and remove the failure-simulation lab
docker image rm cloudpulse:local       # remove a locally built CLI image
docker image rm ghcr.io/udayramageri09/cloud-pulse:latest   # remove a pulled release image
```

No persistent volumes, databases, or state are created by anything in this project.
