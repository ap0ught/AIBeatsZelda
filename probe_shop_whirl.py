"""After Level 5: whirlwind to Level 4's island (0x45), raft to 0x55, walk 65, 64, 54, 44 - the arrows shop.
Against 17 screens on foot from Level 5's door."""
import random, sys
import fullgame as fg
from zelda import runner
from zelda.emulator import BizHawk
from zelda.lookahead import Goal
from zelda.overworld import Navigator, LinkDied
from zelda.search import Recorder, make_cross_policy
from zelda.segments import make_lareach_policy
emu = BizHawk(log_name="probe_shop_whirl.log", clean_sram=False); nav = Navigator(emu)
STEPS = [
 ("whirl to 45", lambda: fg.whirl_to_policy(nav, 0x45), lambda s: s.room == 0x45 and s.mode == 5),
 ("sail",        lambda: fg.dock_policy(nav), lambda s: s.room == 0x55),
 ("land",        lambda: fg.settle_policy(nav, lambda q: q.y >= 125 and q.mode == 5), lambda s: s.room == 0x55 and s.y >= 125),
 ("shore",       lambda: make_lareach_policy(nav, Goal(160, 173, 8)), lambda s: s.room == 0x55 and s.y >= 157),
 ("down 65",     lambda: make_cross_policy(nav, "Down"), lambda s: s.room == 0x65),
 ("left 64",     lambda: make_cross_policy(nav, "Left"), lambda s: s.room == 0x64),
 ("up 54",       lambda: make_cross_policy(nav, "Up"), lambda s: s.room == 0x54),
 ("up 44",       lambda: make_cross_policy(nav, "Up"), lambda s: s.room == 0x44),
]
for seed in range(int(sys.argv[1]) if len(sys.argv) > 1 else 2):
    s0 = emu.load("run2/ckpt_fullgame_warp_L5")
    print(f"seed {seed}: room {s0.room:02X} idx {emu.byte(0x523)} tri {emu.byte(0x671):02X} hearts {s0.hearts}", flush=True)
    total = 0
    for label, make, good in STEPS:
        rec = Recorder(emu); rec.step((), 2); nav.blocked = {}
        try:
            out = make()(emu, rec, random.Random(1000 + seed), 3000)
        except LinkDied:
            out = "died"
        except Exception as e:
            out = f"{type(e).__name__}: {str(e)[:50]}"
        s = emu.state(); total += len(rec.inputs)
        ok = s.hearts > 0 and good(s)
        print(f"   {label:12s} {str(out)[:26]:28s} -> {s.room:02X} ({s.x},{s.y}) {len(rec.inputs):5d} fr hearts {s.hearts} {'OK' if ok else 'WRONG'}", flush=True)
        if not ok:
            break
    else:
        print(f"   CHAIN OK {total} frames", flush=True)
emu.close()
