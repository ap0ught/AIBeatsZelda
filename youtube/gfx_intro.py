"""The cold open, under the owner's ad-libbed preamble (~31 s): real day-one footage of the bot playing badly -
walking into trees, dying to Darknuts, swinging at nothing - one window, then two, then a wall of twelve, each stamped
with the real time its test recording was made; a fast-forward flicker; then run 6 clearing the six-Darknut room, full
screen, at double speed, with a stopwatch. usage: python youtube/gfx_intro.py [seconds] [out.mp4]"""
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
import gfx                                   # noqa: E402
from build import render_frames               # noqa: E402

DUR = float(sys.argv[1]) if len(sys.argv) > 1 else 31.0
out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("youtube/clips_v3/intro.mp4")
out.parent.mkdir(parents=True, exist_ok=True)
# (file, start s, caption) - every one a real test recording from the first two days
CELLS = [("nav_test1", 0, "walks into the trees"), ("explore_L3", 50, "meets the Octoroks"), ("fight_test1", 0, "the Zol room"),
         ("darknut_test", 0, "swings at Bubbles"), ("seg_5b_darknuts", 1480, "five Darknuts"), ("cross_59", 5, "five Darknuts, again"),
         ("heal_chain", 5, "and again"), ("seg_5b_darknuts", 2980, "and again"), ("search_keese", 280, "the Keese corridor"),
         ("locked_door", 0, "a locked door"), ("boss_look", 0, "meets Manhandla"), ("explore_L4", 380, "the water problem")]
BUILD_END = DUR - 10.5                       # the wall is complete here; then the fast-forward and the payoff
FLASH = 1.6
F = 60.0988


def decode(path, start, n, w, h, vf=""):
    cmd = ["ffmpeg", "-v", "error", "-ss", str(start), "-i", str(path), "-frames:v", str(n), "-vf",
           (vf + "," if vf else "") + f"scale={w}:{h}:flags=neighbor", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    fr = []
    sz = w * h * 3
    while True:
        raw = p.stdout.read(sz)
        if len(raw) < sz:
            break
        fr.append(Image.frombuffer("RGB", (w, h), raw))
    p.wait()
    return fr


def stamp(path):
    t = datetime.datetime.fromtimestamp(os.path.getmtime(path))
    return t.strftime("SEP %d, %I:%M %p").replace(" 0", " ").lstrip("0")


cells = []
for name, start, cap in CELLS:
    src = Path("video") / f"{name}.mkv"
    fr = decode(src, start, int(22 * F), 256, 224)
    cells.append({"frames": fr, "cap": cap, "stamp": stamp(src)})
# the payoff: run 6's six-Darknut room (segment r8_3f), game area only, at double speed
ck = Path("logs/archive/sixth_run_20260922/checkpoints")
rows = sorted(((json.load(open(f))["frames"], f.stem[9:]) for f in ck.glob("fullgame_*.json")))
prev = 0
for fr_, n_ in rows:
    if n_ == "r8_3f":
        a, b = prev, fr_
        break
    prev = fr_
win = decode("video/sixth_run_2026-09-22/zelda_ai_run6_37m02s_overlay.mp4", a / F, b - a, 768, 672, "crop=768:672:0:24")
win_frames = b - a


def frames():
    n = gfx.nframes(DUR)
    order = list(range(len(CELLS)))
    for v in range(n):
        t = v / gfx.FPS
        im = Image.new("RGB", (gfx.W, gfx.H), gfx.BG)
        d = ImageDraw.Draw(im)
        if t < BUILD_END + FLASH:
            shown = min(len(CELLS), 1 + int(t / (BUILD_END / len(CELLS))))
            speed = 1 if t < BUILD_END else 6
            for idx in order[:shown]:
                c = cells[idx]
                j = min(len(c["frames"]) - 1, int((v - int(idx * (BUILD_END / len(CELLS)) * gfx.FPS)) * speed) % len(c["frames"]))
                x, y = (idx % 4) * 256, 12 + (idx // 4) * 232
                im.paste(c["frames"][j], (x, y))
                d.rectangle((x, y, x + 255, y + 223), outline=(40, 48, 60))
                d.rectangle((x, y, x + 118, y + 15), fill=(0, 0, 0))
                d.text((x + 3, y + 1), c["stamp"], font=gfx.F[13], fill=gfx.GOLD)
                d.rectangle((x, y + 208, x + 255, y + 223), fill=(0, 0, 0))
                d.text((x + 252, y + 209), c["cap"], font=gfx.F[13], fill=gfx.TEXT, anchor="ra")
            # right column
            d.text((1044, 24), "DAY ONE", font=gfx.FB[26], fill=gfx.GOLD)
            d.text((1044, 60), "real test recordings", font=gfx.F[13], fill=gfx.DIM)
            d.text((1044, 100), f"windows: {shown:2d}", font=gfx.F[16], fill=gfx.TEXT)
            if t >= BUILD_END:
                k = int((t - BUILD_END) / FLASH * 11) + 1
                d.rectangle((1044, 300, 1270, 420), fill=(30, 20, 0))
                d.text((1056, 312), ">> FAST FORWARD", font=gfx.FB[20], fill=gfx.GOLD)
                d.text((1056, 350), f"DAY {min(12, k)}", font=gfx.FB[44], fill=gfx.GOLD)
        else:
            k = min(win_frames - 1, int((t - BUILD_END - FLASH) * F * 2))
            im.paste(win[k], (32, 24))
            d.text((832, 60), "DAY TWELVE", font=gfx.FB[26], fill=gfx.GOLD)
            d.text((832, 100), "six Blue Darknuts", font=gfx.F[20], fill=gfx.TEXT)
            d.text((832, 130), "run 6, Level 8, uncut", font=gfx.F[16], fill=gfx.DIM)
            d.text((832, 200), f"{k / F:5.1f} s", font=gfx.FB[72], fill=gfx.GOLD)
            d.text((832, 300), "played at 2x", font=gfx.F[13], fill=gfx.DIM)
            if k >= win_frames - 1:
                d.text((832, 340), f"cleared in {win_frames / F:.1f} seconds", font=gfx.FB[20], fill=gfx.GREEN)
        yield im


render_frames(frames(), out)
print("wrote", out, "payoff", win_frames, "frames")
