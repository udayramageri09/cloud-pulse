# Storyboard

12 scenes, 1920x1080, 30fps, crossfade transitions (0.6s), each scene's on-screen duration sized
to its narration's actual length (not fixed timestamps -- see [narration.md](narration.md) for
exact wording). Approximate running order and feel below; the rendered video's real per-scene
timing comes from `demo-video/build/*.wav` durations at render time.

See [README.md](README.md) for exactly how durations were measured and the video was rendered.

| # | Visual | Source | Feel |
|---|---|---|---|
| 1 | Title card: "CloudPulse" / "LINUX & NETWORK DIAGNOSTICS TOOLKIT" / "Investigate. Diagnose. Understand." | generated title card | Clean open, pulse-line accent |
| 2 | Bullet card: "When something breaks, every minute counts" + 4 failure modes | generated bullet card | Problem framing |
| 3 | Terminal frame: system diagnostics (CPU/memory/disk/uptime/processes) | sliced from `captures/01_healthy.txt` | Real CLI output |
| 4 | Terminal frame: network diagnostics (DNS/TCP/HTTP) | sliced from `captures/01_healthy.txt` | Real CLI output |
| 5 | `docker compose ps` -- both lab containers healthy | `screenshots/docker-compose-ps.png` | Lab intro |
| 6 | App stopped -- TCP ok, HTTP 504 | `screenshots/scenario-504-upstream-down.png` | First failure, verified live |
| 7 | Real Nginx error log: `upstream timed out` | `screenshots/nginx-logs.png` | Ground-truth evidence |
| 8 | `/fail` route -- HTTP 500 | `screenshots/scenario-500.png` | Application-level failure |
| 9 | `APP_MODE=unhealthy` -- HTTP 503 | `screenshots/scenario-503-unhealthy.png` | Third distinct failure mode |
| 10 | Full JSON incident report | `screenshots/sample-incident-json.png` | Structured output |
| 11 | `python -m unittest discover -v` -- 13 passing | `screenshots/test-suite.png` | Engineering quality |
| 12 | Closing title card with GitHub URL | generated title card | Close |

Every screenshot-sourced scene (5-11) is a PNG already rendered from a real captured run (see
[`screenshots/README.md`](../screenshots/README.md)) -- the video does not re-stage or re-type any
of that output. Each clip applies a slow, subtle zoom (ffmpeg `zoompan`, scale capped at 1.08x) for
visual motion on an otherwise static frame, matching the "smooth zooms on static terminal captures"
style rather than a literal screen recording (see [README.md](README.md) for why).
