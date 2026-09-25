"""Composite a BizHawk video dump with a live "AI controller" panel on the right.

Usage: python render_overlay.py <name>
Reads logs/<name>.inputs.txt, logs/<name>.events.txt, logs/<name>.trace.txt, video/<name>.mkv
Writes video/<name>_overlay.mp4
"""
from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HARNESS = Path(__file__).resolve().parent
LOGS, VIDEO = HARNESS / "logs", HARNESS / "video"
FONTS = Path(r"C:\Windows\Fonts")

W, H = 1280, 720
SCALE = 3
GW, GH = 256 * SCALE, 224 * SCALE          # 768 x 672
GX, GY = 0, (H - GH) // 2
PX, PW = GW, W - GW                        # panel at x=768, 512 wide
FPS = "60.0988"
NES_FPS = 60.0988

BG = (9, 12, 18)
PANEL_BG = (13, 17, 24)
GRID = (22, 28, 38)
DIM = (90, 100, 115)
TEXT = (200, 208, 218)
ACCENT = (255, 204, 0)        # Zelda gold
GREEN = (80, 230, 120)
RED = (235, 70, 70)
BLUE = (90, 160, 255)

MODES = {0x00: "TITLE", 0x01: "FILE SELECT", 0x02: "TRANSITION", 0x03: "SCREEN WIPE", 0x04: "STAIRS OUT",
         0x05: "NORMAL PLAY", 0x06: "PRE-SCROLL", 0x07: "SCROLLING", 0x0A: "LEAVING CAVE", 0x0B: "IN CAVE",
         0x0E: "REGISTER", 0x0F: "ELIMINATION", 0x10: "STAIRS IN"}


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / name), size)


F_TITLE = font("consolab.ttf", 22)
F_BIG = font("consolab.ttf", 17)
F_TEXT = font("consola.ttf", 16)
F_SMALL = font("consola.ttf", 13)
F_FEED = font("consola.ttf", 13)


def load_logs(name: str):
    inputs = [tuple(b for b in l.split(",") if b) for l in (LOGS / f"{name}.inputs.txt").read_text().splitlines()
              if not l.startswith("#")]
    events = []
    for l in (LOGS / f"{name}.events.txt").read_text().splitlines():
        fr, _, txt = l.partition("\t")
        events.append((int(fr), txt))
    trace = {}
    for l in (LOGS / f"{name}.trace.txt").read_text().splitlines():
        fr, btn, state = l.split("\t")
        kv = {k: int(v) for k, _, v in (t.partition("=") for t in state.split())}
        trace[int(fr)] = kv
    return inputs, events, trace


def fmt_time(frame: int) -> str:
    t = frame / NES_FPS
    return f"{int(t // 60):02d}:{t % 60:06.3f}"


def hearts(kv) -> str:
    full = kv["hp"] & 0x0F
    frac = kv["hpfrac"]
    cur = full + (1.0 if frac >= 0x80 else 0.5 if frac > 0 else 0.0)
    return f"{cur:g}/{(kv['hp'] >> 4) + 1}"


