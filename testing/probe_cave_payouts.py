"""Measure the three pre-candle caves' payouts, reaching 0x0F the way the guide does.

The guide reaches 0x1D from BELOW (out of 0x2D), then right twice to 0x1F, then up to 0x0F. Walking
east from 0x1C dead-ended - the entry point into 0x1D decides whether the path east exists.
Payout collection uses what four earlier probes taught: Link enters a cave at the bottom, the money
sits in the middle, and the item slot reads empty for an old man's gift - so walk north and watch $066D.
"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
from zelda.emulator import BizHawk
from zelda.overworld import Navigator, NavError, LinkDied
from zelda import bot, secrets

emu = BizHawk(log_name="probe_cave_payouts.log", clean_sram=False)
nav = Navigator(emu)


def walk_in_and_take(tag):
    before = emu.byte(0x66D)
    st = emu.state()
    for _ in range(300):
        if st.mode in (0x0B, 0x10):
            break
        opening = secrets.opening(emu)
        if opening is None:
            break
        tx, ty = opening
        dx, dy = tx - st.x, ty - st.y
        st = emu.step(("Right" if dx > 0 else "Left") if abs(dx) > 2 else ("Down" if dy > 0 else "Up"), 1)
    for _ in range(400):
        st = emu.state()
        if st.mode == 0x0B and st.y > 150:
            break
        emu.step((), 2)
    if emu.state().mode != 0x0B:
        print(f"   [{tag}] never got inside: {emu.state()}", flush=True)
        return
    for i in range(400):
        st = emu.state()
        if emu.byte(0x66D) != before:
            break
        emu.step("Right" if st.x < 116 else "Left" if st.x > 124 else ("Up" if st.y > 140 else ()), 1)
    for _ in range(90):
        emu.step((), 1)
    after = emu.byte(0x66D)
    print(f"   [{tag}] RUPEES {before} -> {after}  (+{after - before})", flush=True)
    print("   shot:", emu.screenshot(f"payout_{tag}"), flush=True)


def push_open(stand, face):
    nav.go(lambda x, y: (x, y) == stand, "the Armos", max_replans=40)
    for _ in range(140):
        emu.step(face, 1)


def bomb_open(stand, face):
    nav.go(lambda x, y: (x, y) == stand, "the rock", max_replans=40)
    emu.step(face, 2)
    bot.select_b_item(emu, emu.step, bot.B_BOMBS)
    emu.step("B", 2)
    for _ in range(90):
        emu.step((), 1)


for tag, ckpt, opener in (
    ("3d_armos", "ckpt_fullgame_l5w02_3d", lambda: push_open((144, 109), "Down")),
    ("2d_bomb",  "ckpt_fullgame_l5w03_2d", lambda: bomb_open((112, 77), "Left")),
):
    print(f"\n== {tag} ==", flush=True)
    try:
        emu.load(ckpt); emu.wait(4)
        opener()
        print("   opening:", secrets.opening(emu), flush=True)
        walk_in_and_take(tag)
    except (NavError, LinkDied) as e:
        print(f"   FAILED: {type(e).__name__}: {str(e)[:90]}", flush=True)

print("\n== 0x0F, the guide's way: 0x2D up, right, right, up ==", flush=True)
try:
    emu.load("ckpt_fullgame_l5w03_2d"); emu.wait(4)
    for d in ("Up", "Right", "Right", "Up"):
        s = nav.exit_screen(d)
        print(f"   {d:5s} -> {s.room:02X} at ({s.x},{s.y}) hearts {s.hearts}", flush=True)
    print("   opening on arrival:", secrets.opening(emu), flush=True)
    print("   shot:", emu.screenshot("payout_0f_arrive"), flush=True)
    walk_in_and_take("0f_walkin")
except (NavError, LinkDied) as e:
    print(f"   FAILED: {type(e).__name__}: {str(e)[:90]}", flush=True)
emu.close()
