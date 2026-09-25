"""Debug: run ONE stage search (first kill) on a segment from run 5's state, printing every attempt."""
import os, sys
os.environ["ZELDA_ROUTE"] = "4"; os.environ["ZELDA_SEARCH_DEBUG"] = "1"
import fullgame as fg
from zelda import runner, search, lookahead
from zelda.lookahead import enemy_hp_total, static_slots
from zelda.overworld import read_enemies
from zelda.emulator import BizHawk
from zelda.overworld import Navigator
name = sys.argv[1]; k = int(sys.argv[2]) if len(sys.argv) > 2 else 4
segs = fg.segments(); names = [s[0] for s in segs]; i = names.index(name)
state = f"run5/ckpt_fullgame_{names[i - 1]}"
scouts = [BizHawk(log_name=f"probe_stage_{j}.log", clean_sram=False) for j in range(k)]
navs = [Navigator(e) for e in scouts]
s0 = scouts[0].load(state); runner.SEG_START = s0
ignore = static_slots(scouts[0])
n0 = enemy_hp_total(scouts[0], None, ignore)[1]
print(f"start: hearts {s0.hearts}/{s0.containers}, {n0} killable:", [(e[1], e[2], e[3], e[4] >> 4) for e in read_enemies(scouts[0]) if lookahead.killable(e)])
lookahead.KILL_STAGE[0] = n0 - 1
def bonus(emu):
    s = emu.state()
    ens = [e for e in read_enemies(emu) if lookahead.killable(e) and e[0] not in ignore]
    hp = sum(e[4] >> 4 for e in ens); d = min((abs(e[2] - s.x) + abs(e[3] - s.y) for e in ens), default=0)
    return -20.0 * hp - 0.8 * d
search.EXTRA_VALUE[0] = bonus
room0 = s0.room
ok = lambda emu, s: s.hearts > 0 and s.room == room0 and s.mode == 5 and getattr(emu, "stage_count", 99) <= n0 - 1
best = search.parallel_search(scouts, navs, state, segs[i][1], ok, tries=40, max_frames=1500, label=name + "~k1", log=print, patience=14)
print("BEST", best.frames, best.hearts, best.bonus, "value", search.value_of(best, s0.containers))
for e in scouts: e.close()
