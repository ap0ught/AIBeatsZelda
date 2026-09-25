"""Validate the whole 0x0F detour end to end, with the policies the run will use, step after step from
the same live state (no reloads between steps): 0x2D -> 0x1D -> 0x1E -> 0x1F -> through the gap -> the
100-rupee cave -> back through the gap -> 0x1E -> 0x1D -> 0x2D."""
import random

import fullgame
from zelda.emulator import BizHawk
from zelda.overworld import Navigator
from zelda.segments import make_cross_policy, make_cross_at_policy
from zelda.search import Recorder

emu = BizHawk(log_name="probe_0f_detour.log", clean_sram=False)
nav = Navigator(emu)
STEPS = [
    ("up to 1D",      lambda: make_cross_at_policy(nav, "Up", at=120),                        0x1D),
    ("right to 1E",   lambda: make_cross_policy(nav, "Right"),                                0x1E),
    ("right to 1F",   lambda: make_cross_policy(nav, "Right"),                                0x1F),
    ("through to 0F", lambda: fullgame.hold_through_policy(nav, 128, "Up", 0x0F),             0x0F),
    ("the cave",      lambda: fullgame.secret_cave_policy(nav, None, "Up", "walk", want=100), 0x0F),
    ("back to 1F",    lambda: fullgame.hold_through_policy(nav, 128, "Down", 0x1F),           0x1F),
    ("left to 1E",    lambda: make_cross_policy(nav, "Left"),                                 0x1E),
    ("left to 1D",    lambda: make_cross_policy(nav, "Left"),                                 0x1D),
    ("down to 2D",    lambda: make_cross_at_policy(nav, "Down", at=120),                      0x2D),
]
emu.load("ckpt_fullgame_l5w03_2d")
total = 0
r0 = emu.byte(0x66D)
for name, make, room in STEPS:
    rec = Recorder(emu)
    try:
        out = make()(emu, rec, random.Random(7), 3000)
    except Exception as e:
        out = f"{type(e).__name__}: {str(e)[:40]}"
    s = emu.state()
    total += len(rec.inputs)
    ok = s.room == room and s.mode == 5
    print(f"  {name:14s} {str(out)[:22]:24s} -> {s.room:02X} ({s.x:3d},{s.y:3d}) {len(rec.inputs):5d} fr  "
          f"rupees {emu.byte(0x66D):3d} hearts {s.hearts}  {'OK' if ok else 'WRONG'}", flush=True)
    if not ok:
        print("  stopping; shot:", emu.screenshot("detour_fail_" + name.replace(" ", "_")), flush=True)
        break
print(f"\nDETOUR: {total} frames, rupees {r0} -> {emu.byte(0x66D)} (+{emu.byte(0x66D) - r0})", flush=True)
emu.close()
