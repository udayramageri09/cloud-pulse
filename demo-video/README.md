# Demo video

`cloudpulse-demo.mp4` (1920x1080, 30fps) walks through the CLI, the failure-simulation lab, and
the incident report format in roughly 2:30-3:00.

## What this actually is, honestly

This environment has no screen recorder and no GUI access, so this is **not** a literal screen
recording. It is a real, automatically rendered video built from:

- **Genuine captured output** for every scene showing CLI/lab/test results -- each one is a PNG
  already produced from an actual run (see [`screenshots/README.md`](../screenshots/README.md)),
  restyled as a terminal window, never retyped or fabricated.
- **Synthesized narration** via Windows SAPI (`pyttsx3`, "Microsoft David Desktop" voice) -- a
  real, intelligible voice, but a text-to-speech one, not a human voice actor.
- **Real video encoding** via `ffmpeg` (bundled through `imageio-ffmpeg`, no system install
  needed) -- actual H.264/AAC output, actual crossfade transitions (`xfade`/`acrossfade`), and a
  slow Ken-Burns-style zoom (`zoompan`) on each otherwise-static frame for motion.

If you want a literal screen recording with a human voiceover instead, [recording-checklist.md](recording-checklist.md)
gives the exact commands and order to record it yourself, and [narration.md](narration.md) is a
ready-to-read script (or write your own).

## Rebuilding it

```bash
pip install pillow pyttsx3 pywin32 imageio-ffmpeg   # Windows only (pyttsx3 uses SAPI)
python demo-video/tools/render_frames.py            # regenerates screenshots/*.png from captures/
python demo-video/tools/build_video.py              # synthesizes narration, builds, and crossfades the final video
```

`build_video.py` reads real text from `../captures/*.txt` and real PNGs from `../screenshots/`,
synthesizes narration per scene, sizes each scene's on-screen duration to that narration's actual
measured length, and crossfades all 12 scenes into `cloudpulse-demo.mp4`. Nothing is hand-timed or
guessed -- see `tools/build_video.py` for the exact pipeline.

**Platform note:** `pyttsx3`'s SAPI backend is Windows-only. On Linux/macOS, swap `synthesize()` in
`build_video.py` for any TTS that can write a WAV file (e.g. `espeak-ng`, `say` on macOS), or skip
narration synthesis entirely and pass pre-recorded WAV files for each scene -- the rest of the
pipeline (frame generation, zoompan, crossfade) is platform-independent since it runs through
`imageio-ffmpeg`.

## Contents

- [storyboard.md](storyboard.md) -- scene-by-scene visual plan.
- [narration.md](narration.md) -- the exact narration text used.
- [asset-plan.md](asset-plan.md) -- where every visual/audio asset actually comes from.
- [recording-checklist.md](recording-checklist.md) -- steps to record a real screencast version instead.
- `tools/render_frames.py`, `tools/build_video.py` -- the actual render pipeline.
- `cloudpulse-demo.mp4` -- the rendered output.
