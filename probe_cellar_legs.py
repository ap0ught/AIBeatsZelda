"""Trace every leg of take_cellar_item_la in the Silver Arrow cellar: goal, result, frames used and
where Link ends. The last re-probe ended on identical frames after a fix, so the failure is earlier
than the code that was fixed - find which leg."""
import random
import fullgame
import zelda.lookahead as la
from zelda.emulator import BizHawk
from zelda.overworld import Navigator, read_enemies
try:
    from zelda.search import Recorder
except ImportError:
    from zelda.runner import Recorder

emu = BizHawk(log_name="probe_cellar_legs.log", clean_sram=False)
nav = Navigator(emu)
real_reach = la.plan_reach


def traced_reach(emu_, rec_, goal, **kw):
    s0 = emu_.state()
    r = real_reach(emu_, rec_, goal, **kw)
    s1 = emu_.state()
    tgt = getattr(goal, "target", None)
    tol = getattr(goal, "tol", None)
    print(f"    leg goal={tgt} tol={tol} max={kw.get('max_frames')} -> {r} | "
          f"{s1.frame - s0.frame} frames | ({s0.x},{s0.y}) -> ({s1.x},{s1.y}) mode {s1.mode:02X} room {s1.room:02X} "
          f"hp {s1.hearts} | $0659={emu_.byte(0x659):02X}", flush=True)
    if r != "arrived":
        print("      objects:", [(hex(e[1]), e[2], e[3]) for e in read_enemies(emu_)], flush=True)
        print("      shot:", emu_.screenshot(f"cellar_leg_fail_{s1.frame}"), flush=True)
    return r


la.plan_reach = traced_reach
for seed in (1000, 1001):
    emu.load("ckpt_fullgame_s9_10_st"); emu.wait(2)
    rec = Recorder(emu)
    print(f"seed {seed}: start {emu.state()}", flush=True)
    out = fullgame.cellar_item_policy(nav, 0x659)(emu, rec, random.Random(seed), 3000)
    print(f"seed {seed}: outcome={out} | end {emu.state()} | $0659={emu.byte(0x659):02X}", flush=True)
emu.close()
