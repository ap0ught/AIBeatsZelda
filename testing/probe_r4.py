"""Walk a stretch of ROUTE 4 from any saved state, each segment judged by its own success test.
usage: ZELDA_ROUTE=4 python probe_r4.py <state> <first segment> <count> [seed]"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import os, random, sys
os.environ["ZELDA_ROUTE"] = "4"
import fullgame as fg
from zelda import runner
from zelda.emulator import BizHawk
from zelda.overworld import Navigator, LinkDied
from zelda.search import Recorder

state, first, count = sys.argv[1], sys.argv[2], int(sys.argv[3])
seed = int(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4].isdigit() else 0
segs = fg.segments(); names = [s[0] for s in segs]; k = names.index(first)
emu = BizHawk(log_name="probe_r4.log", clean_sram=False); nav = Navigator(emu)
s0 = emu.load(state); runner.SEG_START = s0
print(f"from {state}: L{s0.level} room {s0.room:02X} ({s0.x},{s0.y}) hearts {s0.hearts}/{s0.containers} bombs {s0.bombs} "
      f"keys {s0.keys} rupees {s0.rupees}")
total = 0
for i in range(k, min(len(segs), k + count)):
    runner.SEG_START = emu.state()
    rec = Recorder(emu); rec.step((), 2); nav.blocked = {}
    try:
        out = segs[i][1](nav)(emu, rec, random.Random(1000 + seed), 3000)
    except LinkDied:
        out = "died"
    except Exception as e:
        out = f"{type(e).__name__}: {str(e)[:60]}"
    s = emu.state()
    good = out != "died" and bool(segs[i][2](emu, s))
    total += len(rec.inputs)
    print(f"  {names[i]:13s} {str(out)[:34]:36s} {len(rec.inputs):5d} fr ok={good}  -> L{s.level} {s.room:02X} ({s.x},{s.y}) "
          f"hearts {s.hearts}/{s.containers} bombs {s.bombs} keys {s.keys} rupees {s.rupees}", flush=True)
    if not good:
        emu.screenshot(f"r4_{names[i]}")
        if "--continue" not in sys.argv:
            break
print("total", total, "frames")
emu.close()
