"""Which Level 6 rooms on the route hold which enemy types - the owner's "orange and blue ghosts" -
read from the object table a moment after each saved room entry (no inputs, just waiting)."""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
from collections import Counter

from zelda.emulator import BizHawk
from zelda.overworld import read_enemies

ROOMS = ["l6_7a", "l6_78", "l6_68", "l6_58", "l6_48", "l6_38", "l6_28", "r6_18", "l6_19", "l6_1a", "l6_1b",
         "l6_0b", "l6_b1b", "l6_b1a", "l6_b19", "l6_29", "l6_39", "l6_3a", "l6_1d", "l6_2d", "l6_2c"]
emu = BizHawk(log_name="probe_l6_enemies.log", clean_sram=False)
for name in ROOMS:
    try:
        emu.load(f"ckpt_fullgame_{name}")
    except Exception as e:
        print(f"{name:8s} no state ({e})", flush=True)
        continue
    seen = Counter()
    for _ in range(6):
        emu.step((), 10)
        for slot, t, x, y, hp in read_enemies(emu):
            seen[t] = max(seen[t], sum(1 for e in read_enemies(emu) if e[1] == t))
    s = emu.state()
    print(f"{name:8s} room {s.room:02X}: " + ", ".join(f"type {t:02X} x{n}" for t, n in sorted(seen.items())), flush=True)
emu.close()
