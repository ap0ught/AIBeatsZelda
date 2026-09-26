"""Probe the pieces of single-entry Level 8 and Level 9, each chain from the finished run's own saved
states, with the policies the run would use (no reloads inside a chain).

  A  L7 pond -> whirlwind to Level 2's door (0x3C) -> 4C -> 4D -> 5D -> 6D (east half) -> burn into
     Level 8. Would replace the 22-screen walk along row 6.
  B  the 100-rupee tree on 0x6B from the walk-in side (the old run only ever reached it from below)
  C  after Level 8: whirlwind from 6C to Level 1's door -> 38 -> 48 -> 47 -> heart container #12
  D  Level 9's bomb pile room 0x16 -> north through the locked door to the old man's 0x06
  E  Level 7's second room 0x59 -> west 0x58 -> north through the locked door to 0x48 (bomb upgrade?)

usage: python probe_single_entries.py [A B C D E] [--seeds N]
"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import random
import sys

import fullgame as fg
from zelda.emulator import BizHawk
from zelda.overworld import Navigator
from zelda.search import Recorder
from zelda.segments import make_cross_policy, make_cross_at_policy


def cross(d):
    return lambda nav: make_cross_policy(nav, d)


CHAINS = {
    "A": ("ckpt_fullgame_warp_L7", [
        ("down to 52",   cross("Down"),                                            lambda s: s.room == 0x52),
        ("whirl to 3C",  lambda nav: fg.whirl_to_policy(nav, 0x3C),                lambda s: s.room == 0x3C and s.mode == 5),
        ("down to 4C",   cross("Down"),                                            lambda s: s.room == 0x4C),
        ("right to 4D",  cross("Right"),                                           lambda s: s.room == 0x4D),
        ("down to 5D",   cross("Down"),                                            lambda s: s.room == 0x5D),
        ("down to 6D",   lambda nav: make_cross_at_policy(nav, "Down", at=192),    lambda s: s.room == 0x6D and s.x >= 176),
        ("burn into L8", lambda nav: fg.burn_entry_policy(nav, (192, 109), "Left", 8), lambda s: s.level == 8 and s.mode == 5),
    ]),
    "B": ("ckpt_fullgame_n8_6b", [
        ("cave on 6B",   lambda nav: fg.burn_cave_policy(nav, (128, 141), "Down"), lambda s: s.level == 0 and s.mode == 5),
        ("down to 7B",   cross("Down"),                                            lambda s: s.room == 0x7B),
    ]),
    "C": ("ckpt_fullgame_n9_6c", [
        ("whirl to 37",  lambda nav: fg.whirl_to_policy(nav, 0x37),                lambda s: s.room == 0x37 and s.mode == 5),
        ("right to 38",  cross("Right"),                                           lambda s: s.room == 0x38),
        ("down to 48",   cross("Down"),                                            lambda s: s.room == 0x48),
        ("left to 47",   cross("Left"),                                            lambda s: s.room == 0x47),
        ("heart cave",   lambda nav: fg.hc_cave_policy(nav, (176, 157), "Down", "burn"), lambda s: s.mode == 5 and s.level == 0),
    ]),
    "D": ("ckpt_fullgame_m9_16_bombs", [
        ("up to 06",     cross("Up"),                                              lambda s: s.room == 0x06 and s.level == 9),
    ]),
    "E": ("ckpt_fullgame_l7_59", [
        ("left to 58",   cross("Left"),                                            lambda s: s.room == 0x58 and s.level == 7),
        ("up to 48",     cross("Up"),                                              lambda s: s.room == 0x48 and s.level == 7),
    ]),
}

args = [a for a in sys.argv[1:] if a in CHAINS]
seeds = int(sys.argv[sys.argv.index("--seeds") + 1]) if "--seeds" in sys.argv else 2
emu = BizHawk(log_name="probe_single_entries.log", clean_sram=False)
nav = Navigator(emu)
for key in (args or list(CHAINS)):
    state, steps = CHAINS[key]
    for seed in range(seeds):
        emu.load(state)
        s = emu.state()
        print(f"\n[{key}] seed {seed} from {state}: room {s.room:02X} L{s.level} ({s.x},{s.y}) hearts {s.hearts}/"
              f"{s.raw.get('hpmax', '?')} rup {s.rupees} keys {s.keys} bombs {s.bombs}", flush=True)
        total = 0
        for label, make, good in steps:
            rec = Recorder(emu)
            try:
                out = make(nav)(emu, rec, random.Random(seed * 7 + 1), 6000)
            except Exception as e:
                out = f"{type(e).__name__}: {str(e)[:50]}"
            s = emu.state()
            total += len(rec.inputs)
            okay = s.hearts > 0 and good(s)
            print(f"   {label:13s} {str(out)[:30]:32s} -> {s.room:02X} L{s.level} ({s.x:3d},{s.y:3d}) "
                  f"{len(rec.inputs):5d} fr  hearts {s.hearts} rup {s.rupees} keys {s.keys} bombs {s.bombs}"
                  f"  {'OK' if okay else 'WRONG'}", flush=True)
            if not okay:
                print("   shot:", emu.screenshot(f"single_{key}_{seed}_{label.replace(' ', '_')}"), flush=True)
                break
        else:
            print(f"   CHAIN {key} OK in {total} frames", flush=True)
        if key == "E":
            print("   shot:", emu.screenshot(f"single_E_{seed}_end"), flush=True)
emu.close()
