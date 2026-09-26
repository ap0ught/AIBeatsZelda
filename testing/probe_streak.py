"""Does the fight planner work the ten-kill streak for bombs? Runs a chain of fight rooms from a run-3 state and
prints the streak counter ($50), bombs and rupees after each room."""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import random, sys
import fullgame as fg
from zelda import runner, lookahead
from zelda.emulator import BizHawk
from zelda.overworld import Navigator, LinkDied
from zelda.search import Recorder

first, count = sys.argv[1], int(sys.argv[2])
lookahead.BOMB_TARGET[0] = int(sys.argv[3]) if len(sys.argv) > 3 else 6
segs = fg.segments(); names = [s[0] for s in segs]; k = names.index(first)
emu = BizHawk(log_name="probe_streak.log", clean_sram=False); nav = Navigator(emu)
s0 = emu.load(f"ckpt_fullgame_{names[k-1]}"); runner.SEG_START = s0
print(f"start before {first}: bombs {s0.bombs} rupees {s0.rupees} hearts {s0.hearts} streak {emu.byte(0x50)}")
for i in range(k, k + count):
    runner.SEG_START = emu.state()
    rec = Recorder(emu); rec.step((), 2); nav.blocked = {}
    try:
        out = segs[i][1](nav)(emu, rec, random.Random(1000), 3000)
    except LinkDied:
        out = "died"
    except Exception as e:
        out = f"{type(e).__name__}: {str(e)[:50]}"
    s = emu.state()
    good = out != "died" and segs[i][2](emu, s)
    print(f"  {names[i]:12s} {str(out)[:26]:28s} {len(rec.inputs):5d} fr ok={good} bombs {s.bombs} rupees {s.rupees} "
          f"hearts {s.hearts} streak {emu.byte(0x50)} bombflag {emu.byte(0x51)}", flush=True)
    if not good:
        break
emu.close()
