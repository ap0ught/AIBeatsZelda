"""Second pass at the two caves that did not open cleanly.

0x2D (30, bomb): the sweep found the spot (112,77) facing Left when Link arrived from 0x2C on the
left; arriving from below, the navigator could not reach it. Try the left arrival, and reach the spot
with the damage-aware planner rather than the navigator.

0x0F (100, no item): the guide goes 0x2D -> up to 0x1D -> right twice to 0x1F -> up. Leaving 0x2D
upward at the navigator's default column lands Link at x=32 on 0x1D, apparently in a pocket with no
way east. Try leaving 0x2D at a range of columns and see which arrival connects east.
"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import random
from zelda.emulator import BizHawk
from zelda.overworld import Navigator, NavError, LinkDied
from zelda.lookahead import plan_reach, Goal
from zelda.search import Recorder
from zelda import bot, secrets

emu = BizHawk(log_name="probe_caves2.log", clean_sram=False)
nav = Navigator(emu)


def collect(tag, before):
    st = emu.state()
    for _ in range(300):
        if st.mode in (0x0B, 0x10):
            break
        op = secrets.opening(emu)
        if op is None:
            break
        dx, dy = op[0] - st.x, op[1] - st.y
        st = emu.step(("Right" if dx > 0 else "Left") if abs(dx) > 2 else ("Down" if dy > 0 else "Up"), 1)
    for _ in range(400):
        st = emu.state()
        if st.mode == 0x0B and st.y > 150:
            break
        emu.step((), 2)
    if emu.state().mode != 0x0B:
        print(f"   [{tag}] did not get inside: {emu.state()}", flush=True); return
    for _ in range(400):
        st = emu.state()
        if emu.byte(0x66D) != before:
            break
        emu.step("Right" if st.x < 116 else "Left" if st.x > 124 else ("Up" if st.y > 140 else ()), 1)
    for _ in range(90):
        emu.step((), 1)
    print(f"   [{tag}] RUPEES {before} -> {emu.byte(0x66D)} (+{emu.byte(0x66D) - before})", flush=True)


print("== 0x2D: arrive from the left, reach (112,77) with the planner, bomb Left ==", flush=True)
try:
    emu.load("ckpt_fullgame_l5w04_2c"); emu.wait(4)
    s = nav.exit_screen("Right"); print(f"   arrived {s.room:02X} at ({s.x},{s.y})", flush=True)
    before = emu.byte(0x66D)
    rec = Recorder(emu)
    res = plan_reach(emu, rec, Goal(112, 77, 3), max_frames=900, rng=random.Random(3))
    st = emu.state(); print(f"   plan_reach: {res} -> ({st.x},{st.y})", flush=True)
    for _ in range(40):
        st = emu.state()
        if (st.x, st.y) == (112, 77):
            break
        emu.step(("Right" if st.x < 112 else "Left") if st.x != 112 else ("Down" if st.y < 77 else "Up"), 1)
    emu.step("Left", 2)
    bot.select_b_item(emu, emu.step, bot.B_BOMBS); emu.step("B", 2)
    for _ in range(90):
        emu.step((), 1)
    print("   opening:", secrets.opening(emu), flush=True)
    collect("2d", before)
except (NavError, LinkDied) as e:
    print(f"   FAILED: {type(e).__name__}: {str(e)[:90]}", flush=True)

print("\n== 0x0F: which column out of 0x2D connects 0x1D eastward? ==", flush=True)
for col in (56, 88, 120, 152, 184, 216):
    try:
        emu.load("ckpt_fullgame_l5w03_2d"); emu.wait(4)
        s = nav.exit_screen("Up", at=col)
        msg = f"   col {col:3d}: 1D at ({s.x},{s.y})"
        s = nav.exit_screen("Right"); msg += f" -> {s.room:02X}"
        s = nav.exit_screen("Right"); msg += f" -> {s.room:02X}"
        s = nav.exit_screen("Up"); msg += f" -> {s.room:02X} at ({s.x},{s.y}) hearts {s.hearts}"
        print(msg + "  REACHED", flush=True)
        print("   opening on 0x0F:", secrets.opening(emu), flush=True)
        print("   shot:", emu.screenshot("probe2_0f"), flush=True)
        collect("0f", emu.byte(0x66D))
        break
    except (NavError, LinkDied) as e:
        print(f"{msg if 'msg' in dir() else f'   col {col}'}  FAILED: {str(e)[:60]}", flush=True)
emu.close()
