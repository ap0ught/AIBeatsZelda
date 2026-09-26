"""Ganon's room after the Triforce of Power: why does walking out north take 1,087 frames?"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import random
from zelda.emulator import BizHawk
from zelda.overworld import Navigator, read_enemies, read_cells
from zelda.lookahead import plan_reach, Goal, Lattice
from zelda.search import Recorder

emu = BizHawk(log_name="probe_g9_32.log", clean_sram=False)
nav = Navigator(emu)
s0 = emu.load("ckpt_fullgame_g9_power")
print("start", s0.room, s0.x, s0.y, "mode", s0.mode, "enemies", [(hex(e[1]), e[2], e[3]) for e in read_enemies(emu)])
lat = Lattice(emu)
print("lattice cells:", len(lat.free), "start on lattice:", lat.snap(s0.x, s0.y) in lat.free)
cells = read_cells(emu)
for r in range(22):
    print(" ".join(f"{cells[r][c]:02x}" for c in range(0, 32, 2)))
rec = Recorder(emu)
trace = []
orig_step = rec.step


def step(buttons, n=1):
    s = orig_step(buttons, n)
    trace.append((len(rec.inputs), s.x, s.y, buttons))
    return s


rec.step = step
res = plan_reach(emu, rec, Goal(120, 85, 6), max_frames=900, rng=random.Random(1000))
print("plan_reach:", res, "frames", len(rec.inputs), "at", emu.state().x, emu.state().y)
for t in trace[:12] + [("...",)] + trace[-6:]:
    print("  ", t)
# how long does Link stay frozen after the fanfare? hold Up from the checkpoint and watch
emu.load("ckpt_fullgame_g9_power")
first_move = None
p0 = None
for i in range(400):
    s = emu.step("Up", 1)
    if p0 is None:
        p0 = (s.x, s.y)
    if first_move is None and (s.x, s.y) != p0:
        first_move = i
        break
print("holding Up from the checkpoint: Link first moves at frame", first_move)
emu.close()
