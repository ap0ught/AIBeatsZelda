"""Would the trim rule actually cut Gleeok's dead air? Test it against the recorded winner, cheaply.

Re-searching the fight to find out costs 27 minutes of wall clock. The archived run already contains
a 6,020-frame winner for that segment, and the question is only where the rule would cut it - so
replay those inputs and evaluate the segment's own success test frame by frame, exactly as
Run.segment now does: three confirmations, four frames apart, after frame 40.

Background: the first attempt at this refused to trim while any item lay on the floor, which the boss
drops the instant it dies - so the guard was true for precisely the window worth cutting.

usage: python probe_trim_rule.py [segment]      (default: gleeok)
"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import json
import sys

import fullgame
from zelda.emulator import BizHawk, LOGS_DIR

seg_name = sys.argv[1] if len(sys.argv) > 1 else "gleeok"
segs = fullgame.segments()
names = [s[0] for s in segs]
name, factory, success, tries = segs[names.index(seg_name)]
prev = names[names.index(seg_name) - 1]


def inputs_of(seg):
    p = LOGS_DIR / "checkpoints" / f"fullgame_{seg}.json"
    d = json.loads(p.read_text())
    return [tuple(b for b in l.split(",") if b) for l in d["inputs"]], d["frames"]


post, _ = inputs_of(seg_name)
_, pre_n = inputs_of(prev)
seg_inputs = post[pre_n:]
print(f"{seg_name}: {len(seg_inputs)} recorded frames (from the archived run)", flush=True)

emu = BizHawk(log_name="probe_trim_rule.log", clean_sram=False)
# The segment's own start state, and NO settle frames - one stray frame desyncs every input after it.
emu.load(f"fullgame_{seg_name}_start")

hits = cut = 0
first_true = None
for i, b in enumerate(seg_inputs):
    emu.step(b, 1)
    if i < 40 or i % 4:
        continue
    q = emu.state()
    ok = q.mode in (5, 9) and success(emu, q)
    if ok and first_true is None:
        first_true = i
    if ok:
        hits += 1
        if hits >= 3 and not cut:
            cut = i + 1
            break
    else:
        hits = 0

if cut:
    print(f"success first held at frame {first_true}; rule would cut at {cut}", flush=True)
    print(f"TRIM: {len(seg_inputs) - cut} frames of {len(seg_inputs)} "
          f"({(len(seg_inputs) - cut) / 60.0988:.1f} seconds of video)", flush=True)
    print("state at the cut:", emu.state(), flush=True)
    print("success holds there:", bool(success(emu, emu.state())), flush=True)
else:
    print("the rule would not trim this segment at all", flush=True)
emu.close()
