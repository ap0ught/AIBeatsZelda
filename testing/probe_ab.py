"""A/B a segment's policy from the finished run's own start state.

usage: python probe_ab.py [--seeds N] [--modes old,new] [--budget F] seg1 seg2 ...
Each segment starts from ckpt_fullgame_<previous segment> (the state the run really had there), runs the
segment's real factory from fullgame.segments() for N seeds per mode, and prints frames/hearts/success.
'old' sets zelda.overworld.OLD_AVOIDANCE (wide berth + waiting); 'new' is the current code."""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import random
import sys
import time

import fullgame
from zelda import overworld, runner, lookahead
from zelda.emulator import BizHawk
from zelda.overworld import LinkDied, Navigator
from zelda.search import Recorder

args = sys.argv[1:]
seeds = 4
modes = ["old", "new"]
budget = 3000
names_in = []
i = 0
while i < len(args):
    if args[i] == "--seeds":
        seeds = int(args[i + 1]); i += 2
    elif args[i] == "--modes":
        modes = args[i + 1].split(","); i += 2
    elif args[i] == "--budget":
        budget = int(args[i + 1]); i += 2
    else:
        names_in.append(args[i]); i += 1

segs = fullgame.segments()
names = [s[0] for s in segs]
emu = BizHawk(log_name="probe_ab.log", clean_sram=False)
nav = Navigator(emu)
totals = {m: [0, 0, 0.0] for m in modes}
for name in names_in:
    k = names.index(name)
    _, factory, success, tries = segs[k]
    state = f"ckpt_fullgame_{names[k - 1]}"
    for mode in modes:
        overworld.OLD_AVOIDANCE[0] = (mode == "old")
        lookahead.OLD_PLANNER[0] = (mode == "old")
        res = []
        for seed in range(seeds):
            s0 = emu.load(state)
            runner.SEG_START = s0
            rec = Recorder(emu)
            rec.step((), 2)
            nav.blocked = {}
            t0 = time.time()
            try:
                out = factory(nav)(emu, rec, random.Random(1000 + seed), budget)
            except LinkDied:
                out = "died"
            except Exception as e:
                out = f"{type(e).__name__}: {str(e)[:40]}"
            s = emu.state()
            ok = out != "died" and success(emu, s)
            res.append((ok, len(rec.inputs), s0.hearts - s.hearts, str(out)[:28], time.time() - t0))
        good = [r for r in res if r[0]]
        best = min(good, key=lambda r: r[1] + 600 * r[2]) if good else None
        line = " ".join(f"{'ok' if r[0] else 'XX'}:{r[1]}/{-r[2]:+.1f}" for r in res)
        print(f"{name:12s} {mode:3s} best {best[1] if best else '----':>5} ({(-best[2] if best else 0):+.1f}h) "
              f"ok {len(good)}/{seeds} | {line} | {sum(r[4] for r in res):.0f}s"
              + ("" if good else f" | {res[0][3]}"), flush=True)
        if best:
            totals[mode][0] += best[1]; totals[mode][1] += 1; totals[mode][2] += best[2]
print()
for m, (fr, n, h) in totals.items():
    print(f"TOTAL {m}: {fr} frames over {n} segments with a success, hearts lost {h:.1f}")
emu.close()
