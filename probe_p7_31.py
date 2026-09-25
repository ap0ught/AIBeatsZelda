"""Overworld 0x32 -> 0x31 (the 'steps' screen on the way to the pond): what is on the screen, and what does
the reach planner do with it? Prints the map, the enemies and a position trace."""
import random
import sys
from zelda import lookahead, overworld
from zelda.emulator import BizHawk
from zelda.overworld import Navigator, read_cells, read_enemies, TileKB, legal, harm_halfhearts
from zelda.search import Recorder
from zelda.segments import make_lareach_policy
from zelda.lookahead import Goal

state = sys.argv[1] if len(sys.argv) > 1 else "ckpt_fullgame_p7_32"
emu = BizHawk(log_name="probe_p7_31.log", clean_sram=False)
nav = Navigator(emu)
s0 = emu.load(state)
print("start", s0.room, s0.x, s0.y, s0.hearts)
cells = read_cells(emu)
kb = TileKB(); kb.use(s0.level, s0.mode)
for r in range(22):
    print("".join("." if cells[r][c] in kb.walkable else "#" if cells[r][c] in kb.solid else "?" for c in range(32)),
          " ".join(f"{cells[r][c]:02x}" for c in range(0, 32, 2)))
print("enemies:", [(e[0], hex(e[1]), e[2], e[3], hex(e[4]), harm_halfhearts(e[1])) for e in read_enemies(emu)])
rec = Recorder(emu)
trace = []
orig_step = rec.step


def step(buttons, n=1):
    s = orig_step(buttons, n)
    if len(rec.inputs) // 30 != (len(rec.inputs) - n) // 30:
        trace.append((len(rec.inputs), s.x, s.y, s.hearts, buttons if isinstance(buttons, str) else tuple(buttons)))
    return s


rec.step = step
pol = make_lareach_policy(nav, Goal(16, 117, 10), then_exit="Left")
out = pol(emu, rec, random.Random(1000), 3000)
print("result", out, "frames", len(rec.inputs), "hearts", emu.state().hearts)
for t in trace:
    print("  ", t)
emu.close()
