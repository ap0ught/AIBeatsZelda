"""Level 9 room 0x20 -> bomb north into 0x10: fight first vs the route's walk-and-bomb, from the live run's own
state (s9_pass3: Link just surfaced in 0x20 with 11.5/12 hearts)."""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import random
import sys

import fullgame as fg
from zelda.emulator import BizHawk
from zelda.overworld import Navigator
from zelda.search import Recorder

emu = BizHawk(log_name="probe_s9_10.log", clean_sram=False)
nav = Navigator(emu)
VARIANTS = {"fight_first": lambda: fg.fight_then_bomb_policy(nav, "Up", 0x10),
            "walk_bomb": lambda: fg.open_or_bomb_policy(nav, "Up", 0x10)}
seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 4
for name, make in VARIANTS.items():
    for seed in range(seeds):
        emu.load("ckpt_fullgame_s9_pass3")
        s0 = emu.state()
        rec = Recorder(emu)
        try:
            out = make()(emu, rec, random.Random(seed + 50), 4000)
        except Exception as e:
            out = f"{type(e).__name__}: {str(e)[:40]}"
        s = emu.state()
        ok = s.room == 0x10 and s.mode == 5 and s.hearts > 0
        print(f"{name:11s} seed {seed}: {str(out)[:26]:28s} -> {s.room:02X} {len(rec.inputs):5d} fr hearts {s0.hearts}->{s.hearts} "
              f"bombs {s0.bombs}->{s.bombs} {'OK' if ok else 'WRONG'}", flush=True)
emu.close()
