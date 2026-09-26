"""Validate grave_sword_policy's walk, push and cave entry on 0x21, inside the real policy.
No saved state has twelve heart containers, so the old man will refuse: the expected outcome is a
pickup failure INSIDE the cave (mode 0x0B), which proves everything before the pickup."""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import random
import fullgame
from zelda.emulator import BizHawk
from zelda.overworld import Navigator
try:
    from zelda.search import Recorder
except ImportError:
    from zelda.runner import Recorder

emu = BizHawk(log_name="probe_sword.log", clean_sram=False)
nav = Navigator(emu)
emu.load("ckpt_fullgame_bw3_31"); emu.wait(4)
s = nav.exit_screen("Up")
print("screen", f"{s.room:02X}", s, "containers", s.containers, flush=True)
emu.save("probe_on_21")
for seed in (1000, 1001, 1002):
    emu.load("probe_on_21"); emu.wait(2)
    rec = Recorder(emu)
    real = rec.step
    modes = set()
    def traced(buttons=(), frames=1, real=real, modes=modes):
        q = real(buttons, frames)
        modes.add(q.mode)
        return q
    rec.step = traced
    out = fullgame.grave_sword_policy(nav, need=0)(emu, rec, random.Random(seed), 3000)
    q = emu.state()
    print(f"seed {seed}: {out} | end {q} | reached cave mode 0x0B: {0x0B in modes}", flush=True)
    if 0x0B in modes:
        print("shot:", emu.screenshot(f"sword_probe_{seed}"), flush=True)
        break
emu.close()
