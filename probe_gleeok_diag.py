"""Why does the Gleeok search produce no successes? Get per-attempt outcomes and timings.

The run's log only records attempts that SUCCEED, so an hour of silence says nothing about whether
attempts are dying, timing out, or simply running long. This runs the same policy the same way -
loading the segment's own start state, no settle frames - and prints what each attempt actually did.

usage: python probe_gleeok_diag.py [tries] [budget]
"""
import random
import sys
import time

import fullgame
from zelda.emulator import BizHawk
from zelda.overworld import Navigator, read_enemies
from zelda.search import Recorder

tries = int(sys.argv[1]) if len(sys.argv) > 1 else 6
budget = int(sys.argv[2]) if len(sys.argv) > 2 else 6000

segs = fullgame.segments()
names = [s[0] for s in segs]
name, factory, success, seg_tries = segs[names.index("gleeok")]

emu = BizHawk(log_name="probe_gleeok_diag.log", clean_sram=False)
nav = Navigator(emu)
policy = fullgame.gleeok_policy(nav, budget=budget)
print(f"gleeok: {tries} attempts at budget {budget} (segment's own tries={seg_tries})", flush=True)

for i in range(tries):
    t0 = time.time()
    emu.load("fullgame_gleeok_start")
    rec = Recorder(emu)
    rec.step((), 2)
    rng = random.Random(1000 + i)
    try:
        outcome = policy(emu, rec, rng, 3000)
    except Exception as e:
        outcome = f"{type(e).__name__}: {str(e)[:40]}"
    s = emu.state()
    ok = success(emu, s)
    left = [(hex(e[1]), e[4] >> 4) for e in read_enemies(emu)]
    print(f"  attempt {i + 1:2d}: {outcome[:34]:36s} {len(rec.inputs):5d} frames  "
          f"{s.hearts:4} hearts  cleared={emu.byte(0x34D):02X}  success={bool(ok)}  "
          f"{time.time() - t0:5.0f}s  left={left[:3]}", flush=True)
emu.close()
