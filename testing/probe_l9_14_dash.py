"""Level 9 room 0x14: five Like Likes between the passage stairs and a LOCKED east door. The first run
killed them with arrows (1,402 frames, 23 rupees). A locked door never needs the room cleared, so try the
damage-aware dash to the door against the old bow fight, from the first run's own state."""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import random

import fullgame as fg
from zelda.emulator import BizHawk
from zelda.lookahead import Goal
from zelda.overworld import Navigator
from zelda.search import Recorder
from zelda.segments import make_lareach_policy

emu = BizHawk(log_name="probe_l9_14_dash.log", clean_sram=False)
nav = Navigator(emu)
VARIANTS = {
    "dash": lambda: make_lareach_policy(nav, Goal(208, 141, 10), then_exit="Right"),
    "bow":  lambda: fg.bow_fight_policy(nav, "Right"),
}
for name, make in VARIANTS.items():
    for seed in range(3):
        emu.load("ckpt_fullgame_l9_pass")
        s0 = emu.state()
        rec = Recorder(emu)
        try:
            out = make()(emu, rec, random.Random(seed), 3000)
        except Exception as e:
            out = f"{type(e).__name__}: {str(e)[:40]}"
        s = emu.state()
        ok = s.room == 0x15 and s.mode == 5 and s.hearts > 0
        print(f"{name:5s} seed {seed}: {str(out)[:30]:32s} -> {s.room:02X} {len(rec.inputs):5d} fr  hearts {s0.hearts}->{s.hearts} "
              f"rupees {s0.rupees}->{s.rupees} keys {s0.keys}->{s.keys} {'OK' if ok else 'WRONG'}", flush=True)
emu.close()
