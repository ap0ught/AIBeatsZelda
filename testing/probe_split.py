"""A/B: whole-room search vs staged (per-kill) search on route-4 fight rooms, from run 5's own states.
usage: ZELDA_SCOUTS=6 python probe_split.py <seg[,seg...]> <whole|split[,...]> [stage_tries] [stage_patience]"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import os, sys, time
os.environ["ZELDA_ROUTE"] = "4"
import fullgame as fg
from zelda import runner
from zelda.runner import Run

want = sys.argv[1].split(","); modes = sys.argv[2].split(",") if len(sys.argv) > 2 else ["whole", "split"]
if len(sys.argv) > 3: runner.STAGE_TRIES[0] = int(sys.argv[3])
if len(sys.argv) > 4: runner.STAGE_PATIENCE[0] = int(sys.argv[4])
segs = fg.segments(); names = [s[0] for s in segs]
log_lines = []
def log(*a):
    s = " ".join(str(x) for x in a)
    if s.startswith("[") or "stage" in s or "no success" in s:
        print("   ", s[:110], flush=True)
run = Run("probe_split", log=log)
run.open()
try:
    for seg in want:
        i = names.index(seg)
        prev = names[i - 1]
        for mode in modes:
            runner.SPLIT_FIGHTS[0] = (mode == "split")
            run.main.load(f"run5/ckpt_fullgame_{prev}")
            run.main.inputs = []
            n0 = 0
            t0 = time.time()
            try:
                s = run.segment(seg, segs[i][1], segs[i][2], tries=segs[i][3], max_frames=3000, checkpoint=False)
                ok = True
            except RuntimeError as e:
                s = run.main.state(); ok = False
            print(f"RESULT {seg:12s} {mode:5s} ok={ok} frames={len(run.main.inputs)} hearts={s.hearts} bombs={s.bombs} "
                  f"({time.time() - t0:.0f}s)", flush=True)
finally:
    run.close()
