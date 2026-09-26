"""Run the real parallel search on one route-4 segment from run 4's state, printing every attempt.
usage: python probe_search.py <segment> [scouts] [tries]"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import os, sys, time
os.environ["ZELDA_ROUTE"] = "4"; os.environ["ZELDA_SEARCH_DEBUG"] = "1"
import fullgame as fg
from zelda import runner, search
from zelda.emulator import BizHawk
from zelda.overworld import Navigator
name = sys.argv[1]; k = int(sys.argv[2]) if len(sys.argv) > 2 else 3; tries = int(sys.argv[3]) if len(sys.argv) > 3 else 60
segs = fg.segments(); names = [s[0] for s in segs]; i = names.index(name)
state = f"run4/ckpt_fullgame_{names[i - 1]}"
scouts = [BizHawk(log_name=f"probe_search_{j}.log", clean_sram=False) for j in range(k)]
navs = [Navigator(e) for e in scouts]
runner.SEG_START = scouts[0].load(state)
free = name in runner.REFILL_SOON
search.HEARTS_FREE[0] = free
from zelda import lookahead
lookahead.CAUTION_OVERRIDE[0] = 0.12 if free else None
t0 = time.time()
best = search.parallel_search(scouts, navs, state, segs[i][1], segs[i][2], tries=max(tries, segs[i][3]), max_frames=3000, label=name, log=print)
print("BEST", best.frames if best else None, "hearts", best.hearts if best else None, f"{time.time() - t0:.0f}s")
for e in scouts: e.close()
