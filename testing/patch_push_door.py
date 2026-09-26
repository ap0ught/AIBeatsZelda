"""push_blocks_for_door: stop at the block that MOVES.

The owner saw it in Level 4: "link also pushes the wrong block after pushing the right block". The loop only
recognised success as a DOOR opening, so in a staircase room (the block uncovers stairs, no door changes) it
leaned on every candidate for the full 90 frames, the right one included, and never remembered which one it
was - Level 9's five stairs rooms paid ~150-200 frames each for that, every run. Now: poll the tile map while
pushing, stop the moment a block starts to slide, let it arrive (that is when the stairs or the door appear),
remember it, and try nothing else - a room only has one block that moves."""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import pathlib

p = pathlib.Path("zelda/overworld.py")
t = p.read_text(encoding="utf-8")
old = """            ee0 = emu.byte(0xEE)
            for _ in range(90):
                s = emu.step("Up", 1)
                if emu.byte(0xEE) != ee0:
                    break
            if emu.byte(0xEE) != ee0 or self._door_open(d):
                emu.note(f"That block did it: the {d} door is open")
                self.remember_block(s0.level, s0.room, br, bc, "Up")
                return True
        emu.note("No block opened the door")
        return False
"""
new = """            ee0 = emu.byte(0xEE)
            before = read_cells(emu)
            moved = False
            for i in range(90):
                s = emu.step("Up", 1)
                if emu.byte(0xEE) != ee0:
                    break
                if i >= 12 and i % 3 == 0:
                    now = read_cells(emu)
                    if any(now[r][c] != before[r][c] for r in range(22) for c in range(32)):
                        moved = True
                        break
            if moved:
                # it slid off its tile; what it hides (stairs, a door) shows when it ARRIVES
                sliding = read_cells(emu)
                for _ in range(40):
                    emu.step((), 1)
                    now = read_cells(emu)
                    if emu.byte(0xEE) != ee0 or any(now[r][c] != sliding[r][c] for r in range(22) for c in range(32)):
                        emu.step((), 2)
                        break
            if emu.byte(0xEE) != ee0 or self._door_open(d):
                emu.note(f"That block did it: the {d} door is open")
                self.remember_block(s0.level, s0.room, br, bc, "Up")
                return True
            if moved:
                # a room has one block that moves, and this was it: nothing else is worth leaning on
                emu.note(f"The block at ({bx},{by}) moved (no door opened: it hides something else)")
                self.remember_block(s0.level, s0.room, br, bc, "Up")
                return False
        emu.note("No block opened the door")
        return False
"""
assert t.count(old) == 1
p.write_text(t.replace(old, new), encoding="utf-8")
print("patched push_blocks_for_door")
