"""Generated animations for the documentary half. Every one of them is drawn from the project's own data: real log
lines, real journal text, the real lookahead branches, the map decoded from the cartridge, the runs' checkpoints.

Each generator is  name(dur_seconds, **kw) -> iterator of 1280x720 RGB PIL images, one per output frame."""
from __future__ import annotations

import glob
import json
import math
import os
import re
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

H_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(H_DIR))
W, H = 1280, 720
FPS = 150247 / 2500
FONTS = Path(r"C:\Windows\Fonts")
BG = (9, 12, 18)
PANEL = (13, 17, 24)
GRID = (22, 28, 38)
DIM = (110, 120, 135)
TEXT = (210, 216, 226)
GOLD = (255, 204, 0)
GREEN = (80, 230, 120)
RED = (235, 70, 70)
BLUE = (90, 160, 255)
SAND = (214, 186, 120)


def font(size, bold=False):
    return ImageFont.truetype(str(FONTS / ("consolab.ttf" if bold else "consola.ttf")), size)


F = {s: font(s) for s in (13, 16, 18, 20, 22, 26, 30, 36, 44, 56, 72)}
FB = {s: font(s, True) for s in (16, 18, 20, 22, 26, 30, 36, 44, 56, 72, 96, 120)}


def nframes(dur):
    return max(1, int(round(dur * FPS)))


def canvas():
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    for gy in range(0, H, 24):
        d.line((0, gy, W, gy), fill=(12, 16, 23))
    return im, d


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def blend(c, a, bg=BG):
    return tuple(int(bg[i] + (c[i] - bg[i]) * max(0.0, min(1.0, a))) for i in range(3))


def wrap(text, width):
    out = []
    for para in text.split("\n"):
        out += textwrap.wrap(para, width) or [""]
    return out


def header(d, title, sub=None):
    d.text((60, 44), title, font=FB[36], fill=GOLD)
    if sub:
        d.text((62, 92), sub, font=F[18], fill=DIM)
    d.line((60, 124, W - 60, 124), fill=(40, 48, 60), width=2)


def hold(im, n):
    for _ in range(n):
        yield im


