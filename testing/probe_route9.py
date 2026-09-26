import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import sys
from zelda.emulator import BizHawk
from zelda.overworld import Navigator
from zelda.explorer import Explorer
ckpt, target, budget = sys.argv[1], int(sys.argv[2], 16), int(sys.argv[3])
emu = BizHawk(log_name="probe_route9.log", clean_sram=False)
nav = Navigator(emu)
ex = Explorer(emu, nav)
try:
    print("ROUTE:", ex.route(target, ckpt, max_nodes=budget))
except Exception as e:
    print("FAILED:", type(e).__name__, str(e)[:120])
emu.close()
