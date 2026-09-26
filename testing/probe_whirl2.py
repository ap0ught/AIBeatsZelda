"""Validate the rewritten whirl_to_policy exactly the way the run will use it: random_search
from the x9_out checkpoint, target Level 1's door (0x37)."""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import fullgame
from zelda.emulator import BizHawk
from zelda.overworld import Navigator
from zelda.search import random_search

emu = BizHawk(log_name="probe_whirl2.log", clean_sram=False)
nav = Navigator(emu)
best = random_search(emu, "ckpt_fullgame_x9_out", fullgame.whirl_to_policy(nav, 0x37, counter=0x0B),
                     lambda e, s: s.room == 0x37 and s.level == 0 and s.mode == 5 and s.hearts > 0,
                     tries=6, max_frames=3000, label="probe whirl to 37", log=print, prefer_hearts=True)
print("BEST:", None if best is None else (best.frames, best.hearts, best.outcome), flush=True)
emu.close()
