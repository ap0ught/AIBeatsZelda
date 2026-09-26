"""Level 4 room 21 (dark, water): where can Link stand, and where would he bomb the north wall from?"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import random
from zelda import bot, runner
from zelda.emulator import BizHawk
from zelda.overworld import Navigator, read_cells, TileKB
from zelda.lookahead import Lattice
from zelda.search import Recorder, make_cross_policy

emu = BizHawk(log_name="probe_l4_21.log", clean_sram=False)
nav = Navigator(emu)
s0 = emu.load("ckpt_fullgame_l4_b31"); runner.SEG_START = s0
rec = Recorder(emu); rec.step((), 2)
print(make_cross_policy(nav, "Up")(emu, rec, random.Random(1000), 3000), len(rec.inputs))
s = emu.state()
print("in room", hex(s.room), "at", s.x, s.y, "ladder flag", emu.byte(0x663))
cells = read_cells(emu)
lat = Lattice(emu)
for y in range(61, 206, 8):
    print("".join("L" if (x, y) == ((s.x + 4) // 8 * 8, y) and abs(y - s.y) < 4 else "." if (x, y) in lat.free else "#" for x in range(0, 241, 8)), y)
print("tile rows (hex) for the room interior:")
for r in range(4, 18):
    print(" ".join(f"{cells[r][c]:02x}" for c in range(4, 28)))
try:
    print("bomb spot Up:", bot.bomb_spot(emu, "Up"))
except Exception as e:
    print("bomb_spot failed:", type(e).__name__, e)
emu.close()
