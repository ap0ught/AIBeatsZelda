"""Live run against the archived fourth run (39:15), segment by segment. usage: python vs_run4.py [worst_n]"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import json, pathlib, sys
import os
ARCH = pathlib.Path(os.environ.get("ZELDA_VS", "logs/archive/fourth_run_20260919/checkpoints"))
LIVE = pathlib.Path("logs/checkpoints")
top = int(sys.argv[1]) if len(sys.argv) > 1 else 12
def table(d):
    rows = sorted(((json.load(open(f))["frames"], f.stem[9:]) for f in d.glob("fullgame_*.json")))
    out, prev = {}, 0
    for fr, n in rows:
        out[n] = (fr - prev, fr); prev = fr
    return out, [n for _, n in rows]
old, _ = table(ARCH)
new, order = table(LIVE)
if not order:
    print("no live checkpoints yet"); sys.exit()
last = order[-1]
d = [(new[n][0] - old[n][0], n, old[n][0], new[n][0]) for n in order if n in old]
cum = new[last][1] - old[last][1] if last in old else None
print(f"{len(order)} of {len(old)} segments done; at '{last}': run 5 = {new[last][1]} frames, run 4 = {old.get(last, (0, 0))[1]} "
      f"-> {cum:+d} frames ({cum / 60.0988:+.1f} s)")
print("biggest gains:", ", ".join(f"{n} {a}->{b}" for dd, n, a, b in sorted(d)[:top]))
print("biggest losses:", ", ".join(f"{n} {a}->{b}" for dd, n, a, b in sorted(d, reverse=True)[:top] if dd > 0))
