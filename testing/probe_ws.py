"""White Sword cave screen (0x0A): where is the cave mouth, what does the approach do?"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import random
from zelda import bot
from zelda.emulator import BizHawk
from zelda.overworld import Navigator, read_enemies, read_cells, TileKB
from zelda.lookahead import plan_reach, Goal, Lattice
from zelda.search import Recorder

emu = BizHawk(log_name="probe_ws.log", clean_sram=False)
nav = Navigator(emu)
s0 = emu.load("ckpt_fullgame_ws_0a")
print("start", hex(s0.room), s0.x, s0.y, s0.hearts, "enemies", [(hex(e[1]), e[2], e[3]) for e in read_enemies(emu)])
spot = bot.find_entrance(emu)
print("entrance", spot)
kb = TileKB(); kb.use(s0.level, s0.mode)
cells = read_cells(emu)
for r in range(22):
    print("".join("." if cells[r][c] in kb.walkable else "#" if cells[r][c] in kb.solid else "?" for c in range(32)))
lat = Lattice(emu)
ex, ey = spot
gf = lat.field([(ex, ey + 16)])
print("goal", (ex, ey + 16), "nearest free", lat.nearest_free(ex, ey + 16), "start walk", lat.walk(gf, s0.x, s0.y, None))
rec = Recorder(emu)
trace = []
orig = rec.step


def step(b, n=1):
    s = orig(b, n)
    trace.append((len(rec.inputs), s.x, s.y, s.hearts, b))
    return s


rec.step = step
res = plan_reach(emu, rec, Goal(ex, ey + 16, 6), max_frames=1200, rng=random.Random(1000))
print("result", res, len(rec.inputs))
for t in trace[::6][:60]:
    print("  ", t)
emu.close()
