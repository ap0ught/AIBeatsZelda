"""Validate hc_cave_policy exactly as the run will use it (random_search from a bookmark) on both
caves that were verified by screenshot: 0x47 (burn) and 0x2C (bomb)."""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import fullgame
from zelda.emulator import BizHawk
from zelda.overworld import Navigator
from zelda.search import random_search

emu = BizHawk(log_name="probe_hc.log", clean_sram=False)
nav = Navigator(emu)
for ckpt, d, room, stand, face, method in [
        ("ckpt_fullgame_h9_48", "Left", 0x47, (176, 157), "Down", "burn"),
        ("ckpt_fullgame_c8_2d", "Left", 0x2C, (176, 157), "Left", "bomb")]:
    s = emu.load(ckpt); s = emu.wait(4)
    s = nav.exit_screen(d)
    name = f"probe_on_{room:02x}"
    emu.save(name)
    need = s.containers + 1
    print(f"=== {room:02X}: {s} | containers {s.containers}, success needs {need}", flush=True)
    best = random_search(emu, name, fullgame.hc_cave_policy(nav, stand, face, method),
                         lambda e, q, need=need: (q.containers >= need and q.level == 0
                                                  and q.mode == 5 and q.hearts > 0),
                         tries=4, max_frames=3000, label=f"probe hc {room:02X}", log=print,
                         prefer_hearts=True)
    print("BEST:", None if best is None else (best.frames, best.hearts, best.outcome), flush=True)
emu.close()
