"""Validate a Patra fight exactly as the run would use it: random_search from the s9_61 checkpoint
with the damage-aware lookahead fighting with the sword. The survey showed only the sword hurts it
(core 0x47 hp 11, eight eyes 0x25 hp 6) and that standing still and swinging gets Link killed."""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import fullgame
from zelda.emulator import BizHawk
from zelda.overworld import Navigator
from zelda.search import random_search
from zelda.segments import make_lafight_policy

emu = BizHawk(log_name="probe_patra_fight.log", clean_sram=False)
nav = Navigator(emu)
best = random_search(emu, "ckpt_fullgame_s9_61", make_lafight_policy(nav, None),
                     lambda e, s: s.hearts > 0 and s.room == 0x61 and e.byte(0x34D) != 0,
                     tries=6, max_frames=9000, label="probe patra lookahead", log=print, prefer_hearts=True)
print("BEST:", None if best is None else (best.frames, best.hearts), flush=True)
emu.close()
