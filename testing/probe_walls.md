# `probe_walls.py`

How many frames does the fighter lose to walls and blocks, and how many swings go into one?

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

---

    python3 testing/probe_walls.py          # any cwd; the bootstrap chdirs to the repo root

## What it touches

- **drives BizHawk** - replays, searches or steps frames
- writes `logs/`, `shots/`, `states/`

## Why this still matters

Cited by production code. These comments are where the numbers came from,
so if this script's method is wrong, the constant is wrong too:

- ``zelda/combat.py`:119` - ZELDA_SWORD_GEOM=0 restores the old box model, which is what the A/B in testing/probe_walls.py

## See also

- [`probe_seg2.py`](probe_seg2.md)
- [`probe_old_man.py`](probe_old_man.md)
- [`probe_new_seg.py`](probe_new_seg.md)
- [`probe_map_chest.py`](probe_map_chest.md)

---

*Generated by `testing/make_doc.py` from the script's own docstring and code. Regenerate with `python3 testing/make_doc.py`; do not hand-edit - `git log` on this file says when.*
