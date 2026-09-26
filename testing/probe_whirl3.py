"""Trace ONE seed of whirl_to_policy frame by frame: every room/mode/level change and every B
press, so the 0x42 failure can be seen instead of inferred."""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import random
import fullgame
from zelda.emulator import BizHawk
from zelda.overworld import Navigator
try:
    from zelda.search import Recorder
except ImportError:
    from zelda.runner import Recorder

emu = BizHawk(log_name="probe_whirl3.log", clean_sram=False)
nav = Navigator(emu)
emu.load("ckpt_fullgame_x9_out"); emu.wait(2)
rec = Recorder(emu)
real_step = rec.step
seen = {"key": None, "n": 0}
def traced(buttons=(), frames=1):
    s = real_step(buttons, frames)
    seen["n"] += frames
    b = buttons if isinstance(buttons, str) else ",".join(buttons)
    key = (s.room, s.mode, s.level)
    if key != seen["key"] or b == "B":
        print(f"  f+{seen['n']:5d} {b or '-':6s} -> room {s.room:02X} mode {s.mode:02X} "
              f"L{s.level} ({s.x},{s.y}) hp {s.hearts} B-item {emu.byte(0x656)}", flush=True)
        seen["key"] = key
    return s
rec.step = traced
out = fullgame.whirl_to_policy(nav, 0x37, counter=0x0B)(emu, rec, random.Random(1000), 3000)
print("OUTCOME:", out, "|", emu.state(), flush=True)
print("shot:", emu.screenshot("whirl3_end"), flush=True)
emu.close()
