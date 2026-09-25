"""0x62's 100-rupee tree, second try with the geometry the ROM gives: the tree is at (128,96) and the
flame only reaches it from (96,93) facing Right (west half) - the sweep's (112,93) misses by 16 px.
From Level 7's pond screen side: 0x52 -> down at x=80 into the west pocket -> burn -> cave -> back up."""
import random

import fullgame as fg
from zelda.emulator import BizHawk
from zelda.overworld import Navigator
from zelda.search import Recorder
from zelda.segments import make_cross_at_policy, make_cross_policy

emu = BizHawk(log_name="probe_cave_62b.log", clean_sram=False)
nav = Navigator(emu)
for seed in range(2):
    emu.load("ckpt_fullgame_w8_52")
    steps = [("down at 80", lambda: make_cross_at_policy(nav, "Down", at=80), lambda s: s.room == 0x62),
             ("burn 62", lambda: fg.burn_cave_policy(nav, (96, 93), "Right"), lambda s: s.mode == 5 and s.level == 0),
             ("back up", lambda: make_cross_policy(nav, "Up"), lambda s: s.room == 0x52),
             ("down at 160", lambda: make_cross_at_policy(nav, "Down", at=160), lambda s: s.room == 0x62 and s.x >= 140),
             ("right to 63", lambda: make_cross_policy(nav, "Right"), lambda s: s.room == 0x63)]
    r0 = emu.state().rupees
    total = 0
    for label, make, good in steps:
        rec = Recorder(emu)
        try:
            out = make()(emu, rec, random.Random(seed + 11), 3000)
        except Exception as e:
            out = f"{type(e).__name__}: {str(e)[:40]}"
        s = emu.state()
        total += len(rec.inputs)
        ok = s.hearts > 0 and good(s)
        print(f"seed {seed} {label:12s} {str(out)[:26]:28s} -> {s.room:02X} ({s.x:3d},{s.y:3d}) {len(rec.inputs):5d} fr "
              f"rupees {s.rupees} hearts {s.hearts} {'OK' if ok else 'WRONG'}", flush=True)
        if not ok:
            print("shot:", emu.screenshot(f"cave62b_{seed}_{label.replace(' ', '_')}"), flush=True)
            break
    print(f"seed {seed}: {total} frames, rupees {r0} -> {emu.state().rupees}", flush=True)
emu.close()
