"""The one crossing the single-pass Level 6 route has never made: into 0x52 from the EAST (the old bait
expedition's way back), then straight down to 0x62 and west into the Lost Woods' first screen. The old
route only ever left 0x52 downward after arriving from 0x42 above. Several seeds, from the old run's
saved state at the end of b7_52."""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import random

from zelda.emulator import BizHawk
from zelda.overworld import Navigator
from zelda.search import Recorder, make_cross_policy

emu = BizHawk(log_name="probe_52_south.log", clean_sram=False)
nav = Navigator(emu)
wins = 0
for seed in range(6):
    emu.load("ckpt_fullgame_b7_52")
    s = emu.state()
    print(f"seed {seed}: start room {s.room:02X} ({s.x},{s.y}) hearts {s.hearts}", flush=True)
    total = 0
    good = True
    for d, room in (("Down", 0x62), ("Left", 0x61)):
        rec = Recorder(emu)
        try:
            out = make_cross_policy(nav, d)(emu, rec, random.Random(seed), 2000)
        except Exception as e:
            out = f"{type(e).__name__}: {str(e)[:40]}"
        s = emu.state()
        total += len(rec.inputs)
        ok = s.room == room and s.mode == 5 and s.hearts > 0
        print(f"   {d:5s} -> {s.room:02X} ({s.x:3d},{s.y:3d}) {len(rec.inputs):5d} fr hearts {s.hearts} "
              f"{str(out)[:24]} {'OK' if ok else 'WRONG'}", flush=True)
        if not ok:
            good = False
            break
    wins += good
    print(f"   total {total} frames", flush=True)
print(f"\n{wins}/6 reached 0x61", flush=True)
emu.close()
