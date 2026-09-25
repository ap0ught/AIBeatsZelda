"""YouTube description for the v3 upload: part-one chapters from the narration's section timing, part-two chapters
from run 6's dungeon entries. usage: python youtube/describe_v3.py <part1 seconds> [live intro seconds]"""
import json, pathlib, sys
F = 60.0988
p1 = float(sys.argv[1]); intro = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
def ts(s):
    s = int(round(s)); return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"
secs = json.load(open("youtube/voice/narration_sections.json", encoding="utf-8"))
ck = sorted(((json.load(open(f))["frames"], f.stem[9:]) for f in pathlib.Path("logs/archive/sixth_run_20260922/checkpoints").glob("fullgame_*.json")))
prev = 0; marks = []
NAMES = {"enter_L3": "Level 3 (the raft)", "white_sword": "The White Sword", "enter_L1": "Level 1", "enter_L4": "Level 4", "enter_L8": "Level 8",
         "enter_L2": "Level 2", "enter_L5": "Level 5", "buy_arrows": "The shops", "enter_L7": "Level 7", "ms_sword": "The Magical Sword",
         "enter_L6": "Level 6", "enter_L9": "Level 9 (Death Mountain)", "g9_ganon": "Ganon", "g9_zelda": "Zelda"}
for fr, n in ck:
    if n in NAMES: marks.append((prev / F, NAMES[n]))
    prev = fr
out = ["Can an AI beat The Legend of Zelda without cheating? Ten days, six complete runs, no controller, no memory editing, no glitches.",
       "The first half is how it learned; the second half is the fastest run, uncut, verified from power-on.", "",
       "The code and the input file: [link]", "", "CHAPTERS"]
if intro: out.append(f"{ts(0)} Intro")
for s in secs:
    if s["section"] == "outro":
        continue
    name = s["section"].split(". ", 1)[-1] if ". " in s["section"] else s["section"]
    out.append(f"{ts(intro + s['start'])} {'Why' if name == 'preamble' else name}")
base = intro + p1
out.append(f"{ts(base)} THE RUN (37:02, uncut)")
for t, name in marks:
    out.append(f"{ts(base + t)} {name}")
run_len = 136526 / F
if any(s["section"] == "outro" for s in secs):
    out.append(f"{ts(base + run_len)} Outro")
out += ["", "Rules: unmodified game, controller inputs only, one continuous run from power-on, no memory editing, no glitches, no human input.",
        "Tool-assisted: every room was rehearsed from a bookmark and the best take kept; the final run is one unbroken input log, replayed",
        "from power-on in a fresh emulator and checked byte for byte. Human records (27:40) are set live on real hardware."]
pathlib.Path("youtube/out_v3/description.txt").write_text("\n".join(out), encoding="utf-8")
print("\n".join(out))
