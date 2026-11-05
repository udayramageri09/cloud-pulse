"""Builds demo-video/cloudpulse-demo.mp4 from real captured CLI/lab output.

Pipeline: synthesize narration per scene with Windows SAPI (pyttsx3), size each
scene's on-screen duration to its narration's actual length, render each scene
as a slow Ken-Burns-style zoom clip (ffmpeg zoompan) with its narration muxed
in, then crossfade all scenes together into one video with ffmpeg's xfade/
acrossfade filters. No step here fabricates on-screen text -- every screenshot
scene reuses a PNG already rendered from a genuine capture.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg
import pyttsx3

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_frames import render_bullet_card, render_terminal, render_title_card  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
CAPTURES = REPO / "captures"
SCREENSHOTS = REPO / "screenshots"
BUILD = REPO / "demo-video" / "build"
OUT_VIDEO = REPO / "demo-video" / "cloudpulse-demo.mp4"

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
FPS = 30
SIZE = "1920x1080"
XFADE_DUR = 0.6
TAIL_PAD = 1.0  # extra seconds of frame held after narration ends, before the next crossfade


def synthesize(text: str, out_wav: Path, rate: int = 140) -> float:
    engine = pyttsx3.init()
    engine.setProperty("rate", rate)
    voices = engine.getProperty("voices")
    engine.setProperty("voice", voices[0].id)  # David
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    engine.save_to_file(text, str(out_wav))
    engine.runAndWait()
    return probe_duration(out_wav)


def probe_duration(path: Path) -> float:
    result = subprocess.run([FFMPEG, "-i", str(path)], capture_output=True, text=True)
    match = re.search(r"Duration: (\d+):(\d+):([\d.]+)", result.stderr)
    if not match:
        raise RuntimeError(f"could not read duration of {path}:\n{result.stderr[-500:]}")
    h, m, s = match.groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def build_scene_clip(image: Path, audio: Path, duration: float, out_mp4: Path) -> None:
    total_frames = int(duration * FPS)
    zoompan = (
        f"scale=1920:1080,"
        f"zoompan=z='min(zoom+0.0006,1.08)':d={total_frames}:s={SIZE}:fps={FPS}"
    )
    cmd = [
        FFMPEG, "-y",
        "-loop", "1", "-i", str(image),
        "-i", str(audio),
        "-t", f"{duration:.3f}",
        "-vf", zoompan,
        "-af", "apad",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        str(out_mp4),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-3000:])


def crossfade_concat(clips: list[Path], durations: list[float], out_path: Path) -> None:
    n = len(clips)
    inputs: list[str] = []
    for c in clips:
        inputs += ["-i", str(c)]

    v_labels = [f"{i}:v" for i in range(n)]
    a_labels = [f"{i}:a" for i in range(n)]
    filters = []
    cum = durations[0]
    prev_v, prev_a = v_labels[0], a_labels[0]
    for i in range(1, n):
        offset = cum - XFADE_DUR
        vout = f"v{i}"
        aout = f"a{i}"
        filters.append(
            f"[{prev_v}][{v_labels[i]}]xfade=transition=fade:duration={XFADE_DUR}:offset={offset:.3f}[{vout}]"
        )
        filters.append(
            f"[{prev_a}][{a_labels[i]}]acrossfade=d={XFADE_DUR}[{aout}]"
        )
        prev_v, prev_a = vout, aout
        cum += durations[i] - XFADE_DUR

    filter_complex = ";".join(filters)
    cmd = [
        FFMPEG, "-y", *inputs,
        "-filter_complex", filter_complex,
        "-map", f"[{prev_v}]", "-map", f"[{prev_a}]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-c:a", "aac", "-b:a", "128k",
        str(out_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-3000:])


def main() -> None:
    BUILD.mkdir(parents=True, exist_ok=True)

    healthy_lines = (CAPTURES / "01_healthy.txt").read_text(encoding="utf-8").splitlines()
    header = healthy_lines[0:6]
    system_lines = healthy_lines[7:14]
    network_lines = healthy_lines[14:17]

    system_frame = BUILD / "frame_system.png"
    render_terminal(header + [""] + system_lines, system_frame, title="cloudpulse --verbose", prompt=None)

    network_frame = BUILD / "frame_network.png"
    render_terminal(header + [""] + network_lines, network_frame, title="cloudpulse --dns --tcp --url", prompt=None)

    title_frame = BUILD / "frame_title.png"
    render_title_card(
        "CloudPulse",
        "LINUX & NETWORK DIAGNOSTICS TOOLKIT",
        title_frame,
        footer="Investigate. Diagnose. Understand.",
    )

    problem_frame = BUILD / "frame_problem.png"
    render_bullet_card(
        "When something breaks, every minute counts",
        [
            "Server unavailable",
            "DNS resolution failure",
            "Connection refused",
            "HTTP 500 / 502 / 503 / 504",
        ],
        problem_frame,
    )

    closing_frame = BUILD / "frame_closing.png"
    render_title_card(
        "CloudPulse",
        "A PRACTICAL APPROACH TO LINUX & NETWORK TROUBLESHOOTING",
        closing_frame,
        footer="Python | Linux | Networking | Docker   -   github.com/udayramageri09/cloud-pulse",
    )

    scenes = [
        (title_frame, "CloudPulse is a lightweight Python toolkit for first response Linux and network diagnostics."),
        (problem_frame, "When something breaks, the first few minutes matter most. Is the host healthy? Can the network even reach the target? CloudPulse automates asking those questions, consistently, every time."),
        (system_frame, "It starts with the host itself: C P U, memory, disk usage, uptime, and the top processes by memory, read straight from Linux proc, with no third party dependencies."),
        (network_frame, "Then the network: D N S resolution, a T C P connection, and an H T T P health check, each with its own timeout, so a hung connection never hangs the whole report."),
        (SCREENSHOTS / "docker-compose-ps.png", "To prove it against real failures, CloudPulse ships its own lab: a demo application behind an Nginx reverse proxy, running locally in Docker."),
        (SCREENSHOTS / "scenario-504-upstream-down.png", "Stop the application, and the proxy can still be reached, but it can no longer reach its upstream. CloudPulse reports that precisely: T C P okay, H T T P critical, a gateway timeout."),
        (SCREENSHOTS / "nginx-logs.png", "The real Nginx log confirms it: a connection attempt to the stopped container's address that simply timed out."),
        (SCREENSHOTS / "scenario-500.png", "A different failure: the application is running, but one route deliberately returns an internal server error. CloudPulse captures the five hundred status directly from the application."),
        (SCREENSHOTS / "scenario-503-unhealthy.png", "And a third case: the application is up, but reports itself not ready. A five oh three, distinct from both the timeout and the application error before it."),
        (SCREENSHOTS / "sample-incident-json.png", "Every run also produces a structured incident report: an incident ID, host information, a severity for each check, and suggested next steps. Never a guessed root cause."),
        (SCREENSHOTS / "test-suite.png", "All of this is backed by a real test suite, continuous integration, and a non root Docker image, built to be read end to end, not just demoed."),
        (closing_frame, "CloudPulse: a practical approach to Linux and network troubleshooting. Thanks for watching."),
    ]

    clips: list[Path] = []
    durations: list[float] = []
    for i, (frame, narration) in enumerate(scenes):
        wav = BUILD / f"scene_{i:02d}.wav"
        dur = synthesize(narration, wav)
        total_dur = dur + TAIL_PAD
        clip = BUILD / f"scene_{i:02d}.mp4"
        build_scene_clip(frame, wav, total_dur, clip)
        clips.append(clip)
        durations.append(total_dur)
        print(f"scene {i:02d}: {dur:.1f}s narration -> {total_dur:.1f}s clip ({frame.name})")

    total_runtime = sum(durations) - XFADE_DUR * (len(durations) - 1)
    print(f"estimated total runtime: {total_runtime:.1f}s")

    crossfade_concat(clips, durations, OUT_VIDEO)
    print(f"wrote {OUT_VIDEO}")


if __name__ == "__main__":
    main()
