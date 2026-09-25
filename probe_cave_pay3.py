"""Measure the two caves that could pay for the arrows.

Tool timing decides everything here (knowledge/rupee_caves.md): the candle arrives in Level 7, but
the 80 rupees for arrows must be spent before Level 6. So only caves Link can open EARLY count:

  0x1A - the sweep found a PUSH secret at (96,141) facing Up. Pushing needs no item at all, and the
         route already crosses this screen twice in the Level 4 travel chain. If it pays, the first
         farm - 37,421 frames, about ten minutes of the finished video - simply disappears.
  0x67 - a BOMB secret at (112,93) facing Up. Bombs arrive early too. Three probes have opened it
         and got Link to the mouth, but none has read the payout: both cave policies bail on their
         own success tests first, and the last one looked for the floor item before the cave had
         finished loading.

This one does it by hand and slowly: open, walk in, WAIT for the room to settle, then read what is
on the floor and walk onto it, watching $066D.
"""
import sys

from zelda.emulator import BizHawk
from zelda.overworld import Navigator, NavError, LinkDied, read_room_item
from zelda import bot, secrets

# (checkpoint, screen, method, stand, face)
TARGETS = [
    ("ckpt_fullgame_l4w00_1a", 0x1A, "push", (96, 141), "Up"),
    ("ckpt_fullgame_w8_67",    0x67, "bomb", (112, 93), "Up"),
]


def open_it(emu, nav, method, stand, face):
    nav.go(lambda x, y: (x, y) == stand, "the spot", max_replans=40)
    emu.step(face, 2)
    if method == "bomb":
        if not bot.select_b_item(emu, emu.step, bot.B_BOMBS):
            return None
        emu.step("B", 2)
        for _ in range(90):
            emu.step((), 1)
    else:                                   # push: lean on the block until it shifts
        for _ in range(140):
            emu.step(face, 1)
    return secrets.opening(emu)


def take(emu, before):
    """Walk in, let the cave load, then walk onto whatever is lying there."""
    st = emu.state()
    for _ in range(240):
        if st.mode in (0x0B, 0x10):
            break
        st = emu.step("Up", 1)
    for _ in range(400):                    # the cave fades in; the item appears late
        st = emu.state()
        if st.mode == 0x0B and st.y > 100:
            break
        emu.step((), 2)
    for _ in range(120):                    # let the room settle before believing the item slot
        emu.step((), 1)
    item = read_room_item(emu)
    print(f"   inside: {emu.state()} | room item: {item}", flush=True)
    if item:
        _, ix, iy = item
        for _ in range(500):
            q = emu.state()
            if emu.byte(0x66D) != before:
                break
            dx, dy = ix - q.x, iy - q.y
            if abs(dx) <= 2 and abs(dy) <= 2:
                emu.step((), 1)
                continue
            emu.step(("Right" if dx > 0 else "Left") if abs(dx) >= abs(dy)
                     else ("Down" if dy > 0 else "Up"), 1)
    for _ in range(90):
        emu.step((), 1)
    return emu.byte(0x66D)


emu = BizHawk(log_name="probe_cave_pay3.log", clean_sram=False)
nav = Navigator(emu)
for ckpt, screen, method, stand, face in TARGETS:
    try:
        s = emu.load(ckpt); s = emu.wait(4)
    except Exception as e:
        print(f"== {screen:02X}: cannot load {ckpt}: {str(e)[:70]}", flush=True)
        continue
    if s.room != screen or s.level:
        print(f"== {screen:02X}: {ckpt} stands on {s.room:02X} L{s.level}; skipping", flush=True)
        continue
    before = emu.byte(0x66D)
    print(f"\n== SCREEN {screen:02X}: {method} from {stand} facing {face} | "
          f"rupees {before}, bombs {s.bombs}, candle {emu.byte(0x65B)}", flush=True)
    try:
        spot = open_it(emu, nav, method, stand, face)
        print(f"   opening: {spot}", flush=True)
        after = take(emu, before)
        print(f"   RUPEES {before} -> {after}  (+{after - before})", flush=True)
        print("   shot:", emu.screenshot(f"paid3_{screen:02x}"), flush=True)
    except (NavError, LinkDied) as e:
        print(f"   FAILED: {type(e).__name__}: {str(e)[:110]}", flush=True)
    except Exception as e:
        print(f"   ERROR: {type(e).__name__}: {str(e)[:110]}", flush=True)
emu.close()
