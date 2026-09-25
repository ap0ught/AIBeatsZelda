"""Old planner vs new planner on open-room fights, from run 2's states (states/run2)."""
import random, sys, time
from zelda import overworld, lookahead, runner
from zelda.emulator import BizHawk
from zelda.overworld import Navigator, LinkDied
from zelda.search import Recorder
from zelda.segments import make_lafight_policy, make_clear_grab_policy
import fullgame as fg
CASES = {
    "l6_28": ("run2/ckpt_fullgame_l6_38", lambda nav: make_lafight_policy(nav, "Up"), lambda s: s.room == 0x28),
    "l5_rec_st": ("run2/ckpt_fullgame_l5_64", fg.clear_push_stairs_policy, lambda s: s.mode == 9),
    "l4_00": ("run2/ckpt_fullgame_l4_10", lambda nav: make_lafight_policy(nav, "Up"), lambda s: s.room == 0x00),
    "l1_72_key": ("run2/ckpt_fullgame_l1_72", lambda nav: make_clear_grab_policy(nav, "Right"), lambda s: s.room == 0x73),
    "r8_3f": ("run2/ckpt_fullgame_l8_3e", lambda nav: make_lafight_policy(nav, "Right"), lambda s: s.room == 0x3F),
    "l7_39": ("run2/ckpt_fullgame_l7_49", lambda nav: make_lafight_policy(nav, "Up"), lambda s: s.room == 0x39),
}
seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 4
emu = BizHawk(log_name="probe_fight_ab.log", clean_sram=False); nav = Navigator(emu)
for name, (state, make, good) in CASES.items():
    for mode in ("old", "new"):
        lookahead.OLD_PLANNER[0] = (mode == "old")
        res = []
        t0 = time.time()
        for seed in range(seeds):
            s0 = emu.load(state); runner.SEG_START = s0
            rec = Recorder(emu); rec.step((), 2); nav.blocked = {}
            try:
                out = make(nav)(emu, rec, random.Random(1000 + seed), 3000)
            except LinkDied:
                out = "died"
            except Exception as e:
                out = type(e).__name__
            s = emu.state()
            res.append((out != "died" and s.hearts > 0 and good(s), len(rec.inputs), s.hearts - s0.hearts))
        ok = [r for r in res if r[0]]
        print(f"{name:10s} {mode}: " + " ".join(f"{'ok' if r[0] else 'XX'}:{r[1]}/{r[2]:+.1f}" for r in res)
              + f"   mean ok {sum(r[1] for r in ok) / max(1, len(ok)):.0f}  ({time.time() - t0:.0f}s)", flush=True)
emu.close()