# ------------------------------------------------------------------------------------------------ cards
def title_card(dur):
    n = nframes(dur)
    l1, l2 = "CAN AI BEAT", "THE LEGEND OF ZELDA"
    l3 = "WITHOUT CHEATING?"
    l4 = "...and how close can it get to the human world record?"
    for k in range(n):
        t = k / FPS
        im, d = canvas()
        a1, a2, a3, a4 = ease(t / 0.8), ease((t - 0.7) / 0.8), ease((t - 1.8) / 0.8), ease((t - 3.6) / 1.0)
        d.text((W // 2, 210), l1, font=FB[56], fill=blend(TEXT, a1), anchor="mm")
        d.text((W // 2, 300), l2, font=FB[72], fill=blend(GOLD, a2), anchor="mm")
        d.text((W // 2, 400), l3, font=FB[56], fill=blend(TEXT, a3), anchor="mm")
        d.text((W // 2, 520), l4, font=F[26], fill=blend(DIM, a4), anchor="mm")
        yield im


RULES = [("THE REAL GAME", "an unmodified copy of the original cartridge"),
         ("CONTROLLER BUTTONS ONLY", "no memory editing, no infinite hearts"),
         ("ONE CONTINUOUS RUN", "power-on to Zelda, a single recording of button presses"),
         ("NO GLITCHES", "no walking through walls, no warping across the map"),
         ("NO HUMAN INPUT. EVER.", "the human runs the programs, watches, and complains")]


def rules_card(dur, upto=0):
    n = nframes(dur)
    first_new = {0: 0, 3: 0, 5: 3}[upto]
    new = list(range(first_new, upto))
    for k in range(n):
        t = k / FPS
        im, d = canvas()
        header(d, "THE RULES", "what 'without cheating' means in this video")
        for i, (big, small) in enumerate(RULES[:upto]):
            y = 170 + i * 100
            if i in new:
                j = new.index(i)
                a = ease((t - (0.4 + j * (dur - 1.2) / max(1, len(new)))) / 0.6)
            else:
                a = 1.0
            d.text((90, y), f"{i + 1}", font=FB[56], fill=blend(GOLD, a))
            d.text((170, y + 2), big, font=FB[30], fill=blend(TEXT, a))
            d.text((172, y + 42), small, font=F[20], fill=blend(DIM, a))
        if upto == 0:
            a = ease((t - 0.5) / 0.8)
            d.text((W // 2, 380), "\"AI beats video game\"", font=FB[44], fill=blend(TEXT, a), anchor="mm")
            d.text((W // 2, 450), "can mean a lot of things.", font=F[30], fill=blend(DIM, ease((t - 1.6) / 0.8)), anchor="mm")
        yield im


def quote(dur, who="", text=""):
    n = nframes(dur)
    lines = wrap(text, 58)
    total = sum(len(l) for l in lines)
    type_time = min(dur * 0.62, total / 28)
    for k in range(n):
        t = k / FPS
        shown = int(total * min(1.0, t / max(0.1, type_time)))
        im, d = canvas()
        d.rectangle((90, 110, W - 90, H - 110), fill=PANEL, outline=(40, 48, 60), width=2)
        d.text((130, 140), who, font=FB[20], fill=GOLD)
        y, left = 210, shown
        for l in lines:
            part = l[:max(0, left)]
            left -= len(l)
            d.text((130, y), part, font=F[30], fill=TEXT)
            y += 46
        if shown < total and (k // 20) % 2 == 0:
            pass
        d.text((W - 130, H - 150), "harness/journal - written by the AI as it worked", font=F[16], fill=DIM, anchor="ra")
        yield im


def disclosure(dur):
    n = nframes(dur)
    left = ["save-state bookmarks", "up to 60 takes of every room", "reads the game's memory", "six emulators at once"]
    right = ["ONE unbroken take from power-on", "controller buttons only", "no bookmarks, no memory edits",
             "verified by replay: memory must MATCH"]
    for k in range(n):
        t = k / FPS
        im, d = canvas()
        header(d, "TOOL-ASSISTED", "to be completely straight with you")
        d.rectangle((70, 160, 620, 520), fill=PANEL, outline=(40, 48, 60), width=2)
        d.rectangle((660, 160, 1210, 520), fill=PANEL, outline=GOLD, width=2)
        d.text((95, 180), "IN PRACTICE", font=FB[26], fill=DIM)
        d.text((685, 180), "IN THE FINAL RUN", font=FB[26], fill=GOLD)
        for i, s in enumerate(left):
            d.text((95, 245 + i * 62), "- " + s, font=F[22], fill=blend(TEXT, ease((t - 0.6 - i * 0.5) / 0.5), PANEL))
        for i, s in enumerate(right):
            d.text((685, 245 + i * 62), "- " + s, font=F[22], fill=blend(TEXT, ease((t - 3.0 - i * 0.6) / 0.5), PANEL))
        a = ease((t - dur * 0.55) / 1.0)
        d.text((W // 2, 590), "Human world records are set LIVE, on real hardware, in one go.", font=FB[26],
               fill=blend(TEXT, a), anchor="mm")
        d.text((W // 2, 635), "That is a different sport.", font=F[22], fill=blend(DIM, a), anchor="mm")
        yield im


def handoff(dur):
    n = nframes(dur)
    for k in range(n):
        t = k / FPS
        im, d = canvas()
        d.text((W // 2, 170), "PART TWO", font=FB[36], fill=blend(DIM, ease(t / 0.6)), anchor="mm")
        d.text((W // 2, 290), "THE FULL RUN", font=FB[96], fill=blend(GOLD, ease((t - 0.4) / 0.8)), anchor="mm")
        d.text((W // 2, 400), "power-on to Zelda  -  39:15  -  uncut", font=F[36], fill=blend(TEXT, ease((t - 1.4) / 0.8)), anchor="mm")
        for i, s in enumerate(["no glitches  -  no memory editing  -  no save states in the run",
                               "replayed from power-on and verified: MATCH",
                               "the panel on the right is the AI's own reasoning, room by room"]):
            d.text((W // 2, 500 + i * 42), s, font=F[22], fill=blend(DIM, ease((t - 2.4 - i * 0.7) / 0.8)), anchor="mm")
        yield im


# ------------------------------------------------------------------------------------------------ terminal
def _log_lines(which):
    if which == "match":
        t = (H_DIR / "logs/archive/fourth_run_20260919/run_until.log").read_text(encoding="utf-8", errors="replace").splitlines()
        i = max(k for k, l in enumerate(t) if l.startswith("frames:"))
        return [l[:118] for l in t[i - 2:i + 7]]
    if which == "search":
        t = (H_DIR / "logs/archive/fourth_run_20260919/run_until.log").read_text(encoding="utf-8", errors="replace").splitlines()
        i = next(k for k, l in enumerate(t) if l.startswith("[l8_5e]"))
        return [l[:118] for l in t[i - 14:i + 40]]
    t = (H_DIR / "logs/archive/third_run_20260919b/run_until.full.log").read_text(encoding="utf-8", errors="replace").splitlines()
    keep = [l for l in t if re.search(r"no success; most common|RuntimeError: segment|genuinely failed|=== attempt 1 |"
                                      r"\[(L\d_done|enter_L\d|g9_ganon|g9_zelda)\]|MATCH|finished cleanly", l)]
    return [l[:118] for l in keep[-46:]]


def terminal(dur, which="match"):
    n = nframes(dur)
    lines = _log_lines(which)
    title = {"match": "python fullgame.py   # the last thing every run does", "search": "logs/run_until.log   # the search, room by room",
             "night": "logs/run_until.log   # the night of September 18-19, failures and restarts only"}[which]
    rows = 22
    per = (dur - 1.0) / max(1, len(lines))
    for k in range(n):
        t = k / FPS
        shown = min(len(lines), int(t / per) + 1)
        im, d = canvas()
        d.rectangle((50, 50, W - 50, H - 50), fill=(5, 7, 10), outline=(40, 48, 60), width=2)
        d.rectangle((50, 50, W - 50, 86), fill=(24, 30, 40))
        d.text((66, 58), title, font=F[18], fill=DIM)
        view = lines[max(0, shown - rows):shown]
        for i, l in enumerate(view):
            c = TEXT
            if "MATCH" in l or "finished cleanly" in l:
                c = GREEN
            elif "no success" in l or "RuntimeError" in l or "failed" in l:
                c = RED
            elif l.startswith("["):
                c = GOLD
            elif "early stop" in l:
                c = DIM
            d.text((70, 104 + i * 25), l[:108], font=F[18], fill=c)
        yield im


# ------------------------------------------------------------------------------------------------ architecture
def architecture(dur):
    n = nframes(dur)
    boxes = [(60, "CLAUDE", ["the AI", "", "reads guides and the", "game's source code,", "writes the bot,", "runs experiments,", "keeps a journal"], GOLD),
             (370, "PYTHON HARNESS", ["20,000 lines,", "all written by the AI", "", "navigator", "fight planner", "room search", "route planner"], TEXT),
             (680, "BRIDGE SCRIPT", ["inside the emulator", "", "a network socket:", "'hold LEFT, 8 frames'", "'read 2 KB of RAM'", "'save a bookmark'"], TEXT),
             (990, "BIZHAWK", ["the emulator", "", "the real game,", "unmodified", "", "one frame at a time"], BLUE)]
    for k in range(n):
        t = k / FPS
        im, d = canvas()
        header(d, "WHO IS PLAYING?", "the AI cannot see the screen or hold a controller, so it built both")
        for i, (x, name, body, col) in enumerate(boxes):
            a = ease((t - 0.5 - i * 1.3) / 0.8)
            d.rectangle((x, 200, x + 250, 520), fill=blend(PANEL, a), outline=blend(col, a), width=2)
            d.text((x + 125, 226), name, font=FB[22], fill=blend(col, a), anchor="mm")
            for j, s in enumerate(body):
                d.text((x + 125, 270 + j * 30), s, font=F[18], fill=blend(TEXT if j > 1 else DIM, a, PANEL), anchor="mm")
            if i < 3:
                aa = ease((t - 1.4 - i * 1.3) / 0.6)
                d.line((x + 254, 330, x + 306, 330), fill=blend(GREEN, aa), width=3)
                d.polygon([(x + 306, 322), (x + 318, 330), (x + 306, 338)], fill=blend(GREEN, aa))
                d.line((x + 254, 410, x + 306, 410), fill=blend(BLUE, aa), width=3)
                d.polygon([(x + 266, 402), (x + 254, 410), (x + 266, 418)], fill=blend(BLUE, aa))
        a = ease((t - 5.0) / 0.8)
        d.text((W // 2, 580), "buttons go right  ->        <-  numbers come back", font=F[22], fill=blend(DIM, a), anchor="mm")
        d.text((W // 2, 630), "No camera. No pixels. No hands.", font=FB[26], fill=blend(TEXT, ease((t - 6.2) / 0.8)), anchor="mm")
        yield im


# ------------------------------------------------------------------------------------------------ RAM vision
def _game(img_path):
    return Image.open(img_path).convert("RGB").resize((768, 672), Image.NEAREST)


def ramvision(dur):
    d_ = H_DIR / "youtube/capture/run6/ramvision"
    meta = json.loads((d_ / "meta.json").read_text())
    n = nframes(dur)
    slow = 4
    for k in range(n):
        i = min(len(meta) - 1, k // slow)
        m = meta[i]
        im, d = canvas()
        im.paste(_game(d_ / f"{i:04d}.png"), (0, 24))
        reveal = ease((k / FPS - 1.2) / 1.0)
        if reveal > 0:
            lx, ly = m["x"] * 3, (m["y"] - 8) * 3 + 24
            d.rectangle((lx, ly, lx + 48, ly + 48), outline=blend(GREEN, reveal), width=3)
            d.text((lx, ly - 20), f"LINK ({m['x']},{m['y']})", font=FB[16], fill=blend(GREEN, reveal))
            for slot, typ, name, x, y, hp in m["enemies"]:
                if typ >= 0x50 or y < 60:
                    continue
                ex, ey = x * 3, (y - 8) * 3 + 24
                d.rectangle((ex, ey, ex + 48, ey + 48), outline=blend(RED, reveal), width=3)
                d.text((ex, ey + 50), f"{name} hp{hp >> 4}", font=FB[16], fill=blend(RED, reveal))
        px = 768
        d.rectangle((px, 0, W, H), fill=PANEL)
        d.line((px, 0, px, H), fill=(40, 48, 60), width=2)
        d.text((px + 16, 14), "WHAT THE AI SEES", font=FB[22], fill=GOLD)
        d.text((px + 16, 46), "2 KB of NES memory, read every frame", font=F[13], fill=DIM)
        y = 84
        for lab, key in (("$0070  object X", "70"), ("$0084  object Y", "84"), ("$034F  object type", "34F"), ("$0485  object health", "485")):
            d.text((px + 16, y), lab, font=F[18], fill=DIM)
            vals = m["ram"][key]
            d.text((px + 16, y + 24), " ".join(f"{v:02X}" for v in vals), font=FB[22], fill=blend(TEXT, 0.35 + 0.65 * reveal, PANEL))
            y += 64
        d.text((px + 16, y + 6), "slot 0 is Link. Slots 1-11 are monsters,", font=F[16], fill=DIM)
        d.text((px + 16, y + 28), "items and projectiles.", font=F[16], fill=DIM)
        y += 84
        d.text((px + 16, y), "DECODED", font=F[13], fill=DIM)
        d.text((px + 16, y + 22), f"Link       x={m['x']:3d} y={m['y']:3d} hearts {m['hearts']}", font=F[20], fill=GREEN)
        yy = y + 50
        for slot, typ, name, x, y2, hp in m["enemies"][:6]:
            if typ >= 0x50:
                continue
            d.text((px + 16, yy), f"{name:<10s} x={x:3d} y={y2:3d} hp {hp >> 4}", font=F[20], fill=RED)
            yy += 28
        d.text((px + 16, H - 70), "BUTTONS THIS FRAME", font=F[13], fill=DIM)
        d.text((px + 16, H - 48), " + ".join(m["buttons"]) or "(none)", font=FB[22], fill=TEXT)
        yield im


# ------------------------------------------------------------------------------------------------ tile learning
def tilelearn(dur):
    d_ = H_DIR / "youtube/capture/run6/tilelearn"
    meta = json.loads((d_ / "meta.json").read_text())
    cells, walk, solid = meta["cells"], set(meta["walkable"]), set(meta["solid"])
    track = meta["track"]
    ev = list(meta["evidence"].items())
    shots = sorted(glob.glob(str(d_ / "f*.png")))
    n = nframes(dur)
    ov = Image.new("RGBA", (768, 672), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    for r in range(22):
        for c in range(32):
            t = cells[r][c]
            col = (80, 230, 120, 70) if t in walk else (235, 70, 70, 95) if t in solid else (255, 204, 0, 120)
            x0, y0 = c * 24, (64 - 8 + r * 8) * 3
            od.rectangle((x0, y0, x0 + 23, y0 + 23), fill=col, outline=(0, 0, 0, 60))
    lines = []
    for tid, e in ev:
        txt = e if isinstance(e, str) else (e.get("why") or e.get("note") or json.dumps(e))
        lines.append(f"tile {tid}: {str(txt)[:40]}")
    for k in range(n):
        t = k / FPS
        i = min(len(shots) - 1, int(t * FPS / 4 / 2))            # half speed
        im, d = canvas()
        g = _game(shots[i]).convert("RGBA")
        a = ease((t - 1.5) / 1.2)
        if a > 0:
            o = ov.copy()
            o.putalpha(o.getchannel("A").point(lambda v: int(v * a)))
            g = Image.alpha_composite(g, o)
        im.paste(g.convert("RGB"), (0, 24))
        upto = min(len(track), i * 4 + 1)
        pts = [(x * 3 + 24, (y - 8) * 3 + 24 + 24) for x, y, _ in track[:upto]]
        if len(pts) > 1 and a > 0:
            d.line(pts, fill=BLUE, width=4)
        px = 768
        d.rectangle((px, 0, W, H), fill=PANEL)
        d.line((px, 0, px, H), fill=(40, 48, 60), width=2)
        d.text((px + 16, 14), "LEARNING WALLS", font=FB[22], fill=GOLD)
        d.text((px + 16, 46), "knowledge/tiles.json - the bot's own notes", font=F[13], fill=DIM)
        d.rectangle((px + 16, 78, px + 34, 96), fill=(80, 230, 120)); d.text((px + 44, 78), "walkable (stood on it)", font=F[16], fill=TEXT)
        d.rectangle((px + 16, 104, px + 34, 122), fill=(235, 70, 70)); d.text((px + 44, 104), "solid (walked into it)", font=F[16], fill=TEXT)
        d.rectangle((px + 16, 130, px + 34, 148), fill=(255, 204, 0)); d.text((px + 44, 130), "unknown: assume fine, find out", font=F[16], fill=TEXT)
        shown = int(max(0, t - 3.0) * 2.2)
        for j, l in enumerate(lines[max(0, shown - 17):shown]):
            d.text((px + 16, 176 + j * 30), l[:50], font=F[16], fill=TEXT if j == min(shown, 17) - 1 else DIM)
        yield im


# ------------------------------------------------------------------------------------------------ lookahead
NAMES = {("hold", "Up"): "WALK UP", ("hold", "Down"): "WALK DOWN", ("hold", "Left"): "WALK LEFT", ("hold", "Right"): "WALK RIGHT",
         ("wait", None): "WAIT", ("swing", "Up"): "SWING UP", ("swing", "Down"): "SWING DOWN", ("swing", "Left"): "SWING LEFT",
         ("swing", "Right"): "SWING RIGHT"}


def lookahead(dur):
    n = nframes(dur)
    sets = []
    for tag, caption in (("danger", "one of these futures walks into a Darknut"), ("strike", "one of these futures lands the sword")):
        d_ = H_DIR / "youtube/capture/lookahead" / tag
        meta = json.loads((d_ / "meta.json").read_text())
        root = Image.open(d_ / "root.png").convert("RGB").resize((512, 448), Image.NEAREST)
        thumbs = [(b, Image.open(d_ / b["file"]).convert("RGB").resize((224, 196), Image.NEAREST)) for b in meta["branches"]]
        sets.append((caption, root, thumbs))
    half = n // 2
    for k in range(n):
        si = 0 if k < half else 1
        t = (k - si * half) / FPS
        span = half / FPS
        caption, root, thumbs = sets[si]
        im, d = canvas()
        d.text((40, 24), "LOOKAHEAD", font=FB[30], fill=GOLD)
        d.text((40, 62), "every 8 frames: freeze, try 9 moves on a copy, score, rewind, play the best", font=F[18], fill=DIM)
        im.paste(root, (40, 130))
        d.rectangle((40, 130, 552, 578), outline=(40, 48, 60), width=2)
        d.text((40, 590), "NOW (frozen)", font=FB[20], fill=TEXT)
        d.text((40, 620), caption, font=F[18], fill=DIM)
        best = max(b["score"] for b, _ in thumbs)
        worst = min(b["score"] for b, _ in thumbs)
        step = (span - 3.0) / 9
        for i, (b, th) in enumerate(thumbs):
            a = ease((t - 0.6 - i * step) / 0.35)
            if a <= 0:
                continue
            cx, cy = 590 + (i % 3) * 230, 104 + (i // 3) * 204
            im.paste(th, (cx, cy))
            done = t > 0.6 + 9 * step + 0.4
            col = GREEN if (done and b["score"] == best) else RED if (done and b["score"] == worst and worst < -100) else (40, 48, 60)
            d.rectangle((cx, cy, cx + 224, cy + 196), outline=col, width=4 if col != (40, 48, 60) else 1)
            d.rectangle((cx, cy + 150, cx + 224, cy + 196), fill=(5, 7, 10))
            d.text((cx + 8, cy + 154), NAMES[(b["macro"], b["dir"])], font=FB[16], fill=TEXT)
            sc = b["score"] * min(1.0, (t - 0.6 - i * step) / 0.5)
            d.text((cx + 216, cy + 174), f"{sc:+.0f}", font=FB[20], fill=GREEN if b["score"] == best else RED if b["score"] < -100 else TEXT, anchor="ra")
        if t > 0.6 + 9 * step + 0.4:
            bb = next(b for b, _ in thumbs if b["score"] == best)
            d.text((40, 672), f"PLAYED FOR REAL:  {NAMES[(bb['macro'], bb['dir'])]}", font=FB[26], fill=GREEN, anchor="ls")
        yield im


# ------------------------------------------------------------------------------------------------ source code scroll
def disasm(dur):
    n = nframes(dur)
    files = [("Z_04.asm   UpdateGanon", "asm_ganon.txt"), ("Z_01.asm   the whirlwind", "asm_whirlwind.txt"), ("Z_01.asm   HandleMonsterDied", "asm_drops.txt")]
    texts = [(t, (H_DIR / "youtube/assets" / f).read_text(encoding="utf-8", errors="replace").splitlines()) for t, f in files]
    per = n // len(texts)
    hot = re.compile(r"WhirlwindPrevRoomIdList|\.BYTE|HelpDropCount|HelpDropValue|Ganon_ScenePhase|ItemTypeToLift|bomb|Bomb", re.I)
    for k in range(n):
        fi = min(len(texts) - 1, k // per)
        title, lines = texts[fi]
        t = (k - fi * per) / FPS
        im, d = canvas()
        d.text((40, 24), "READING THE GAME'S SOURCE", font=FB[30], fill=GOLD)
        d.text((40, 62), "a community disassembly of the cartridge: github.com/aldonunez/zelda1-disassembly", font=F[18], fill=DIM)
        d.rectangle((40, 100, W - 40, H - 30), fill=(5, 7, 10), outline=(40, 48, 60), width=2)
        d.text((56, 108), title, font=FB[18], fill=BLUE)
        off = t * 4.2
        first = int(off)
        for i in range(26):
            li = first + i
            if li >= len(lines):
                break
            l = lines[li].replace("\t", "    ")[:112]
            y = 140 + (i - (off - first)) * 22
            if y < 132:
                continue
            c = GOLD if hot.search(l) else (110, 140, 110) if l.strip().startswith(";") else TEXT
            d.text((60, y), l, font=F[16], fill=c)
        yield im


# ------------------------------------------------------------------------------------------------ run 1 breakdown, complaints
def breakdown(dur):
    n = nframes(dur)
    rows = [("dungeon interiors - the actual game", 34.7, TEXT), ("EARNING RUPEES", 16.4, RED), ("a supply trip to buy bombs", 4.8, RED),
            ("whirlwind rides", 3.0, TEXT), ("one boss (Gleeok)", 1.7, TEXT)]
    for k in range(n):
        t = k / FPS
        im, d = canvas()
        header(d, "RUN 1 - WHERE 1 HOUR 43 MINUTES WENT", "the AI's own breakdown of its first finished run (journal entry 35)")
        for i, (lab, mins, col) in enumerate(rows):
            a = ease((t - 0.5 - i * 0.9) / 0.9)
            y = 190 + i * 88
            d.text((80, y), lab, font=FB[22] if col == RED else F[22], fill=blend(col, min(1, a * 2)))
            d.rectangle((80, y + 34, 80 + int(900 * mins / 34.7 * a), y + 60), fill=blend(col if col == RED else BLUE, a))
            d.text((90 + int(900 * mins / 34.7 * a), y + 34), f"{mins * a:.1f} min", font=FB[22], fill=blend(TEXT, a))
        a = ease((t - 6.0) / 0.8)
        d.text((80, 650), "Sixteen minutes of killing the same two rooms for pocket money.", font=FB[22], fill=blend(GOLD, a))
        yield im


COMPLAINTS = ["\"link sits there attacking the air for about 15 seconds rather than moving on\"",
              "\"link gets stuck in the dark room and is there for nearly 30 seconds when it should take 3-5\"",
              "\"link also pushes the wrong block after pushing the right block\"",
              "\"you chose the whistle... then sit there and dont blow the whistle for a long time\"",
              "\"link sits there for a long time before doing anything (bombing right wall)\"",
              "\"you should generally just go through them and kill them if they get in the way",
              "  rather than avoid them. your pathing takes longer than just killing them\"",
              "\"human world records are under 30 minutes... it would be amazing",
              "  if you were in the realm of that\""]


def complaints(dur):
    n = nframes(dur)
    per = (dur - 2.0) / len(COMPLAINTS)
    for k in range(n):
        t = k / FPS
        im, d = canvas()
        header(d, "THE REVIEW", "my notes on the 58-minute run, as I sent them (typos included)")
        for i, l in enumerate(COMPLAINTS):
            a = ease((t - 0.5 - i * per) / 0.5)
            hot = "go through them" in l or "rather than avoid" in l
            d.text((80, 170 + i * 54), l, font=FB[22] if hot else F[22], fill=blend(GOLD if hot else TEXT, a))
        yield im


# ------------------------------------------------------------------------------------------------ chart
RUNS = [("RUN 1", "Sep 15", 102 + 21 / 60, "1:42:21"), ("RUN 2", "Sep 16", 57 + 40 / 60, "57:40"), ("RUN 3", "Sep 19", 41.25, "41:15"),
        ("RUN 4", "Sep 19", 39.25, "39:15")]
WR_MIN = 27 + 40 / 60


def chart(dur, upto=4, wr=True, gap=False):
    n = nframes(dur)
    x0, x1, scale = 250, 1050, (1050 - 250) / 105.0
    for k in range(n):
        t = k / FPS
        im, d = canvas()
        header(d, "POWER-ON TO ZELDA", "minutes of game time - every run replayed from power-on and verified")
        for i, (name, date, mins, lab) in enumerate(RUNS[:upto]):
            newest = i == upto - 1
            a = ease((t - 0.4) / 1.6) if newest else 1.0
            y = 180 + i * 96
            d.text((70, y + 4), name, font=FB[30], fill=GOLD if newest else TEXT)
            d.text((70, y + 40), date, font=F[18], fill=DIM)
            col = GREEN if (newest and upto == 4) else BLUE
            d.rectangle((x0, y, x0 + int(mins * scale * a), y + 56), fill=col)
            if a > 0.98:
                d.text((x0 + int(mins * scale) + 12, y + 10), lab, font=FB[36], fill=TEXT)
        if wr:
            a = ease((t - 2.2) / 0.8)
            xw = x0 + int(WR_MIN * scale)
            for yy in range(160, 580, 14):
                d.line((xw, yy, xw, yy + 7), fill=blend(RED, a), width=3)
            d.text((xw, 596), "HUMAN WORLD RECORD 27:40", font=FB[22], fill=blend(RED, a), anchor="ma")
            d.text((xw, 626), "any% no up+a - live, real hardware, glitches allowed", font=F[16], fill=blend(DIM, a), anchor="ma")
        if gap and upto == 4:
            a = ease((t - 3.4) / 0.8)
            xa, xb, y = x0 + int(WR_MIN * scale), x0 + int(39.25 * scale), 180 + 3 * 96 + 70
            d.line((xa, y, xb, y), fill=blend(GOLD, a), width=3)
            d.text(((xa + xb) // 2, y + 8), "11:30", font=FB[26], fill=blend(GOLD, a), anchor="ma")
        yield im


WR_ROUTE = [("Get the Wooden Sword", None), ("SCREEN SCROLL to Level 3", "glitch"), ("Level 3  ->  Level 4  ->  Level 1", None),
            ("heart container at the heart rock, a 30-rupee secret", "take"), ("buy the BLUE CANDLE", "take"),
            ("SCREEN SCROLL to Level 5", "glitch"), ("recorder warp, the 100-rupee secret", "take"),
            ("WORLD WRAP south for two more heart containers", "glitch"), ("SCROLL to Level 2", "glitch"),
            ("recorder warp: buy MEAT and ARROWS", None), ("Level 7, then the MAGIC SWORD", "take"), ("Levels 6, 8, 9 by recorder", None)]


def wr_route(dur):
    n = nframes(dur)
    per = (dur * 0.62) / len(WR_ROUTE)
    for k in range(n):
        t = k / FPS
        im, d = canvas()
        header(d, "THE RECORD ROUTE", "\"Three First Blue Candle\" - Order of the Ate's route notes for the 27:40 category")
        for i, (l, kind) in enumerate(WR_ROUTE):
            a = ease((t - 0.4 - i * per) / 0.4)
            late = t > dur * 0.68
            col = RED if kind == "glitch" else GREEN if (kind == "take" and late) else TEXT
            d.text((90, 150 + i * 40), f"{i + 1:2d}.  {l}", font=FB[22] if kind == "glitch" else F[22], fill=blend(col, a))
            if kind == "glitch" and a > 0.9:
                d.text((1190, 150 + i * 40), "GLITCH", font=FB[22], fill=RED, anchor="ra")
            if kind == "take" and late:
                d.text((1190, 150 + i * 40), "LEGIT - TAKE IT", font=FB[22], fill=GREEN, anchor="ra")
        a = ease((t - dur * 0.78) / 0.8)
        d.text((W // 2, 665), "WE STAY GLITCH-FREE - AND TAKE EVERYTHING ELSE", font=FB[30], fill=blend(GOLD, a), anchor="mm")
        yield im


# ------------------------------------------------------------------------------------------------ the decoded overworld
_MAP = {}


def _map_base():
    if "im" in _MAP:
        return _MAP["im"], _MAP["free"]
    from zelda import owroute
    sw, sh = 80, 50
    im = Image.new("RGB", (16 * sw, 8 * sh), (16, 22, 30))
    d = ImageDraw.Draw(im)
    free = {}
    for room in range(128):
        f = owroute.free(room, True)
        free[room] = f
        ox, oy = (room & 15) * sw, (room >> 4) * sh
        for x, y in f:
            px, py = ox + int(x / 256 * sw), oy + int((y - 61) / 168 * sh)
            d.rectangle((px, py, px + 2, py + 2), fill=SAND)
        d.rectangle((ox, oy, ox + sw - 1, oy + sh - 1), outline=(30, 38, 50))
    _MAP["im"], _MAP["free"] = im, free
    return im, free


def _xy(room, x, y):
    return (room & 15) * 80 + int(x / 256 * 80), 140 + (room >> 4) * 50 + int((y - 61) / 168 * 50)


def _route_points(archive):
    rows = []
    for f in glob.glob(str(H_DIR / archive / "checkpoints" / "fullgame_*.json")):
        dd = json.load(open(f))
        m = re.search(r"mode=(\w\w)/\w\w L(\d) room=([0-9a-f]{2}) pos=\((\d+),(\d+)\)", dd["summary"])
        rows.append((dd["frames"], os.path.basename(f)[9:-5], int(m.group(1), 16), int(m.group(2)), int(m.group(3), 16), int(m.group(4)), int(m.group(5))))
    rows.sort()
    pts, marks = [], []
    for fr, name, mode, lvl, room, x, y in rows:
        if lvl == 0 and mode == 5 and room < 128:
            pts.append((fr, _xy(room, x, y), "w" in name and ("_w" in name)))
        mm = re.match(r"L(\d)_done", name)
        nice = {"white_sword": "WHITE-SWORD", "ms_sword": "MAGICAL-SWORD", "buy_candle": "candle", "buy_arrows": "arrows",
                "buy_food": "bait", "h2c_heart": "heart", "h47_heart": "heart", "hc_47_heart": "heart", "cave_0f": "100r",
                "cave_6b": "100r", "cave_67": "30r", "cave_3d": "30r"}
        if name in nice:
            marks.append((fr, nice[name]))
        if mm:
            marks.append((fr, f"L{mm.group(1)}"))
    zelda = next(fr for fr, name, *_ in rows if name == "g9_zelda")
    return pts, marks, zelda


DOORS = {1: 0x37, 2: 0x3C, 3: 0x74, 4: 0x45, 5: 0x0B, 6: 0x22, 7: 0x42, 8: 0x6D, 9: 0x05}


def map(dur, mode="reveal"):
    n = nframes(dur)
    base, free = _map_base()
    if mode != "reveal":
        pts, marks, total = _route_points("logs/archive/third_run_20260919b" if mode == "route3" else "logs/archive/fourth_run_20260919")
    order3 = "L3  L1  White Sword  L4  L2  L5  shops  L6  L7  L8  heart  Magical Sword  L9"
    order4 = "L3  heart  100r  CANDLE  White Sword  L1  heart  L4  100r  L8  L2  L5  shops  L7  Magical Sword  L6  L9"
    for k in range(n):
        t = k / FPS
        im, d = canvas()
        if mode == "reveal":
            header(d, "THE WHOLE MAP, FROM THE CARTRIDGE", "128 screens decoded from the ROM - this is where Link can stand")
            shown = int(128 * ease(t / (dur * 0.6)))
            m2 = Image.new("RGB", base.size, (16, 22, 30))
            for room in range(shown):
                ox, oy = (room & 15) * 80, (room >> 4) * 50
                m2.paste(base.crop((ox, oy, ox + 80, oy + 50)), (ox, oy))
            im.paste(m2, (0, 140))
            d.text((60, 570), f"screens decoded: {shown}/128", font=FB[26], fill=TEXT)
            a = ease((t - dur * 0.66) / 0.8)
            d.text((60, 615), "checked against every screen the bot had actually walked:", font=F[22], fill=blend(DIM, a))
            d.text((60, 650), "98 of 98 identical", font=FB[30], fill=blend(GREEN, a))
        else:
            col = (255, 140, 60) if mode == "route3" else GREEN
            header(d, "RUN 3'S ROUTE" if mode == "route3" else "THE PLANNER'S ROUTE", order3 if mode == "route3" else order4)
            im.paste(base, (0, 140))
            for lvl, room in DOORS.items():
                x, y = _xy(room, 120, 130)
                d.ellipse((x - 9, y - 9, x + 9, y + 9), outline=GOLD, width=2)
                d.text((x, y), str(lvl), font=FB[16], fill=GOLD, anchor="mm")
            frac = ease(t / (dur * 0.72))
            upto_fr = total * frac
            seg = [p for fr, p, _ in pts if fr <= upto_fr]
            for a_, b_ in zip(seg, seg[1:]):
                far = abs(a_[0] - b_[0]) + abs(a_[1] - b_[1]) > 110
                if far:
                    for s in range(0, 10, 2):
                        q0 = (a_[0] + (b_[0] - a_[0]) * s / 10, a_[1] + (b_[1] - a_[1]) * s / 10)
                        q1 = (a_[0] + (b_[0] - a_[0]) * (s + 1) / 10, a_[1] + (b_[1] - a_[1]) * (s + 1) / 10)
                        d.line((q0, q1), fill=BLUE, width=2)
                else:
                    d.line((a_, b_), fill=col, width=3)
            if seg:
                x, y = seg[-1]
                d.ellipse((x - 5, y - 5, x + 5, y + 5), fill=TEXT)
            done = [nm for fr, nm in marks if fr <= upto_fr]
            d.text((60, 560), "done: " + " ".join(done[-14:]), font=F[18], fill=DIM)
            d.text((60, 590), f"game clock {upto_fr / 60.0988 / 60:5.2f} min", font=FB[26], fill=TEXT)
            a = ease((t - dur * 0.78) / 0.7)
            if mode == "route3":
                d.text((60, 640), "model 41.33 min", font=FB[30], fill=blend(GOLD, a))
                d.text((420, 640), "actual 41.26 min", font=FB[30], fill=blend(GREEN, a))
            else:
                d.text((60, 640), "PREDICTED 39.24 min", font=FB[30], fill=blend(GOLD, a))
            d.text((W - 60, 590), "dashed blue = whirlwind ride", font=F[16], fill=DIM, anchor="ra")
        yield im


NUMBERS = [(8, "DAYS", "September 11 to September 19"), (42, "JOURNAL ENTRIES", "written by the AI as it worked"),
           (20271, "LINES OF PYTHON", "201 files, all written by the AI"), (90, "PROBE EXPERIMENTS", "one question each, asked of the emulator"),
           (44000, "REHEARSED ROOMS", "attempts recorded in the four runs' search logs"), (0, "HUMAN INPUTS", "on the controller, ever")]


def numbers(dur):
    n = nframes(dur)
    for k in range(n):
        t = k / FPS
        im, d = canvas()
        header(d, "WHAT IT TOOK")
        for i, (val, lab, sub) in enumerate(NUMBERS):
            a = ease((t - 0.3 - i * (dur - 2.5) / len(NUMBERS)) / 0.7)
            x, y = 90 + (i % 2) * 600, 170 + (i // 2) * 170
            shown = int(val * a)
            txt = f"{shown:,}" + ("+" if val == 44000 and a > 0.99 else "")
            d.text((x, y), txt, font=FB[72], fill=blend(GREEN if val == 0 else GOLD, a))
            d.text((x + 4, y + 82), lab, font=FB[26], fill=blend(TEXT, a))
            d.text((x + 4, y + 116), sub, font=F[16], fill=blend(DIM, a))
        yield im


GEN = {"title_card": title_card, "rules_card": rules_card, "quote": quote, "disclosure": disclosure, "handoff": handoff,
       "terminal": terminal, "architecture": architecture, "ramvision": ramvision, "tilelearn": tilelearn, "lookahead": lookahead,
       "disasm": disasm, "breakdown": breakdown, "complaints": complaints, "chart": chart, "wr_route": wr_route, "map": map, "numbers": numbers}
