"""The tenth kill: the real run-6 sequence in Level 4's dark room (frames 44634-45434) with the cartridge's own code on
the right - HandleMonsterDied from the disassembly - lines lighting up as the counters in memory change: the streak
climbs to nine, a bomb is placed, the tenth kill is the bomb's, HelpDropValue flips to one, and four bombs appear.
Data: youtube/capture/tenth/ (capture_tenth.py) + youtube/assets/asm_drops.txt. usage: python youtube/gfx_tenth.py [out]"""
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).parent))
import gfx
from build import render_frames

out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("youtube/clips_v3/tenth_kill.mp4")
out.parent.mkdir(parents=True, exist_ok=True)
root = Path("youtube/capture/tenth")
meta = json.load(open(root / "meta.json"))
asm = [l.rstrip() for l in open("youtube/assets/asm_drops.txt", encoding="utf-8", errors="replace")]
i0 = next(i for i, l in enumerate(asm) if l.startswith("HandleMonsterDied"))
asm = asm[i0:i0 + 22]
S = 2.5; GX, GY = 24, 24; PX = GX + int(256 * S) + 24
START = 300                     # skip the first 5 s of the capture (nothing happens yet)
def frames():
    hold = 0
    last_kills = meta[START]["kills"]; flash = -999
    events = []                 # (video frame, text)
    for j in range(START, len(meta)):
        m = meta[j]
        im = Image.new("RGB", (gfx.W, gfx.H), gfx.BG)
        game = Image.open(root / f"{j:04d}.png").convert("RGB").resize((int(256 * S), int(224 * S)), Image.NEAREST)
        im.paste(game, (GX, GY))
        d = ImageDraw.Draw(im)
        d.rectangle((PX - 8, 0, gfx.W, gfx.H), fill=gfx.PANEL)
        d.text((PX, 14), "THE CARTRIDGE'S OWN RULE", font=gfx.FB[20], fill=gfx.GOLD)
        d.text((PX, 40), "HandleMonsterDied  (from the disassembly)", font=gfx.F[13], fill=gfx.DIM)
        prev = meta[j - 1]
        killed = m["kills"] != prev["kills"] or m["streak"] > prev["streak"]
        if killed: flash = j
        tenth = m["value"] == 1
        y = 60
        for k, line in enumerate(asm):
            col = gfx.TEXT
            if "INC HelpDropCount" in line and j - flash < 30: col = gfx.GREEN
            if "INC HelpDropValue" in line and tenth: col = gfx.GOLD
            if "CMP #$0A" in line and m["streak"] >= 9: col = gfx.SAND
            if "CMP #$08" in line and tenth: col = gfx.GOLD
            d.text((PX, y), line[:52], font=gfx.F[13], fill=col); y += 15
        y += 10
        d.text((PX, y), "memory, right now", font=gfx.F[13], fill=gfx.DIM); y += 20
        d.text((PX, y), f"$50 HelpDropCount  = {m['streak']:2d}   kills in a row without a hit", font=gfx.F[16], fill=gfx.GREEN if m['streak'] >= 9 else gfx.TEXT); y += 22
        d.text((PX, y), f"$51 HelpDropValue  = {m['value']:2d}   1 = the tenth was a bomb's: drop bombs", font=gfx.F[16], fill=gfx.GOLD if tenth else gfx.TEXT); y += 22
        d.text((PX, y), f"bombs in hand      = {m['bombs']:2d}", font=gfx.F[16], fill=gfx.GOLD if m['bombs'] > prev['bombs'] else gfx.TEXT); y += 30
        # the running story
        if m["streak"] > prev["streak"]: events.append((j, f"kill {m['streak']}, streak {m['streak']}"))
        if m["bombs"] < prev["bombs"]: events.append((j, "the planner holds the sword back and places a bomb"))
        if m["value"] > prev["value"]: events.append((j, "TENTH KILL, made by the bomb -> HelpDropValue = 1"))
        if m["bombs"] > prev["bombs"]: events.append((j, f"four bombs on the floor, picked up: {prev['bombs']} -> {m['bombs']}"))
        for ej, text in events[-8:]:
            d.text((PX, y), f"f{meta[ej]['frame']}  {text}", font=gfx.F[13], fill=gfx.GOLD if "TENTH" in text or "four" in text else gfx.TEXT); y += 17
        d.text((PX, gfx.H - 40), "Level 4, the dark room before Gleeok - run 6, frames 44934-45434", font=gfx.F[13], fill=gfx.DIM)
        d.text((PX, gfx.H - 22), "read out of the game's code on day 3; used in every run since", font=gfx.F[13], fill=gfx.DIM)
        yield im
        if m["value"] > prev["value"] or m["bombs"] > prev["bombs"]:
            for _ in range(45): yield im
render_frames(frames(), out)
print("wrote", out)
