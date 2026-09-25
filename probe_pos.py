import random, sys
import fullgame
from zelda import runner
from zelda.emulator import BizHawk
from zelda.overworld import Navigator, LinkDied
from zelda.search import Recorder
name = sys.argv[1]
segs = fullgame.segments(); names = [s[0] for s in segs]; k = names.index(name)
emu = BizHawk(log_name="probe_pos.log", clean_sram=False); nav = Navigator(emu)
s0 = emu.load(f"ckpt_fullgame_{names[k-1]}"); runner.SEG_START = s0
rec = Recorder(emu); rec.step((), 2)
raw = rec.step; log = []
def step(buttons=(), frames=1):
    s = raw(buttons, frames)
    log.append((len(rec.inputs), buttons if isinstance(buttons, str) else ",".join(buttons), s.x, s.y))
    return s
rec.step = step
try:
    out = segs[k][1](nav)(emu, rec, random.Random(1000), 3000)
except LinkDied:
    out = "died"
print("outcome", out)
last = None
for n, b, x, y in log[:400]:
    if (b, x, y) != last:
        print(f"  f{n:4d} {b:6s} ({x},{y})")
    last = (b, x, y)
emu.close()
