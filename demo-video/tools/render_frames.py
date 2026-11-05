"""Renders real captured CLI/test/lab output as styled PNG frames.

Used for both the screenshots/ directory (Phase 7) and the demo video's scene
frames (Phase 6). Takes no fabricated text -- every body it renders comes from
a file actually captured by running the real CLI, test suite, or Docker lab.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT_DIR = Path("C:/Windows/Fonts")
MONO = FONT_DIR / "consola.ttf"
MONO_BOLD = FONT_DIR / "consolab.ttf"
SANS = FONT_DIR / "segoeui.ttf"
SANS_BOLD = FONT_DIR / "segoeuib.ttf"
SANS_LIGHT = FONT_DIR / "segoeuil.ttf"

BG_OUTER = (11, 18, 32)       # #0b1220 deep navy
BG_WINDOW = (17, 24, 39)      # #111827 charcoal
BORDER = (31, 41, 55)         # #1f2937
TEAL = (45, 212, 191)         # #2dd4bf accent
WHITE = (245, 247, 250)
MUTED = (154, 165, 184)
YELLOW = (250, 204, 21)
RED = (248, 113, 113)
GREEN = (74, 222, 128)
DOT_RED = (239, 68, 68)
DOT_YELLOW = (245, 158, 11)
DOT_GREEN = (34, 197, 94)


def _font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size)


def _line_color(line: str) -> tuple[int, int, int]:
    stripped = line.lstrip()
    if stripped.startswith(("Symptom:", "Next step:")):
        return MUTED
    if line.startswith(("Incident ID", "Generated", "Host:", "Overall status", "Checks:")):
        return TEAL
    if "[CRITICAL]" in line:
        return RED
    if "[WARNING]" in line:
        return YELLOW
    if " ... ok" in line:
        return GREEN
    if line.startswith(("[INFO]", "[OK]")):
        return MUTED if line.startswith("[INFO]") else GREEN
    return WHITE


def render_terminal(
    lines: list[str],
    out_path: Path,
    title: str = "cloudpulse",
    width: int = 1920,
    height: int = 1080,
    font_size: int = 26,
    wrap_at: int = 110,
    prompt: str | None = None,
) -> None:
    img = Image.new("RGB", (width, height), BG_OUTER)
    draw = ImageDraw.Draw(img)

    margin = 48
    win = (margin, margin, width - margin, height - margin)
    draw.rounded_rectangle(win, radius=18, fill=BG_WINDOW, outline=BORDER, width=2)

    bar_h = 56
    draw.rounded_rectangle(
        (win[0], win[1], win[2], win[1] + bar_h), radius=18, fill=(22, 30, 46)
    )
    draw.rectangle((win[0], win[1] + bar_h - 18, win[2], win[1] + bar_h), fill=(22, 30, 46))
    for i, color in enumerate((DOT_RED, DOT_YELLOW, DOT_GREEN)):
        cx = win[0] + 30 + i * 28
        cy = win[1] + bar_h // 2
        draw.ellipse((cx - 7, cy - 7, cx + 7, cy + 7), fill=color)
    title_font = _font(SANS, 20)
    draw.text((win[0] + 130, win[1] + bar_h // 2 - 10), title, font=title_font, fill=MUTED)

    body_font = _font(MONO, font_size)
    bold_font = _font(MONO_BOLD, font_size)
    x = win[0] + 36
    y = win[1] + bar_h + 28
    line_h = int(font_size * 1.5)

    rendered: list[str] = []
    for raw in lines:
        wrapped = textwrap.wrap(raw, width=wrap_at, subsequent_indent="      ") or [""]
        rendered.extend(wrapped)

    if prompt:
        draw.text((x, y), prompt, font=bold_font, fill=TEAL)
        y += line_h + int(line_h * 0.4)

    for line in rendered:
        if y > win[3] - 60:
            break
        color = _line_color(line)
        font = bold_font if line.startswith(("[CRITICAL]", "[WARNING]")) else body_font
        draw.text((x, y), line, font=font, fill=color)
        y += line_h

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)


def render_title_card(
    headline: str,
    subhead: str,
    out_path: Path,
    width: int = 1920,
    height: int = 1080,
    footer: str | None = None,
) -> None:
    img = Image.new("RGB", (width, height), BG_OUTER)
    draw = ImageDraw.Draw(img)

    for i in range(height):
        t = i / height
        r = int(11 + (18 - 11) * t)
        g = int(18 + (26 - 18) * t)
        b = int(32 + (43 - 32) * t)
        draw.line((0, i, width, i), fill=(r, g, b))

    headline_font = _font(SANS_BOLD, 108)
    sub_font = _font(SANS_LIGHT, 34)

    bbox = draw.textbbox((0, 0), headline, font=headline_font)
    hw = bbox[2] - bbox[0]
    hx = (width - hw) // 2
    hy = height // 2 - 110
    draw.text((hx, hy), headline, font=headline_font, fill=WHITE)

    sub_bbox = draw.textbbox((0, 0), subhead, font=sub_font)
    sw = sub_bbox[2] - sub_bbox[0]
    draw.text(((width - sw) // 2, hy + 150), subhead, font=sub_font, fill=MUTED)

    # Pulse-line accent motif
    py = hy + 230
    pts = [
        (width // 2 - 420, py), (width // 2 - 260, py), (width // 2 - 220, py - 40),
        (width // 2 - 180, py + 60), (width // 2 - 140, py), (width // 2 + 420, py),
    ]
    draw.line(pts, fill=TEAL, width=4, joint="curve")
    draw.ellipse((width // 2 - 180 - 7, py + 60 - 7, width // 2 - 180 + 7, py + 60 + 7), fill=TEAL)

    if footer:
        footer_font = _font(SANS, 26)
        fb = draw.textbbox((0, 0), footer, font=footer_font)
        fw = fb[2] - fb[0]
        draw.text(((width - fw) // 2, height - 100), footer, font=footer_font, fill=MUTED)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)


def render_bullet_card(
    headline: str,
    bullets: list[str],
    out_path: Path,
    width: int = 1920,
    height: int = 1080,
) -> None:
    img = Image.new("RGB", (width, height), BG_OUTER)
    draw = ImageDraw.Draw(img)
    for i in range(height):
        t = i / height
        r = int(11 + (18 - 11) * t)
        g = int(18 + (26 - 18) * t)
        b = int(32 + (43 - 32) * t)
        draw.line((0, i, width, i), fill=(r, g, b))

    headline_font = _font(SANS_BOLD, 56)
    bullet_font = _font(MONO, 40)

    hb = draw.textbbox((0, 0), headline, font=headline_font)
    hw = hb[2] - hb[0]
    hy = 220
    draw.text(((width - hw) // 2, hy), headline, font=headline_font, fill=WHITE)

    y = hy + 140
    for bullet in bullets:
        text = f"x  {bullet}"
        bb = draw.textbbox((0, 0), text, font=bullet_font)
        bw = bb[2] - bb[0]
        draw.text(((width - bw) // 2, y), text, font=bullet_font, fill=RED)
        y += 76

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)


def slice_lines(src: Path, start: int, end: int) -> list[str]:
    lines = src.read_text(encoding="utf-8", errors="replace").splitlines()
    return lines[start:end]


if __name__ == "__main__":
    repo = Path(__file__).resolve().parents[2]
    captures = repo / "captures"
    screenshots = repo / "screenshots"

    jobs = [
        ("00_tests.txt", "cloudpulse - python -m unittest discover -s tests -v", "test-suite.png", "$ python -m unittest discover -s tests -v", 21),
        ("01_healthy.txt", "cloudpulse --dns example.com --tcp 127.0.0.1:18080 --url http://127.0.0.1:18080/health --verbose", "healthy-report.png", "$ cloudpulse --dns example.com --tcp 127.0.0.1:18080 --url http://127.0.0.1:18080/health --verbose", None),
        ("02_app_error_500.txt", "cloudpulse --url http://127.0.0.1:18080/fail --verbose", "scenario-500.png", "$ cloudpulse --url http://127.0.0.1:18080/fail --verbose", None),
        ("03_upstream_504.txt", "cloudpulse --url http://127.0.0.1:18080/health --tcp 127.0.0.1:18080 --verbose", "scenario-504-upstream-down.png", "$ cloudpulse --url http://127.0.0.1:18080/health --tcp 127.0.0.1:18080 --verbose", None),
        ("04_unhealthy_503.txt", "cloudpulse --url http://127.0.0.1:18080/health --verbose", "scenario-503-unhealthy.png", "$ cloudpulse --url http://127.0.0.1:18080/health --verbose", None),
        ("06_compose_ps.txt", "docker compose ps", "docker-compose-ps.png", "$ docker compose ps", None),
        ("07_proxy_logs.txt", "docker compose logs proxy --tail 20", "nginx-logs.png", "$ docker compose logs proxy --tail 20", 20),
    ]

    for src_name, title, out_name, prompt, font_size in jobs:
        src = captures / src_name
        if not src.exists():
            print(f"skip (missing): {src}")
            continue
        text = src.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        kwargs = {"font_size": font_size} if font_size else {}
        render_terminal(lines, screenshots / out_name, title=title, prompt=prompt, **kwargs)
        print(f"wrote {screenshots / out_name}")

    # JSON sample rendered too, pretty as-is
    json_src = captures / "05_sample_incident.json"
    if json_src.exists():
        lines = json_src.read_text(encoding="utf-8").splitlines()
        render_terminal(
            lines,
            screenshots / "sample-incident-json.png",
            title="cloudpulse --format json",
            font_size=20,
            wrap_at=140,
            prompt="$ cloudpulse --format json --dns example.com --tcp 127.0.0.1:18080 --url http://127.0.0.1:18080/health",
        )
        print(f"wrote {screenshots / 'sample-incident-json.png'}")
