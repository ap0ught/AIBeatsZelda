"""Screen 0x1A: the one cave that could pay for the arrows.

The tool timing is what makes this screen matter (knowledge/rupee_caves.md): the candle only arrives
in Level 7, but the 80 rupees for arrows must be spent before Level 6, because Gohma cannot be killed
without them. That rules out every burn cave. The ROM's overworld secret table marks 0x1A as 0x03 -
the value used by screens whose entrance is already drawn, needing no tool at all - and the route
already walks straight across it early, twice, in the Level 4 travel chain. If it pays, the first
farm (37,421 frames) can simply be deleted.

Measure, do not assume: the same table marks 0x0F, which turned out to be unreachable, and the
community map's 100 rupees on 0x62 turned out to be nothing at all.

usage: python probe_cave_1a.py [checkpoint]
"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import sys

from zelda.emulator import BizHawk
from zelda.overworld import Navigator, NavError, LinkDied, read_cells, read_room_item
from zelda import secrets

CKPT = sys.argv[1] if len(sys.argv) > 1 else "ckpt_fullgame_l4w00_1a"

emu = BizHawk(log_name="probe_cave1a.log", clean_sram=False)
nav = Navigator(emu)
s = emu.load(CKPT); s = emu.wait(4)
before = emu.byte(0x66D)
print(f"start: {s} | rupees {before} bombs {s.bombs} candle {emu.byte(0x65B)}", flush=True)

spot = secrets.opening(emu)
print("entrance already drawn?", spot, flush=True)
cells = read_cells(emu)
for r16 in range(11):
    print("   " + " ".join(f"{cells[r16*2][c16*2]:02X}" for c16 in range(16)), flush=True)
print("shot:", emu.screenshot("cave1a_screen"), flush=True)

if spot is None:
    # No mouth drawn. Try the tools Link actually has this early - bombs and pushing, never the
    # candle, which he will not own for another two dungeons.
    print("\nno drawn entrance; sweeping with bomb and push only", flush=True)
    print("sweep ->", secrets.sweep(emu, nav, methods=("bomb", "push")), flush=True)
else:
    tx, ty = spot
    print(f"\nwalking into the entrance at ({tx},{ty})", flush=True)
    try:
        nav.go(lambda x, y: abs(x - tx) <= 8 and y >= ty + 8, "below the cave mouth", max_replans=40)
        st = emu.state()
        for _ in range(240):
            if st.mode in (0x0B, 0x10):
                break
            st = emu.step("Up", 1)
        for _ in range(300):
            st = emu.state()
            if st.mode == 0x0B:
                break
            emu.step((), 2)
        print("inside:", emu.state(), "| room item:", read_room_item(emu), flush=True)
        print("shot:", emu.screenshot("cave1a_inside"), flush=True)
        item = read_room_item(emu)
        if item:
            _, ix, iy = item
            for _ in range(400):
                q = emu.state()
                if emu.byte(0x66D) != before:
                    break
                dx, dy = ix - q.x, iy - q.y
                if abs(dx) <= 2 and abs(dy) <= 2:
                    emu.step((), 1)
                    continue
                emu.step(("Right" if dx > 0 else "Left") if abs(dx) >= abs(dy)
                         else ("Down" if dy > 0 else "Up"), 1)
        for _ in range(60):
            emu.step((), 1)
        after = emu.byte(0x66D)
        print(f"RUPEES {before} -> {after}  (+{after - before})", flush=True)
        print("shot:", emu.screenshot("cave1a_paid"), flush=True)
    except (NavError, LinkDied) as e:
        print(f"FAILED: {type(e).__name__}: {str(e)[:120]}", flush=True)
emu.close()
