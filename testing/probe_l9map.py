"""Tour everything reachable from a checkpoint, recording each room's enemies and items.

This is the scout answering a question the ROM tables could not: the door graph says Level 9's
body is forty rooms, but it does not say which of them holds Ganon. Walking it does.
"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import sys
from zelda.emulator import BizHawk
from zelda.overworld import Navigator
from zelda.explorer import Explorer

ckpt = sys.argv[1]
budget = int(sys.argv[2]) if len(sys.argv) > 2 else 45
emu = BizHawk(log_name="probe_l9map.log", clean_sram=False)
nav = Navigator(emu)
ex = Explorer(emu, nav)
try:
    ex.route(None, ckpt, max_nodes=budget)
except Exception as e:
    print("FAILED:", type(e).__name__, str(e)[:200])
finally:
    emu.close()
