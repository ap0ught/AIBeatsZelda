"""Which room-clearing segments never needed the clear?

For every dungeon segment whose policy fights the whole room (make_lafight_policy / make_clear_policy with an
exit), look up the exit door in the cartridge's table. A shutter needs the room cleared; an open, locked or
bombed door does not. For the ones that do not, race the existing policy against a plain crossing from the
finished run's own state and print both.

usage: python probe_cross_audit.py [--seeds N] [--list]"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import inspect
import json
import pathlib
import random
import re
import sys
import time

import fullgame
from zelda import runner
from zelda.emulator import BizHawk
from zelda.overworld import LinkDied, Navigator
from zelda.romdata import room_info
from zelda.search import Recorder, make_cross_policy

seeds = int(sys.argv[sys.argv.index("--seeds") + 1]) if "--seeds" in sys.argv else 3
S = pathlib.Path(r"C:/Users/scots/AppData/Local/Temp/claude/G--AI-World-Record/d5fcfe9d-4ac8-40d5-8a32-00e8e94fae89/scratchpad")
facts = {f["name"]: f for f in json.load(open(S / "captions/facts.json", encoding="utf-8"))}
segs = fullgame.segments()
names = [s[0] for s in segs]
SIDE = {"Up": "N", "Down": "S", "Left": "W", "Right": "E"}
cands = []
for k, (name, factory, success, tries) in enumerate(segs):
    f = facts.get(name)
    if not f or not f["start"]["level"]:
        continue
    try:
        src = inspect.getsource(factory)
    except Exception:
        continue
    m = re.search(r"make_(lafight|clear)_policy\(nav, \"(Up|Down|Left|Right)\"", src)
    if not m:
        continue
    d = m.group(2)
    lv, room = f["start"]["level"], int(f["start"]["room"], 16)
    door = room_info(lv, room)[SIDE[d]]
    gained = f["end"]["keys"] > f["start"]["keys"] or f["end"]["bombs"] > f["start"]["bombs"]
    cands.append((name, k, d, door, f["frames"], gained, f["start_room_enemies_from_rom"]))
print(f"{len(cands)} room-clearing segments with an exit:")
for name, k, d, door, fr, gained, en in cands:
    print(f"  {name:12s} exit {d:5s} door {door:9s} {fr:5d} fr {'(gained key/bombs)' if gained else '':19s} {en}")
if "--list" in sys.argv:
    sys.exit()

emu = BizHawk(log_name="probe_cross_audit.log", clean_sram=False)
nav = Navigator(emu)
print("\nracing the non-shutter ones (best of", seeds, "seeds):")
for name, k, d, door, fr, gained, en in cands:
    if door == "shutter":
        continue
    only = [a for a in sys.argv[1:] if a in names]
    if only and name not in only:
        continue
    _, factory, success, tries = segs[k]
    state = f"ckpt_fullgame_{names[k - 1]}"
    out = {}
    for label, make in (("fight", lambda: factory(nav)), ("cross", lambda: make_cross_policy(nav, d))):
        res = []
        for seed in range(seeds):
            s0 = emu.load(state)
            runner.SEG_START = s0
            rec = Recorder(emu)
            rec.step((), 2)
            nav.blocked = {}
            try:
                o = make()(emu, rec, random.Random(1000 + seed), 3000)
            except LinkDied:
                o = "died"
            except Exception as e:
                o = f"{type(e).__name__}"
            s = emu.state()
            ok = o != "died" and s.hearts > 0 and s.mode == 5 and s.room == int(facts[name]["end"]["room"], 16)
            res.append((ok, len(rec.inputs), s0.hearts - s.hearts))
        good = [r for r in res if r[0]]
        out[label] = (min(good, key=lambda r: r[1] + 300 * r[2]) if good else None, len(good))
    fb, cb = out["fight"], out["cross"]
    print(f"  {name:12s} door {door:8s} fight {fb[0][1] if fb[0] else '----':>5} ({(-fb[0][2] if fb[0] else 0):+.1f}h, {fb[1]}/{seeds})"
          f"   cross {cb[0][1] if cb[0] else '----':>5} ({(-cb[0][2] if cb[0] else 0):+.1f}h, {cb[1]}/{seeds})   was {fr}", flush=True)
emu.close()
