"""How many attempts does the White Sword approach actually need at 3.5 hearts?

Route 5 reached ckpt_fullgame_ws_0a at 3.5/5 hearts and got zero successes in 60. run6 reached the same
screen at 4.5/5 and succeeded on attempt 39. A Blue Lynel hits for two hearts, and `hearts >= containers`
is false below full, so the sword beam is off and only a clean walk gets Link to the cave mouth.

This runs the real cave_item_policy - not a reimplementation - from the real checkpoint, and reports how
many attempts succeed at each starting health. If 3.5 hearts simply needs more draws than 60, the fix is a
larger `tries`; if it needs a different order of magnitude, the fix is to arrive healthier and that is a
routing problem, not a patience problem. The difference matters, so measure it rather than guess.

    python3 testing/probe_white_sword_effort.py [attempts]
"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)
del _os, _sys, _pathlib

import random
import sys

from zelda.emulator import BizHawk
from zelda.overworld import Navigator
from zelda.search import Recorder

sys.path.insert(0, str(_ROOT))
import fullgame as fg

N = int(sys.argv[1]) if len(sys.argv) > 1 else 40

with BizHawk(log_name="probe_white_sword_effort.log") as emu:
    nav = Navigator(emu)
    won = 0
    deaths = 0
    for i in range(N):
        s0 = emu.load("ckpt_fullgame_ws_0a")
        rec = Recorder(emu)
        orig = emu.step
        emu.step = rec.step
        try:
            out = fg.cave_item_policy(nav, 0x657)(emu, rec, random.Random(7000 + i), 3000)
        except Exception as exc:                       # a policy that raises is a failure, not a crash
            out = f"raised: {str(exc)[:40]}"
        finally:
            emu.step = orig
        s = emu.state()
        good = s.sword >= 2 and s.mode == 5 and s.level == 0 and s.hearts > 0
        if good:
            won += 1
        else:
            deaths += 1
        print(f"[{i:3d}] {s0.hearts}/{s0.containers} hearts -> {out:34s} "
              f"sword {s0.sword}->{s.sword} hp {s.hearts}  {'WIN' if good else 'fail'}")
    print(f"\n{N - deaths}/{N} wins from 3.5/5 hearts.  {deaths} failures.")
    if won:
        print(f"the 60-attempt segment would have needed about {N // won} tries to see one of these.")
