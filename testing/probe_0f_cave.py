"""0x0F reached (hold Up at x=128 on 0x1F - the navigator thinks that rock is solid). Now find the
100-rupee cave on it, walk in, and read the payout."""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
from zelda.emulator import BizHawk
from zelda.overworld import Navigator, NavError, LinkDied, read_cells
from zelda import secrets

emu = BizHawk(log_name="probe_0f_cave.log", clean_sram=False)
nav = Navigator(emu)
emu.load("ckpt_fullgame_l5w03_2d"); emu.wait(4)
s = nav.exit_screen("Up", at=120); s = nav.exit_screen("Right"); s = nav.exit_screen("Right")
try:
    nav.go(lambda x, y: x == 128 and y <= 93, "the top at x=128", optimistic=True, max_replans=40)
except (NavError, LinkDied):
    pass
st = emu.state()
for _ in range(160):
    if st.room != 0x1F:
        break
    st = emu.step("Up", 1)
for _ in range(60):
    emu.step((), 1)
s = emu.state()
before = emu.byte(0x66D)
print(f"on {s.room:02X} at ({s.x},{s.y}) hearts {s.hearts} rupees {before}", flush=True)
op = secrets.opening(emu)
print("opening detector:", op, flush=True)
cells = read_cells(emu)
for r in range(11):
    print(f"  {r:2d} " + " ".join(f"{cells[r*2][c*2]:02X}" for c in range(16)), flush=True)
print("shot:", emu.screenshot("probe_0f_screen"), flush=True)
if op:
    tx, ty = op
    for _ in range(400):
        st = emu.state()
        if st.mode in (0x0B, 0x10):
            break
        dx, dy = tx - st.x, ty - st.y
        st = emu.step(("Right" if dx > 0 else "Left") if abs(dx) > 2 else ("Down" if dy > 0 else "Up"), 1)
    for _ in range(400):
        st = emu.state()
        if st.mode == 0x0B and st.y > 150:
            break
        emu.step((), 2)
    for _ in range(120):
        emu.step((), 1)
    print("inside:", emu.state(), flush=True)
    print("shot:", emu.screenshot("probe_0f_inside"), flush=True)
    for _ in range(400):
        st = emu.state()
        if emu.byte(0x66D) != before:
            break
        emu.step("Right" if st.x < 116 else "Left" if st.x > 124 else ("Up" if st.y > 140 else ()), 1)
    for _ in range(90):
        emu.step((), 1)
    print(f"RUPEES {before} -> {emu.byte(0x66D)} (+{emu.byte(0x66D) - before})", flush=True)
emu.close()
