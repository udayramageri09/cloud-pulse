# Asset plan

Everything the rendered video needs, and where each piece actually comes from -- no asset here is
stock footage or a generic template.

| Asset | Source | Notes |
|---|---|---|
| Title/closing cards | `tools/render_frames.py::render_title_card` | Generated: navy/charcoal gradient, white headline, teal pulse-line accent -- matches `assets/banner.svg`'s palette |
| Problem-framing card | `tools/render_frames.py::render_bullet_card` | Generated bullet list, same palette |
| System/network diagnostics frames | `tools/render_frames.py::render_terminal`, fed lines sliced from `captures/01_healthy.txt` | Real CLI output, restyled as a terminal window |
| Lab/failure-scenario frames | `screenshots/*.png` (already rendered from `captures/*.txt`) | Reused directly -- see [`screenshots/README.md`](../screenshots/README.md) |
| Narration audio | Windows SAPI via `pyttsx3`, "Microsoft David Desktop" voice, rate 165 | See [narration.md](narration.md) for exact text |
| Fonts | Consolas (terminal text), Segoe UI (titles) -- both already present on Windows | No external font downloads |
| Color palette | Deep navy (`#0b1220`), charcoal (`#111827`), white (`#f5f7fa`), teal accent (`#2dd4bf`) | Matches `assets/banner.svg` / `assets/logo.svg` |
| Video/audio encoding | `imageio-ffmpeg` (bundles a real ffmpeg binary, no system install needed) | `libx264` + `aac`, 1920x1080, 30fps |

## What this plan deliberately does not include

- Stock footage, generic b-roll, or any third-party video clip -- every frame is either generated
  from this project's own palette or a genuine captured screenshot.
- A human-recorded voiceover -- see [README.md](README.md) for the honest tradeoff and how to
  swap one in.
- Background music -- adding royalty-free music would be straightforward (`-i music.mp3` mixed
  under the narration track at render time) but was left out to keep the asset list to things that
  are either generated here or genuinely captured, with nothing externally sourced.
