"""Level 9 room 0x51 (Like Likes) -> north into 0x41. The plain crossing succeeded once in 18 attempts, in 4,081
frames (the first run: 591). Try the sword fighter and the damage-aware dash from the live run's state."""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import random

from zelda.emulator import BizHawk
from zelda.lookahead import Goal
from zelda.overworld import Navigator, read_enemies
from zelda.search import Recorder, make_cross_policy
from zelda.segments import make_lafight_policy, make_lareach_policy

emu = BizHawk(log_name="probe_g9_41.log", clean_sram=False)
nav = Navigator(emu)
emu.load("ckpt_fullgame_g9_51")
emu.step((), 20)
print("enemies:", sorted(f"{e[1]:02X}@({e[2]},{e[3]})" for e in read_enemies(emu)), flush=True)
VARIANTS = {"sword": lambda: make_lafight_policy(nav, "Up"),
            "dash": lambda: make_lareach_policy(nav, Goal(120, 77, 10), then_exit="Up"),
            "cross": lambda: make_cross_policy(nav, "Up")}
for name, make in VARIANTS.items():
    for seed in range(3):
        emu.load("ckpt_fullgame_g9_51")
        s0 = emu.state()
        rec = Recorder(emu)
        try:
            out = make()(emu, rec, random.Random(seed + 70), 5000)
        except Exception as e:
            out = f"{type(e).__name__}: {str(e)[:40]}"
        s = emu.state()
        ok = s.room == 0x41 and s.mode == 5 and s.hearts > 0
        print(f"{name:5s} seed {seed}: {str(out)[:26]:28s} -> {s.room:02X} {len(rec.inputs):5d} fr hearts {s0.hearts}->{s.hearts} "
              f"{'OK' if ok else 'WRONG'}", flush=True)
emu.close()
