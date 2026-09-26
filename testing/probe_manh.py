import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import random
from zelda import runner, search, lookahead
from zelda.emulator import BizHawk
from zelda.overworld import Navigator, LinkDied
from zelda.search import Recorder
from zelda.boss import parts
from zelda.lookahead import plan_fight
emu = BizHawk(log_name="probe_manh.log", clean_sram=False); nav = Navigator(emu)
for mode, kw in (("free bombs c=1.0", dict(use_bombs="free")), ("free bombs c=0.4", dict(use_bombs="free"))):
    lookahead.CAUTION_OVERRIDE[0] = None if "1.0" in mode else 0.4
    for seed in range(4):
        s0 = emu.load("ckpt_fullgame_4c_bomb"); rec = Recorder(emu); rec.step((), 2)
        rng = random.Random(1000 + seed)
        rec.step((), rng.randint(0, 30)); rec.step("Right", 16)
        try:
            out = plan_fight(emu, rec, max_frames=2500, rng=rng, **kw)
        except LinkDied:
            out = "died"
        s = emu.state()
        print(f"{mode} seed {seed}: {out:8s} frames {len(rec.inputs):5d} hearts {s.hearts} bombs {s0.bombs}->{s.bombs} parts left {len(parts(emu))}", flush=True)
emu.close()
