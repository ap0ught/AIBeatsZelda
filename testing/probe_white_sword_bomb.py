"""The White Sword screen (0x0A): can a single bomb take the Blue Lynel off it?

Route 5 reached this segment at 3.5/5 hearts and failed 60 of 60 attempts; run6 reached it at 4.5/5 and
succeeded on attempt 39. A Blue Lynel hits for two hearts, so at 3.5 one hit is survivable and the second is
death - and `hearts >= containers` is false, so the sword beam is off. The margin, not the search, is what
failed. Link is carrying bombs out of Level 3, and a bomb kills a Lynel outright, so the question is whether
one can be placed and survived from where the checkpoint leaves him.

From ckpt_fullgame_ws_0a: Link at (208,221) facing Down, cave mouth somewhere on 0x0A, one Blue Lynel.
Each seed picks a bombing tile at a different range from the Lynel, so this measures the FUSE and the blast
rather than one lucky placement. Prints what died, what Link paid, and whether the cave mouth was reachable
afterwards.

    python3 testing/probe_white_sword_bomb.py [tries]
"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib

import random
import sys

from zelda import bot, ram
from zelda.emulator import BizHawk
from zelda.lookahead import Goal, plan_reach
from zelda.overworld import LinkDied, NavError, Navigator, enemy_name, read_enemies
from zelda.search import Recorder

TRIES = int(sys.argv[1]) if len(sys.argv) > 1 else 6
# Stand this far from the Lynel and drop one. A bomb explodes where it is PLACED, not where it is aimed,
# so this is the only knob that matters: at 24-64 px the blast landed two or more tiles short and the
# Lynel came out at full health every time. Adjacent is the range being tested now, with the fuse
# (bomb_darknuts measures ~76 frames) as the only thing standing between Link and his own bomb.
RANGES = [8, 12, 16, 20, 24, 32]


def nearest_tile(em, ex, ey, r):
    """A free lattice tile at roughly range r from the enemy, preferring Link's own side of the room."""
    lat = _LATTICE
    s = em.state()
    best = None
    for x, y in sorted(lat.free):
        d = abs(x - ex) + abs(y - ey)
        if abs(d - r) <= 8:
            back = abs(x - s.x) + abs(y - s.y)
            score = (abs(d - r), back)
            if best is None or score < best[0]:
                best = (score, (x, y))
    return best[1] if best else None


with BizHawk(log_name="probe_white_sword_bomb.log") as emu:
    nav = Navigator(emu)
    from zelda.lookahead import Lattice
    for i in range(TRIES):
        r = RANGES[i % len(RANGES)]
        s0 = emu.load("ckpt_fullgame_ws_0a")
        rec = Recorder(emu)
        rec.step((), 4 + i * 5)
        s = emu.state()
        ens = [e for e in read_enemies(emu) if e[1] in (0x01, 0x02)]
        if not ens:
            print(f"[{i}] no Lynel on the screen right now (it moves); skipping")
            continue
        e = ens[0]
        print(f"[{i}] range {r}: Link {s.x},{s.y} hp {s.hearts}/{s.containers} bombs {s.bombs}; "
              f"{enemy_name(e[1])} at {e[2]},{e[3]} hp {e[4] >> 4}")
        try:
            _LATTICE = Lattice(emu)
            tile = nearest_tile(emu, e[2], e[3], r)
            if tile is None:
                print(f"      no free tile near range {r}")
                continue
            tx, ty = tile
            s = nav.go(lambda x, y: x == tx and y == ty, f"the bombing tile ({tx},{ty})", max_replans=60)
            if not bot.select_b_item(emu, emu.step, bot.B_BOMBS):
                print("      could not select bombs")
                continue
            # the direction press immediately before B is not decoration: the game places the bomb in
            # the tile Link is facing, and a bare B with nothing held does not arm it. This is the
            # sequence bomb_darknuts() uses, and the first version of this probe omitted the face
            # press - six of six, bombs never left inventory.
            b0 = emu.byte(ram.BOMBS)
            emu.step("Up" if ty < s.y else "Down" if ty > s.y else
                     "Left" if tx < s.x else "Right", 1)
            emu.step("B", 2)
            spent = emu.byte(ram.BOMBS) != b0
            if not spent:
                print("      the B press did not spend a bomb - placement failed, not the fuse")
                continue
            # get off the tile the fuse is burning on, and keep going: the blast catches Link too
            for _ in range(4):
                s = emu.step("Right" if s.x <= tx else "Left", 8)
            frames = 0
            while frames < 240:
                s = emu.step((), 4)
                frames += 4
                if not [o for o in read_enemies(emu) if o[1] in (0x01, 0x02)]:
                    break
            left = [o for o in read_enemies(emu) if o[1] in (0x01, 0x02)]
            hp_now = f"{left[0][4] >> 4}" if left else "-"
            print(f"      bomb placed, {frames:3d}f  Lynels left={len(left)} hp {e[4] >> 4}->{hp_now}  "
                  f"Link {s.hearts}/{s.containers} alive={s.hearts > 0}")
            if not left and s.hearts > 0:
                spot = bot.find_entrance(emu)
                print(f"      screen clear and Link is alive; cave mouth at {spot}")
        except (NavError, LinkDied, bot.BotError) as exc:
            print(f"      failed: {str(exc)[:70]}")
print("done")
