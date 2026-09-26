"""Validate secret_cave_policy itself - through a Recorder, exactly as the run would call it - on the
two on-route caves the re-route depends on. Earlier probes used ad-hoc code; this uses the policy."""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import random, time
import fullgame
from zelda.emulator import BizHawk
from zelda.overworld import Navigator
from zelda.search import Recorder

emu = BizHawk(log_name="probe_cave_policy.log", clean_sram=False)
nav = Navigator(emu)
CASES = [
    ("0x3D push", "ckpt_fullgame_l5w02_3d", (144, 109), "Down", "push"),
    ("0x2D bomb", "ckpt_fullgame_l5w03_2d", (112, 77), "Left", "bomb"),
]
for tag, ckpt, stand, face, method in CASES:
    pol = fullgame.secret_cave_policy(nav, stand, face, method, want=30)
    print(f"\n== {tag} ==", flush=True)
    for seed in range(3):
        t0 = time.time()
        emu.load(ckpt)
        rec = Recorder(emu); rec.step((), 2)
        r0 = emu.byte(0x66D)
        try:
            out = pol(emu, rec, random.Random(1000 + seed), 3000)
        except Exception as e:
            out = f"{type(e).__name__}: {str(e)[:40]}"
        s = emu.state()
        print(f"   seed {seed}: {str(out)[:30]:32s} rupees {r0}->{emu.byte(0x66D)}  {len(rec.inputs):5d} frames  "
              f"room {s.room:02X} mode {s.mode:02X} hearts {s.hearts}  {time.time()-t0:4.0f}s", flush=True)
emu.close()
