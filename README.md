<p align="center">
  <img src="assets/banner.svg" alt="CloudPulse - Linux & Network Diagnostics Toolkit" width="100%"/>
</p>

<p align="center">
  <a href="https://github.com/udayramageri09/cloud-pulse/actions/workflows/ci.yml"><img src="https://github.com/udayramageri09/cloud-pulse/actions/workflows/ci.yml/badge.svg" alt="CI status"></a>
  <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python 3.10+">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-informational" alt="MIT License"></a>
</p>

CloudPulse is a lightweight Python CLI for first-response Linux and network diagnostics -- the
checks a Support/SRE engineer runs in the first few minutes of an incident. Pure standard library,
no dependencies.

## Demo

<!-- Uploaded to YouTube? Replace the line below with: [![Watch the demo](https://img.youtube.com/vi/VIDEO_ID/maxresdefault.jpg)](https://youtu.be/VIDEO_ID) -->

<p align="center">
  <video src="demo-video/cloudpulse-demo.mp4" controls width="720">
  </video>
</p>

<p align="center"><a href="demo-video/cloudpulse-demo.mp4">cloudpulse-demo.mp4</a> -- 2:27, walks through the CLI, a real Docker failure lab (500/503/504), and the incident report format.</p>

## Features

- **Host diagnostics** -- CPU, memory, disk, uptime, top processes (Linux `/proc`, no `psutil`)
- **Network diagnostics** -- DNS, TCP, HTTP/HTTPS, each with a timeout and clean error handling
- **Structured incident reports** -- severity, observed symptom, and next steps, as text or JSON
- **A real failure lab** -- Docker Compose environment reproducing 500/503/504 scenarios
- **Tested & CI'd** -- 13 passing tests, GitHub Actions on every push, a non-root Docker image

## Quick start

```bash
python -m pip install -e .
cloudpulse --dns example.com --tcp example.com:443 --url https://example.com
```

```text
CloudPulse Incident Report
Overall status: HEALTHY
[INFO] dns (example.com) - addresses=['104.20.23.154', ...], duration_ms=13.3
[INFO] http (https://example.com) - http_status=200, duration_ms=42.94
```

Try the failure lab:

```bash
./simulation/lab.sh up          # or lab.ps1 on Windows
./simulation/lab.sh stop-app    # cloudpulse now reports a 504, verified live
```

## Learn more

| | |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Design decisions and why checks/reporting are separate modules |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Docker image, GHCR, Codespaces, releases |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Every lab scenario, with real logs |
| [INTERVIEW_PREPARATION.md](INTERVIEW_PREPARATION.md) | 20+ Q&A on the engineering behind this |
| [screenshots/](screenshots/) | Genuine captured CLI/lab/test output |
| [CHANGELOG.md](CHANGELOG.md) | What's shipped |

## License

[MIT](LICENSE)
