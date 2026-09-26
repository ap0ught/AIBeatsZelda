"""Run a segment's policy from the CURRENT run's checkpoint state (states/ckpt_fullgame_<prev>) with notes."""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import random, sys
import fullgame
from zelda import runner, search, lookahead
from zelda.emulator import BizHawk
from zelda.overworld import Navigator, LinkDied
from zelda.search import Recorder
PREFIX = "run2/" if "--run2" in sys.argv else ""
name = sys.argv[1]; seeds = int(sys.argv[2]) if len(sys.argv) > 2 else 4; show = "--notes" in sys.argv
segs = fullgame.segments(); names = [s[0] for s in segs]; k = names.index(name)
free = name in runner.REFILL_SOON
search.HEARTS_FREE[0] = free; lookahead.CAUTION_OVERRIDE[0] = 0.12 if free else None
emu = BizHawk(log_name="probe_new_seg2.log", clean_sram=False); nav = Navigator(emu)
for seed in range(seeds):
    s0 = emu.load(f"{PREFIX}ckpt_fullgame_{names[k-1]}"); runner.SEG_START = s0
    rec = Recorder(emu); rec.step((), 2); nav.blocked = {}
    n0 = len(emu.events)
    try:
        out = segs[k][1](nav)(emu, rec, random.Random(1000 + seed), 3000)
    except LinkDied:
        out = "died"
    except Exception as e:
        out = f"{type(e).__name__}: {str(e)[:60]}"
    s = emu.state()
    print(f"seed {seed}: {str(out)[:40]:42s} frames {len(rec.inputs):5d} ok {bool(out != 'died' and segs[k][2](emu, s))} hearts {s0.hearts}->{s.hearts} bombs {s0.bombs}->{s.bombs} keys {s0.keys}->{s.keys} room {s.room:02X}", flush=True)
    if show:
        for fr, txt in emu.events[n0:][-70:]:
            print(f"      {fr - s0.frame:5d}  {txt[:140]}")
emu.close()
