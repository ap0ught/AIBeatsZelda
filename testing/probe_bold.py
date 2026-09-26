"""A/B: what a lost half heart costs the planners, on run 4's own rooms (states/run4).
usage: python probe_bold.py <seg[,seg...]> <mode[,mode...]> [seeds]
modes: name=dmg_scale:beam_premium:time_scale[:compound[:lazy_hold]]  e.g. base=1:1:1 comp=1:1:1:1:1"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import os, random, sys, time, json, pathlib
os.environ["ZELDA_ROUTE"] = "4"
import fullgame as fg
from zelda import runner, lookahead
from zelda.emulator import BizHawk
from zelda.overworld import Navigator, LinkDied
from zelda.search import Recorder

names_want = sys.argv[1].split(",")
modes = [(m.split("=")[0], [float(v) for v in m.split("=")[1].split(":")]) for m in sys.argv[2].split(",")]
seeds = int(sys.argv[3]) if len(sys.argv) > 3 else 6
segs = fg.segments(); names = [s[0] for s in segs]
tag = "_".join(names_want)[:40]
emu = BizHawk(log_name=f"probe_bold_{tag}.log", clean_sram=False); nav = Navigator(emu)
out_rows = []
for name in names_want:
    i = names.index(name)
    state = f"run4/ckpt_fullgame_{names[i - 1]}"
    kept = None
    try:
        a = json.load(open(f"logs/archive/fourth_run_20260919/checkpoints/fullgame_{names[i - 1]}.json"))["frames"]
        b = json.load(open(f"logs/archive/fourth_run_20260919/checkpoints/fullgame_{name}.json"))["frames"]
        kept = b - a
    except Exception:
        pass
    for mname, vals in modes:
        ds, bp, ts = vals[:3]
        lookahead.DMG_SCALE[0], lookahead.BEAM_PREMIUM[0], lookahead.TIME_SCALE[0] = ds, bp, ts
        lookahead.COMPOUND[0] = bool(vals[3]) if len(vals) > 3 else False
        lookahead.LAZY_HOLD[0] = bool(vals[4]) if len(vals) > 4 else False
        lookahead.FACE_FIRST[0] = bool(vals[5]) if len(vals) > 5 else False
        lookahead.COMPOUND_STEPS[0] = (8, 16, 24) if (len(vals) > 6 and vals[6]) else (8, 16)
        lookahead.IFRAME_SHAPING[0] = bool(vals[7]) if len(vals) > 7 else False
        from zelda import search as _srch
        _srch.DASH_CROSS[0] = vals[8] if len(vals) > 8 else 0.0
        res = []
        t0 = time.time()
        for seed in range(seeds):
            s0 = emu.load(state); runner.SEG_START = s0
            rec = Recorder(emu); rec.step((), 2); nav.blocked = {}
            try:
                out = segs[i][1](nav)(emu, rec, random.Random(1000 + seed), 3000)
            except LinkDied:
                out = "died"
            except Exception as e:
                out = type(e).__name__
            s = emu.state()
            good = out != "died" and bool(segs[i][2](emu, s))
            res.append((good, len(rec.inputs), s.hearts - s0.hearts, str(out)[:28]))
        ok = [r for r in res if r[0]]
        line = (f"{name:12s} kept {kept}  {mname:8s} ok {len(ok)}/{seeds}  best {min((r[1] for r in ok), default=0):5d}  "
                f"mean {sum(r[1] for r in ok) / max(1, len(ok)):6.0f}  hearts {sum(r[2] for r in ok) / max(1, len(ok)):+.2f}   "
                + " ".join(f"{r[1]}/{r[2]:+.1f}" if r[0] else f"XX[{r[3]}@{r[1]}]" for r in res) + f"   ({time.time() - t0:.0f}s)")
        print(line, flush=True)
emu.close()