def draw_controller(d: ImageDraw.ImageDraw, x: int, y: int, held: set[str]):
    """A stylised NES pad, 240x90, with pressed inputs lit."""
    def c(on): return ACCENT if on else (40, 48, 60)
    # body
    d.rounded_rectangle((x, y, x + 240, y + 90), radius=8, fill=(30, 36, 46), outline=(60, 70, 85))
    # d-pad
    cx, cy, a = x + 45, y + 45, 12
    d.rectangle((cx - a, cy - 3 * a, cx + a, cy + 3 * a), fill=(50, 58, 70))
    d.rectangle((cx - 3 * a, cy - a, cx + 3 * a, cy + a), fill=(50, 58, 70))
    d.rectangle((cx - a, cy - 3 * a, cx + a, cy - a), fill=c("Up" in held))
    d.rectangle((cx - a, cy + a, cx + a, cy + 3 * a), fill=c("Down" in held))
    d.rectangle((cx - 3 * a, cy - a, cx - a, cy + a), fill=c("Left" in held))
    d.rectangle((cx + a, cy - a, cx + 3 * a, cy + a), fill=c("Right" in held))
    # select / start
    for i, (b, lab) in enumerate((("Select", "SEL"), ("Start", "START"))):
        bx = x + 92 + i * 44
        d.rounded_rectangle((bx, y + 50, bx + 30, y + 62), radius=6, fill=c(b in held))
        d.text((bx + 15, y + 68), lab, font=F_SMALL, fill=DIM, anchor="mt")
    # B / A
    for i, b in enumerate(("B", "A")):
        bx = x + 180 + i * 34
        d.ellipse((bx, y + 28, bx + 28, y + 56), fill=c(b in held), outline=(80, 30, 30))
        d.text((bx + 14, y + 68), b, font=F_SMALL, fill=DIM, anchor="mt")


