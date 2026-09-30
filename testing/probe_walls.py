"""How many frames does the fighter lose to walls and blocks, and how many swings go into one?

The wasted-shot instrument (zelda/combat.py, ZELDA_WASTED=1) was built to tell three things apart:
a swing aimed into a wall, an enemy that moved, and a swing at nothing on purpose. It counts the
first kind. It could not count the other half of the same mistake, which is not swinging at all -
it is WALKING into the wall, one frame at a time, in a loop that repeats until the budget runs out.
Fighter._move stepped by the sign of the difference and never asked the tile map, so in a room with
furniture in it that is exactly what it did.

So: same room, same seeds, the wall gate on and off (ZELDA_NO_WALLS=1 restores the old behaviour).
Both sides run the real segment policy from the real checkpoint, with the wasted instrument on, and
the numbers printed are the ones the change is supposed to move: refused steps, aimed swings that
did nothing, aimed swings that went into a wall, and the frames the segment took.

Run it:  python3 testing/probe_walls.py [segment] [attempts]
Default segment is 4a_bombs (Level 3 room 0x4A, five Peahats and a bomb cache) because it is a
make_clear_policy, which is Fighter.clear_room - the Fighter, not the lookahead planner, and the
Fighter is the code that had never asked the map. A segment the planner runs (4b_left, say) will
report zero of everything on both sides, which is the honest answer for that segment and a waste of
an afternoon if you do not know it in advance.

WHAT IT FOUND, 2026-09-30, room $4A, six attempts a side. In the order the questions were wrong:

1. "He walks into walls." TRUE, and the only thing that was true of the original suspicion: 26 to 245
   refused steps a side depending on the trajectory, 0 with the gate off. The gate is in.

2. "He swings into walls." FALSE, 82 wasted swings out of 82 with a wall in the way - because the
   instrument was asking the wrong question. It tested the TARGET'S OWN CELL, and the thing the
   strike gate prevents is a wall BETWEEN them. Fixed: the instrument now tests the line, and the
   line version also says zero on this room.

3. "He swings at things the game will not let him hit." TRUE, and the real cost. Six beam swings at
   ONE dead Gel from 103 to 142 px away - 144 frames - because read_enemies filters on the type byte
   and a corpse keeps its type, its slot and its position until the game clears it. Fixed: a slot at
   0 HP is not a target.

4. "The Zol in the wall is unhittable until it comes out." PLAUSIBLE, AND WRONG. Every remaining
   wasted swing here is a Zol at 2 HP, at a legal sword gap, reading state $00 - and gating on
   state == 3 took this room from 82 wasted swings to ZERO and from 33 hits to ZERO, with every
   attempt ending "died fighting" and the fighter never swinging at all. A gate that makes a room
   unclearable is indistinguishable from a fix in the one counter meant to detect it. UpdateZolState
   has three states (0 Wander, 1 Shove, 2 Split), so 3 is not one a Zol can be in - which is exactly
   why the gate removed every swing rather than the wasted ones.

5. "The sword reaches 16 to 26 px." ALSO WRONG, and this one was the biggest thing in the file. The
   game does not use box sizes at all: DoObjectsCollideWithThresholds returns no-hit when the
   centre-to-centre distance is >= its threshold, and those thresholds are 16 and 12. So the reach
   is 16 px, the old model refused to swing inside 16 and reached to 26, and every one of its 82
   misses was a swing the cartridge had already refused. With Z_01's own arithmetic (sword_reach in
   zelda/combat.py, ZELDA_SWORD_GEOM=0 for the old one) this room goes from 33 hits in 115 swings
   and usually-not-cleared to 8 in 12 and cleared every time.

The reach histogram - "type@px: hits/misses", printed by this probe and by wasted_report - is the
thing that settles the next one: the Zol takes damage at 12-15 px (3 in 14) and never at 4-11 px
(0 in 5), with attr $01, invincibility timer $00 and metastate $00, i.e. every byte the cartridge's
own "can this be hit" path looks at says it should land. Nobody here has read UpdateZol's damage
path far enough to say why, and this room has one Zol in it.

The frame means are not quoted. They moved -564, +37, +54 and +289 across four runs of this probe
while the failure mode underneath them stayed the same - which is what a mean over three or four
attempts in a room this one is worth.
"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, states/ are repo-relative
ATTEMPTS = int(_os.environ.get("PROBE_ATTEMPTS", "6"))
SEGMENT = _sys.argv[1] if len(_sys.argv) > 1 else "4a_bombs"
del _os, _sys, _pathlib
import random

import fullgame
from zelda import combat
from zelda.emulator import BizHawk
from zelda.overworld import Navigator
from zelda.search import Recorder

CKPT = "fullgame_4a_bombs"       # L3 room 0x4A, and 4a_bombs is a make_clear_policy -
                                 # the one L3 segment the Fighter runs instead of the planner


def run(segment_name, walls: bool):
    """The same seeds with the wall gate on and off. Returns (per-attempt, counters)."""
    combat.NO_WALLS[0] = not walls
    seg = {s[0]: s for s in fullgame.segments()}[segment_name]
    _name, factory, _success, _tries = seg
    combat.WASTED[0] = True
    combat._wasted_stats.update({"swings": 0, "hits": 0, "wasted": 0, "solid": 0, "in_wall": 0,
                                 "buried": 0, "bumped": 0})
    combat._wasted_log.clear()
    emu = BizHawk(log_name=f"probe_walls_{'on' if walls else 'off'}.log", clean_sram=False)
    try:
        emu.load(f"ckpt_{CKPT}")
        nav = Navigator(emu)
        out = []
        for seed in range(1000, 1000 + ATTEMPTS):
            root = emu.msave()
            rec = Recorder(emu)
            try:
                res = factory(nav)(emu, rec, random.Random(seed), 3000)
            except Exception as e:
                res = f"raised {type(e).__name__}: {str(e)[:40]}"
            emu.mload(root)
            emu.mfree(root)
            out.append((seed, len(rec.inputs), str(res)[:26]))
        return out, dict(combat._wasted_stats), list(combat._wasted_log)
    finally:
        emu.close()


def main():
    segment = SEGMENT
    print(f"probe_walls: segment {segment!r} from ckpt_{CKPT}, {ATTEMPTS} attempts a side, "
          f"ZELDA_WASTED=1, same seeds both sides\n", flush=True)
    rows = {}
    for walls in (False, True):
        tag = "walls ON " if walls else "walls OFF"
        out, st, log = run(segment, walls)
        rows[walls] = (out, st, log)
        print(f"--- {tag}", flush=True)
        for seed, frames, res in out:
            print(f"    seed {seed}: {frames:5d} frames  {res}", flush=True)
        print(f"    aimed swings {st['swings']}, hits {st['hits']}, wasted {st['wasted']}"
              f"  [wall in the way {st['solid']}, target in a wall {st['in_wall']},"
              f" still in its burrow {st['buried']}]", flush=True)
        print(f"    steps refused as wall/block/water: {st['bumped']}", flush=True)
        print("    reach (type@px: hits/misses):  "
              + "  ".join(f"{k}:{v[0]}/{v[1]}" for k, v in sorted(st.get("reach", {}).items())), flush=True)
        for line in log[-6:]:
            print(line, flush=True)
        print(flush=True)
    off, on = rows[False], rows[True]
    fo = sum(f for _, f, _ in off[0]) / max(1, len(off[0]))
    fn = sum(f for _, f, _ in on[0]) / max(1, len(on[0]))
    print(f"mean frames: walls off {fo:.0f}, walls on {fn:.0f}  ({fn - fo:+.0f})", flush=True)
    print(f"refused steps: off {off[1]['bumped']}, on {on[1]['bumped']}", flush=True)
    print(f"wasted swings: off {off[1]['wasted']}, on {on[1]['wasted']}"
          f"  [wall in the way: off {off[1]['solid']}, on {on[1]['solid']}]"
          f"  [in a wall: off {off[1]['in_wall']}, on {on[1]['in_wall']}]"
          f"  [still in its burrow: off {off[1]['buried']}, on {on[1]['buried']}]", flush=True)
    print("\nWhat this does NOT say: one room, one seed set, and the fighter is not the only thing\n"
          "that walks. A mean over six attempts is a smell, not a result - re-run it on the room\n"
          "the change is actually for before believing either number.", flush=True)


main()
