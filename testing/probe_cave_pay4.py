"""Measure 0x67 properly: walk onto the money, do not wait to be told it is there.

The screenshot settled what this cave is - "IT'S A SECRET TO EVERYBODY", the old man who hands over
rupees - and it also showed why three probes read +0: Link walks in at the BOTTOM of the cave, the
payment sits in the middle, and `read_room_item` returns None for these old-man gifts, so the probes
never took a step toward it.

So walk north until the rupee counter moves, and only then decide what the cave is worth.

(For contrast, screen 0x1A is now known to be the opposite kind: "PAY ME AND I'LL TALK", -5/-10/-20.
It takes money. It is not an income source and the route must not walk into it.)
"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
from zelda.emulator import BizHawk
from zelda.overworld import Navigator, NavError, LinkDied
from zelda import bot, secrets

CKPT, STAND, FACE = "ckpt_fullgame_w8_67", (112, 93), "Up"

emu = BizHawk(log_name="probe_cave_pay4.log", clean_sram=False)
nav = Navigator(emu)
s = emu.load(CKPT); s = emu.wait(4)
before = emu.byte(0x66D)
print(f"start: {s} | rupees {before} bombs {s.bombs}", flush=True)
try:
    nav.go(lambda x, y: (x, y) == STAND, "the bombing spot", max_replans=40)
    emu.step(FACE, 2)
    if not bot.select_b_item(emu, emu.step, bot.B_BOMBS):
        raise SystemExit("could not select bombs")
    emu.step("B", 2)
    for _ in range(90):
        emu.step((), 1)
    print("opening:", secrets.opening(emu), "| state:", emu.state(), flush=True)

    st = emu.state()
    for _ in range(240):                       # into the mouth
        if st.mode in (0x0B, 0x10):
            break
        st = emu.step("Up", 1)
    for _ in range(400):                       # let the cave finish loading
        st = emu.state()
        if st.mode == 0x0B and st.y > 150:
            break
        emu.step((), 2)
    print("inside at:", emu.state(), flush=True)

    # Walk north up the middle. The old man stands at the top; his payment sits between him and Link.
    for i in range(400):
        st = emu.state()
        if emu.byte(0x66D) != before:
            print(f"   money at frame +{i}: {emu.byte(0x66D)}", flush=True)
            break
        if st.x < 116:
            emu.step("Right", 1)
        elif st.x > 124:
            emu.step("Left", 1)
        elif st.y > 140:
            emu.step("Up", 1)
        else:
            emu.step((), 1)
    for _ in range(120):
        emu.step((), 1)
    after = emu.byte(0x66D)
    print(f"RUPEES {before} -> {after}  (+{after - before})", flush=True)
    print("state:", emu.state(), flush=True)
    print("shot:", emu.screenshot("cave67_final"), flush=True)
except (NavError, LinkDied) as e:
    print(f"FAILED: {type(e).__name__}: {str(e)[:120]}", flush=True)
emu.close()
