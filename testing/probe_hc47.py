"""Re-validate hc_cave_policy on 0x47 (burn) after squaring up exactly on the spot."""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import fullgame
from zelda.emulator import BizHawk
from zelda.overworld import Navigator
from zelda.search import random_search

emu = BizHawk(log_name="probe_hc47.log", clean_sram=False)
nav = Navigator(emu)
s = emu.load("ckpt_fullgame_h9_48"); s = emu.wait(4)
s = nav.exit_screen("Left")
emu.save("probe_on_47")
need = s.containers + 1
print(f"=== 47: {s} | containers {s.containers}, success needs {need}", flush=True)
best = random_search(emu, "probe_on_47", fullgame.hc_cave_policy(nav, (176, 157), "Down", "burn"),
                     lambda e, q: q.containers >= need and q.level == 0 and q.mode == 5 and q.hearts > 0,
                     tries=4, max_frames=3000, label="probe hc 47", log=print, prefer_hearts=True)
print("BEST:", None if best is None else (best.frames, best.hearts), flush=True)
emu.close()
