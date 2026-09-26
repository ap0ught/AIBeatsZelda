"""Overworld bombs: stop waiting when the rock OPENS, not after a fixed count.

bomb_entry_policy (Level 9's door) stood for 160 frames after laying the bomb and secret_cave_policy for 150;
the doorway appears about 90-100 frames after the B press. On Spectacle Rock that is a second of standing
among Lynels for nothing. Poll the tiles instead (the fixed count stays as the upper bound)."""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import pathlib

p = pathlib.Path("fullgame.py")
t = p.read_text(encoding="utf-8")

old1 = """                rec.step(face, 1)
                rec.step("B", 2)
                rec.step((), 160)
            st = emu.state()
            for _ in range(300):
                if st.level == level or st.mode not in (5, 9):
                    break
"""
new1 = """                rec.step(face, 1)
                rec.step("B", 2)
                for i in range(160):
                    rec.step((), 1)
                    if i >= 40 and i % 2 == 0 and read_cells(emu)[r8][c8] == 0x24:
                        break                      # the rock is open: go, do not stand among the Lynels
            st = emu.state()
            for _ in range(300):
                if st.level == level or st.mode not in (5, 9):
                    break
"""
assert t.count(old1) == 1
t = t.replace(old1, new1)

old2 = """                    rec.step(face, 1)
                    rec.step("B", 2)
                    for _ in range(150):
                        rec.step((), 1)
            st = emu.state()
            for _ in range(400):                               # onto the staircase
"""
new2 = """                    rec.step(face, 1)
                    rec.step("B", 2)
                    for i in range(150):
                        rec.step((), 1)
                        if i >= 40 and i % 2 == 0 and secrets.opening(emu, base) is not None:
                            break                  # the cave mouth is drawn: stop waiting for the smoke
            st = emu.state()
            for _ in range(400):                               # onto the staircase
"""
assert t.count(old2) == 1
t = t.replace(old2, new2)
p.write_text(t, encoding="utf-8")
print("patched the two overworld bomb waits")
