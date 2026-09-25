"""Run one segment's policy once from the finished run's state and print the navigator's notes."""
import random, sys
import fullgame
from zelda import overworld, runner
from zelda.emulator import BizHawk
from zelda.overworld import Navigator, LinkDied
from zelda.search import Recorder
name = sys.argv[1]; seed = int(sys.argv[2]) if len(sys.argv) > 2 else 0
segs = fullgame.segments(); names = [s[0] for s in segs]; k = names.index(name)
emu = BizHawk(log_name="probe_debug_seg.log", clean_sram=False); nav = Navigator(emu)
s0 = emu.load(f"ckpt_fullgame_{names[k-1]}"); runner.SEG_START = s0
rec = Recorder(emu); rec.step((), 2)
n0 = len(emu.events)
try:
    out = segs[k][1](nav)(emu, rec, random.Random(1000 + seed), 3000)
except LinkDied:
    out = "died"
s = emu.state()
print("outcome:", out, "| frames", len(rec.inputs), "| ok", segs[k][2](emu, s), "|", s)
for fr, txt in emu.events[n0:][-60:]:
    print(f"  {fr - s0.frame:5d}  {txt[:150]}")
emu.close()
