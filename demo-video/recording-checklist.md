# Recording checklist

For re-recording this with a real screen capture and a human voiceover instead of the generated
version in this directory (see [README.md](README.md) for why the shipped version is generated
rather than screen-recorded).

## Before recording

- [ ] Reset the lab to a clean baseline: `./simulation/lab.sh reset`.
- [ ] Confirm the baseline is actually healthy: `cloudpulse --url http://127.0.0.1:8080/health --tcp 127.0.0.1:8080` exits 0.
- [ ] Set your terminal to a dark theme, Consolas or Cascadia Code, 20-24pt, 120-column width.
- [ ] Close anything that might pop up a notification during recording.
- [ ] Have [narration.md](narration.md) open on a second monitor or printed, to read from (or
  write your own -- it only needs to describe what's actually on screen).

## Recording order (matches [storyboard.md](storyboard.md))

- [ ] Scene 1-2: record narration only, or a static title slide, for the intro.
- [ ] Scene 3-4: `cloudpulse --dns example.com --tcp example.com:443 --url https://example.com --verbose`
  against your own network (host-only, no lab needed).
- [ ] Scene 5: `docker compose ps` right after `./simulation/lab.sh up`.
- [ ] Scene 6: `./simulation/lab.sh stop-app`, then
  `cloudpulse --url http://127.0.0.1:8080/health --tcp 127.0.0.1:8080 --verbose`. Record the real
  wait for the response -- it takes about 3 seconds in this lab's configuration (see
  [TROUBLESHOOTING.md](../TROUBLESHOOTING.md)); don't cut that gap, it's the point.
- [ ] Scene 7: `docker compose logs proxy --tail 20` in the same terminal.
- [ ] Scene 8: `./simulation/lab.sh start-app`, then
  `cloudpulse --url http://127.0.0.1:8080/fail --verbose`.
- [ ] Scene 9: `./simulation/lab.sh unhealthy`, then
  `cloudpulse --url http://127.0.0.1:8080/health --verbose`.
- [ ] Scene 10: `./simulation/lab.sh healthy`, then
  `cloudpulse --format json --dns example.com --tcp 127.0.0.1:8080 --url http://127.0.0.1:8080/health`.
- [ ] Scene 11: `python -m unittest discover -s tests -v`.
- [ ] Scene 12: closing slide / sign-off.

## After recording

- [ ] `./simulation/lab.sh down` to tear the lab back down.
- [ ] Trim dead air at the start/end of each clip, but keep the real response-time gap in scene 6.
- [ ] Export at 1920x1080, 30fps, matching this directory's generated version so either can drop
  into the README's video link.
