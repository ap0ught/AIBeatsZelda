"""Finish the job on screen 0x67: bomb the wall, walk into the cave, and read the money.

Three probes have now confirmed the cave exists - the sweep opens it with a bomb from (112,93)
facing Up, and Link reaches mode 0x10 (entering a cave) at (112,84). What none of them measured is
the payout, because both cave policies bailed on their own success tests ("did not get the heart
container", "walked into a cave") before reading $066D.

So do it by hand: bomb, hold Up until the cave loads, look at what is on the floor, walk onto it,
and read the rupee counter.
"""
import random

from zelda.emulator import BizHawk
from zelda.overworld import Navigator, NavError, LinkDied, read_room_item
from zelda.search import Recorder
from zelda import bot

CKPT, STAND, FACE = "ckpt_fullgame_w8_67", (112, 93), "Up"

emu = BizHawk(log_name="probe_cave67b.log", clean_sram=False)
nav = Navigator(emu)
s = emu.load(CKPT); s = emu.wait(4)
before = emu.byte(0x66D)
print("start:", s, "| rupees", before, "bombs", s.bombs, flush=True)
rec = Recorder(emu)
orig = emu.step
try:
    emu.step = rec.step
    nav.go(lambda x, y: (x, y) == STAND, "the bombing spot", max_replans=40)
    rec.step(FACE, 2)
    if not bot.select_b_item(emu, rec.step, bot.B_BOMBS):
        raise SystemExit("could not select bombs")
    rec.step("B", 2)
    for _ in range(90):
        rec.step((), 1)
    print("after the bomb:", emu.state(), flush=True)

    st = emu.state()
    for _ in range(240):                       # walk north into the hole the bomb made
        if st.mode in (0x0B, 0x10):
            break
        st = rec.step("Up", 1)
    for _ in range(300):                       # let the cave finish loading
        st = emu.state()
        if st.mode == 0x0B:
            break
        rec.step((), 2)
    print("inside:", emu.state(), "| room item:", read_room_item(emu), flush=True)
    print("shot:", emu.screenshot("cave67_inside"), flush=True)

    item = read_room_item(emu)
    if item:
        _, ix, iy = item
        for _ in range(400):
            q = emu.state()
            if emu.byte(0x66D) != before:
                break
            dx, dy = ix - q.x, iy - q.y
            if abs(dx) <= 2 and abs(dy) <= 2:
                rec.step((), 1)
                continue
            rec.step(("Right" if dx > 0 else "Left") if abs(dx) >= abs(dy)
                     else ("Down" if dy > 0 else "Up"), 1)
    for _ in range(60):
        rec.step((), 1)
    after = emu.byte(0x66D)
    print(f"RUPEES {before} -> {after}  (+{after - before}) in {len(rec.inputs)} frames", flush=True)
    print("state:", emu.state(), flush=True)
    print("shot:", emu.screenshot("cave67_paid2"), flush=True)
except (NavError, LinkDied) as e:
    print(f"FAILED: {type(e).__name__}: {str(e)[:120]}", flush=True)
finally:
    emu.step = orig
emu.close()