def render(name: str):
    inputs, events, trace = load_logs(name)
    n = len(inputs)
    src = VIDEO / f"{name}.mkv"
    out = VIDEO / f"{name}_overlay.mp4"

    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(src), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                           stdout=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", FPS, "-i", "-", "-i", str(src), "-map", "0:v", "-map", "1:a?",
                            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                            "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)], stdin=subprocess.PIPE)

    base = Image.new("RGB", (W, H), BG)
    bd = ImageDraw.Draw(base)
    bd.rectangle((PX, 0, W, H), fill=PANEL_BG)
    for gy in range(0, H, 24):
        bd.line((PX, gy, W, gy), fill=GRID)
    bd.line((PX, 0, PX, H), fill=(40, 48, 60), width=2)
    bd.text((PX + 16, 14), "AI CONTROLLER", font=F_TITLE, fill=ACCENT)
    bd.text((PX + 16, 44), "OBJECTIVE  /  WHY", font=F_SMALL, fill=DIM)
    bd.text((PX + 16, 214), "INPUT", font=F_SMALL, fill=DIM)
    bd.text((PX + 16, 334), "GAME STATE (read from RAM)", font=F_SMALL, fill=DIM)
    bd.text((PX + 16, 434), "FRAME STREAM", font=F_SMALL, fill=DIM)

    frame_bytes = 256 * 224 * 3
    # live session dumps carry one extra frame from launch; align the video to the stepped frames
    total = int(subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
                                "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", str(src)],
                               capture_output=True, text=True).stdout.strip() or n)
    for _ in range(max(0, total - n)):
        dec.stdout.read(frame_bytes)
    # One objective on screen at a time, each with a minimum dwell: seventeen segments are shorter
    # than two seconds, and a caption that flashes past is worse than no caption. Identical
    # consecutive objectives merge, so one thought spans a corridor instead of blinking per room.
    #
    # The dwell used to be enforced by pushing the NEXT caption later (each one held 90 frames). After a burst of
    # short segments the panel ran seconds behind the game and then "caught up" - the owner saw it: "a screen or
    # two away from where you actually are". Worst of all were route steps that are skipped at run time (Level 4's
    # ring shortcut when Link is a bomb short): each lasts a few frames, and each still claimed its 90, so the
    # panel described bombing walls Link never went near. Now a caption always starts on its own frame, and one
    # whose segment is over within half a second is not shown at all.
    timeline: list[tuple[int, str, str, str]] = []
    prev_head = ""
    for i, (fr, txt) in enumerate(events):
        head, _, why = txt.partition("||")
        if timeline and head == timeline[-1][1] and why == timeline[-1][2]:
            continue
        nxt = events[i + 1][0] if i + 1 < len(events) else fr + 10 ** 6
        if nxt - fr < 30:
            continue
        timeline.append((max(fr - 1, 0), head, why, prev_head))
        prev_head = head
    ti = -1

    feed: list[str] = []
    k = 0
    while True:
        raw = dec.stdout.read(frame_bytes)
        if len(raw) < frame_bytes or k >= n:
            break
        game = Image.frombuffer("RGB", (256, 224), raw).resize((GW, GH), Image.NEAREST)
        im = base.copy()
        im.paste(game, (GX, GY))
        d = ImageDraw.Draw(im)

        held = set(inputs[k])
        kv = trace.get(k + 1, trace.get(k, {}))
        while ti + 1 < len(timeline) and timeline[ti + 1][0] <= k:
            ti += 1

        # header: frame / time
        d.text((W - 16, 18), f"frame {k + 1:05d}   {fmt_time(k + 1)}", font=F_TEXT, fill=TEXT, anchor="rt")

        # Objective and reason. Neither fades with age: this is what the bot is doing RIGHT NOW, and
        # a dimming objective reads as a stale one. The previous objective sits below it in grey.
        if ti >= 0:
            _, head, why, last = timeline[ti]
            y = 64
            for line in textwrap.wrap(head, 40)[:2]:
                d.text((PX + 16, y), line, font=F_BIG, fill=ACCENT)
                y += 22
            y = max(y + 4, 96)
            for line in textwrap.wrap(why, 54)[:3]:
                d.text((PX + 16, y), line, font=F_TEXT, fill=TEXT)
                y += 18
            if last:
                d.text((PX + 16, 178), "before this: " + last[:44], font=F_SMALL, fill=DIM)
        d.line((PX + 16, 200, W - 16, 200), fill=GRID)

        # controller + textual buttons
        draw_controller(d, PX + 16, 232, held)
        btxt = " + ".join(inputs[k]) if inputs[k] else "(none)"
        d.text((PX + 270, 250), "HOLDING", font=F_SMALL, fill=DIM)
        d.text((PX + 270, 268), btxt, font=F_BIG, fill=ACCENT if inputs[k] else DIM)

        # state
        if kv:
            mode = kv["mode"]
            rows = [("MODE", f"{mode:02X} {MODES.get(mode, '?')}"), ("ROOM", f"{kv['room']:02X}  level {kv['level']}"),
                    ("LINK", f"x={kv['x']:3d}  y={kv['y']:3d}  dir={kv['dir']}"),
                    ("HEARTS", hearts(kv)), ("SWORD", str(kv["sword"])), ("RUPEES", str(kv["rupees"]))]
            for i, (lab, val) in enumerate(rows):
                cx = PX + 16 + (i % 2) * 250
                cy = 352 + (i // 2) * 22
                d.text((cx, cy), lab, font=F_SMALL, fill=DIM)
                d.text((cx + 70, cy), val, font=F_TEXT, fill=GREEN if lab == "SWORD" and kv["sword"] else TEXT)

        # raw feed: one line per frame, newest at the bottom
        feed.append(f"f{k + 1:05d} {btxt[:11]:<11} m={kv.get('mode', 0):02X} r={kv.get('room', 0):02X} "
                    f"({kv.get('x', 0):3d},{kv.get('y', 0):3d}) sw={kv.get('sword', 0)} lag={kv.get('lag', 0)}")
        lines = feed[-17:]
        for i, line in enumerate(lines):
            age = len(lines) - 1 - i
            shade = max(70, 220 - age * 10)
            d.text((PX + 16, 454 + i * 15), line, font=F_FEED, fill=(shade, shade, shade) if age else GREEN)

        enc.stdin.write(im.tobytes())
        k += 1
        if k % 300 == 0:
            print(f"  {k}/{n} frames", flush=True)

    dec.stdout.close()
    enc.stdin.close()
    enc.wait()
    print("wrote", out)
    return out


if __name__ == "__main__":
    render(sys.argv[1] if len(sys.argv) > 1 else "milestone1")
