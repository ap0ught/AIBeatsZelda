"""Does the new input-trimming in Run.segment actually cut dead air without breaking the segment?

Level 4's Gleeok is the test case the owner spotted: the search recorded 6,020 frames, and replaying
those inputs into MAIN clears the room at frame 2,336 - so about 3,684 frames of the finished video
are Link standing motionless after the boss is dead.

This re-runs that one segment through the real Run.segment path (search, play into MAIN, trim,
re-check success) from the checkpoint before it, and reports what the trim kept.

usage: python probe_trim.py [segment]      (default: gleeok)
"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import sys

import fullgame
from zelda.runner import Run

seg_name = sys.argv[1] if len(sys.argv) > 1 else "gleeok"
segs = fullgame.segments()
names = [s[0] for s in segs]
i = names.index(seg_name)
prev = names[i - 1]
name, factory, success, tries = segs[i]

print(f"testing '{seg_name}', resuming from checkpoint '{prev}'", flush=True)
with Run("fullgame", log=print) as run:
    run.stamp_segment_list(segs)
    run.allow_legacy = True                 # the checkpoints on disk are from the previous route
    if run.resume(prev) is None:
        raise SystemExit(f"no usable checkpoint for {prev}")
    before = len(run.main.inputs)
    s = run.segment(name, factory, success, tries=min(tries, 30), max_frames=3000, checkpoint=False)
    kept = len(run.main.inputs) - before
    print(f"\nRESULT: {seg_name} kept {kept} frames (the finished run recorded 6020 for gleeok)", flush=True)
    print("end state:", s, flush=True)
    print("success still holds:", bool(success(run.main, s)), flush=True)
    run.finish(verify=False)
