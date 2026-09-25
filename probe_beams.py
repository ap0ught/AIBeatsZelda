"""A/B the sword-beam rollout on fight segments of the CURRENT run, from the state each one started in."""
import os, random, sys
os.environ["ZELDA_ROUTE"] = "4"
import fullgame as fg
from zelda import runner, lookahead
from zelda.emulator import BizHawk
from zelda.overworld import Navigator, LinkDied
from zelda.search import Recorder

names_wanted = sys.argv[1].split(",")
seeds = int(sys.argv[2]) if len(sys.argv) > 2 else 4
segs = fg.segments(); names = [s[0] for s in segs]
emu = BizHawk(log_name="probe_beams.log", clean_sram=False); nav = Navigator(emu)
for name in names_wanted:
    k = names.index(name)
    for mode in ("off", "on"):
        lookahead.BEAMS[0] = (mode == "on")
        res = []
        for seed in range(seeds):
            s0 = emu.load(f"ckpt_fullgame_{names[k-1]}"); runner.SEG_START = s0
            rec = Recorder(emu); rec.step((), 2); nav.blocked = {}
            try:
                out = segs[k][1](nav)(emu, rec, random.Random(1000 + seed), 3000)
            except LinkDied:
                out = "died"
            except Exception as e:
                out = type(e).__name__
            s = emu.state()
            good = out != "died" and bool(segs[k][2](emu, s))
            res.append((good, len(rec.inputs), s.hearts - s0.hearts))
        okr = [r for r in res if r[0]]
        print(f"{name:12s} hearts {s0.hearts}/{s0.containers} beams {mode:3s}: " + " ".join(f"{'ok' if g else 'XX'}:{f}/{dh:+.1f}" for g, f, dh in res)
              + f"   mean ok {sum(r[1] for r in okr) / max(1, len(okr)):.0f}", flush=True)
emu.close()
