"""Does seeing monster drops actually change what a farm earns?

The pickup routine and the fight planner both used to read only the room item, so every rupee, heart
and bomb dropped by a kill was invisible. This runs the exact farm that stalled in the live run - from
its own start state, no settle frames - with the fixed code, and reports what each attempt earned.
"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import random, time
import fullgame
from zelda.emulator import BizHawk
from zelda.overworld import Navigator
from zelda.combat import Fighter
from zelda.search import Recorder

emu = BizHawk(log_name="probe_drops.log", clean_sram=False)
nav = Navigator(emu)
emu.load("fullgame_l6_farm20_start")
print("sanity: visible_drops() at start ->", Fighter(nav).visible_drops(), flush=True)
policy = fullgame.farm_dungeon_policy(nav, 20, 6)
for i in range(4):
    t0 = time.time()
    emu.load("fullgame_l6_farm20_start")
    s0 = emu.state(); r0 = emu.byte(0x66D)
    rec = Recorder(emu); rec.step((), 2)
    try:
        out = policy(emu, rec, random.Random(1000 + i), 3000)
    except Exception as e:
        out = f"{type(e).__name__}: {str(e)[:40]}"
    s = emu.state(); r1 = emu.byte(0x66D)
    n = max(1, len(rec.inputs))
    print(f"  attempt {i+1}: {str(out)[:26]:28s} rupees {r0}->{r1} (+{r1-r0}) in {n:5d} frames "
          f"= {1000*(r1-r0)/n:5.1f} per 1000 frames | hearts {s0.hearts}->{s.hearts} | {time.time()-t0:4.0f}s",
          flush=True)
emu.close()
