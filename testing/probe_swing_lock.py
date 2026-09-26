"""How long does a sword swing really pin Link? Press A (the macro's way: face 1 frame, A for 2), then hold a
direction and see on which frame he first moves. Also: how short can the A press be, and when does the blade hit?"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import sys
from zelda.emulator import BizHawk
emu = BizHawk(log_name="probe_swing_lock.log", clean_sram=False)
state = sys.argv[1] if len(sys.argv) > 1 else "run4/ckpt_fullgame_l8_3e"
for a_frames in (1, 2):
    for face in (0, 1):
        s0 = emu.load(state)
        emu.step((), 2)
        s = emu.state()
        x0, y0 = s.x, s.y
        if face:
            emu.step("Right", 1)
        emu.step("A", a_frames)
        moved = None
        track = []
        for k in range(1, 30):
            s = emu.step("Left", 1)
            track.append((s.x, s.y))
            if moved is None and (s.x, s.y) != (x0 + (1 if face else 0), y0) and (s.x, s.y) != (x0, y0):
                moved = k
        print(f"A held {a_frames}f, face-first {face}: start ({x0},{y0}); first movement on frame {moved} after A released; "
              f"track {track[:16]}")
emu.close()
