"""Why won't the navigator leave Ganon's room? Look at the tiles, then try three ways out of it from
the state saved right after the Triforce of Power is taken."""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
from zelda.emulator import BizHawk
from zelda.overworld import Navigator, NavError, read_cells, read_enemies, BLOCK_IDS, DOOR_GOALS
from zelda.lookahead import plan_reach, Goal
from zelda.search import Recorder
import random

emu = BizHawk(log_name="probe_42_north.log", clean_sram=False)
nav = Navigator(emu)
s = emu.load("probe_ending_power"); s = emu.wait(2)
print("state:", s, flush=True)
print("objects:", [(e[0], hex(e[1]), e[2], e[3], e[4] >> 4) for e in read_enemies(emu)], flush=True)
cells = read_cells(emu)
for r16 in range(11):
    print(f"  {r16:2d} " + " ".join(f"{cells[r16*2][c16*2]:02X}" for c16 in range(16)), flush=True)
print("blocks:", sorted({(r // 2, c // 2) for r in range(22) for c in range(32) if cells[r][c] in BLOCK_IDS}), flush=True)

snap = emu.msave()
print("--- 1. nav.exit_screen('Up')", flush=True)
try:
    print("   ->", emu.state() if nav.exit_screen("Up") else "?", flush=True)
except (NavError, RuntimeError) as e:
    print("   NavError:", str(e)[:90], flush=True)

emu.mload(snap); emu.wait(2)
print("--- 2. plan_reach to the doorway, then hold Up", flush=True)
rec = Recorder(emu)
res = plan_reach(emu, rec, Goal(120, 85, 6), max_frames=900, rng=random.Random(7))
print("   plan_reach:", res, emu.state(), flush=True)
st = emu.state()
for _ in range(240):
    if st.room != 0x42:
        break
    st = emu.step("Up", 1)
print("   after holding Up:", emu.state(), flush=True)

emu.mload(snap); emu.wait(2)
print("--- 3. straight walk: x to 120, then Up", flush=True)
st = emu.state()
for _ in range(400):
    if st.x == 120:
        break
    st = emu.step("Right" if st.x < 120 else "Left", 1)
print("   at x:", emu.state(), flush=True)
for _ in range(400):
    if st.room != 0x42:
        break
    st = emu.step("Up", 1)
print("   after Up:", emu.state(), flush=True)
print("shot:", emu.screenshot("north_try"), flush=True)
emu.mfree(snap)
emu.close()
