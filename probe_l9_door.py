"""Spectacle Rock (0x05): how long does the damage-aware planner take to reach the bombing spot, against the
plain navigator? From the current run's dm9_05 checkpoint."""
import random
import sys
from zelda.emulator import BizHawk
from zelda.overworld import Navigator, NavError, LinkDied, read_enemies
from zelda.lookahead import plan_reach, Goal
from zelda.search import Recorder

emu = BizHawk(log_name="probe_l9_door.log", clean_sram=False)
nav = Navigator(emu)
for mode in ("reach", "nav"):
    for seed in range(3):
        s0 = emu.load("ckpt_fullgame_dm9_05")
        rec = Recorder(emu)
        rec.step((), 2 + seed * 3)
        if seed == 0 and mode == "reach":
            print("start", s0.x, s0.y, "enemies", [(hex(e[1]), e[2], e[3]) for e in read_enemies(emu)])
        try:
            if mode == "reach":
                res = plan_reach(emu, rec, Goal(80, 173, 6), max_frames=4000, rng=random.Random(1000 + seed))
            else:
                orig = emu.step
                emu.step = rec.step
                try:
                    nav.go(lambda x, y: abs(x - 80) <= 6 and abs(y - 173) <= 6, "the bombing spot", optimistic=True,
                           max_replans=80)
                    res = "arrived"
                finally:
                    emu.step = orig
        except (NavError, LinkDied) as e:
            res = f"{type(e).__name__}: {str(e)[:50]}"
        s = emu.state()
        print(f"{mode} seed {seed}: {res}  frames {len(rec.inputs)}  hearts {s0.hearts}->{s.hearts}  at ({s.x},{s.y})", flush=True)
emu.close()
