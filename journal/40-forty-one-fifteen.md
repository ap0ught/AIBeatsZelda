# 40 — Forty-one fifteen

Third full run, power-on to Zelda: **148,766 frames = 41m15s of game time** (151,768 with the ending), replayed
from power-on in a fresh emulator, RAM fingerprint `761dab9f…` — MATCH. The second run was 57m40s, the first
1h43m. No cheats, no memory writes, no save states in the played trajectory; 351 searched segments.
(The first complete pass of this run finished at 41m45s, fingerprint `dd3bf258…`, also MATCH; its last half hour
was then searched again with two fixes found in its own trace - see "The tail" below. Both are archived:
`logs/archive/third_run_20260919` and `third_run_20260919b`.)

| milestone | run 2 | run 3 | saved |
|---|---|---|---|
| Level 3 done | 3:49 | 3:09 | 0:39 |
| Level 1 done | 8:36 | 6:42 | 1:54 |
| White Sword | 9:52 | 7:47 | 2:05 |
| Level 4 done | 15:59 | 12:45 | 3:13 |
| Level 2 done | 18:54 | 15:17 | 3:36 |
| Level 5 done | 25:58 | 21:13 | 4:44 |
| Level 6 done | 35:05 | 26:04 | 9:01 |
| Level 7 done | 41:18 | 30:02 | 11:16 |
| Level 8 done | 47:48 | 33:33 | 14:14 |
| Magical Sword | 49:39 | 34:53 | 14:45 |
| Level 9 entered | 50:57 | 35:52 | 15:05 |
| Silver Arrow | 54:47 | 39:00 | 15:46 |
| Zelda | 57:40 | 41:15 | 16:24 |

Journal 39 has the owner's list and the mechanisms behind it (the navigator's waiting and avoidance, water
learned as floor, Manhattan shaping, the whirlwind counter, the door-table audit). This entry is what the run
itself taught on the way through.

## What broke, and what it was

* **The stepladder is an object.** `l5_47b` failed 60 of 60 at a one-tile water crossing. Navigator debug showed an
  "enemy" of type 0x5F sitting on the water tile in front of Link: the game spawns the ladder as an object in the
  monster table, and the new threat list counted it, so the planner kept routing away from its own bridge.
* **A key spent by accident.** Level 4's Vire room has a locked north door the route never uses; Link brushed it
  mid-fight, the key went, and three rooms later the run stopped at the door the key was for. Both planners now
  price a lost key at 6,000 points.
* **One heart into Level 4.** "Go through them" is right for Octoroks and wrong for Lynels. Contact damage comes
  from the ROM table, so penalties scale with it, and the avoidance scale rises as hearts fall.
* **Scouts racing on one JSON file.** Six emulator threads, one `blocks.json`: a `PermissionError` from
  `os.replace` killed a scout thread silently. Locked reads, retried writes, no rewrite when nothing changed, and a
  policy exception is a failed attempt, not a dead scout.
* **Identical attempts.** Sixty attempts that all take the same hit are one attempt. Wider lead-in choices, more
  jitter variety and a per-attempt avoidance bias gave the search something to choose from.
* **The block starts to move; the stairs come later.** I had made `push_any_block` return the moment the tile map
  changed — which is when the block LEAVES its tile. The staircase appears when it arrives, 30 frames on, so
  Level 7's 0D reported "no stairs appeared" 40 times in 60. (My earlier test of the owner's suggestion — push
  that block from the right — had "failed" for exactly this reason. It works: the stairs open in the corner
  behind Link and the walk round the ring of blocks is gone.)
* **"Pushes the wrong block after the right one."** `push_blocks_for_door` only recognised success as a DOOR
  opening, so in a staircase room it leaned on every candidate for 90 frames, the right one included, and never
  remembered it. Now it stops at the block that moves and remembers it: Level 9's 0x30 went 1,042 → 763 frames.
* **Knockback is not a wall.** On the way to the Magical Sword a Lynel at the foot of overworld 0x32's one-tile
  staircase knocked Link back; the navigator recorded "this move is impossible", which on a one-tile staircase is
  the only path: 58 of 60 "no path". A step that fails because Link was hit, or because something is standing
  there, is not scenery — and a Lynel in the lane gets the sword like anything else.

## The pond by whirlwind

The owner flagged the same screen from the other direction: "you struggle getting out of the steps area". In this
run the careful planner dithered up and down that staircase for a thousand frames and lost four hearts to the
Lynels below it. The better answer was not to be there: Level 3's door is five quiet screens from the pond and
the wind's counter sat one note away. Door to pond: 3,420 frames and four hearts became 1,876 and half a heart,
and the recorder was already in hand when Link got there.

## Searching faster

`OverBudget`: an attempt's value is (what its hearts are worth) − frames, and hearts are capped by the containers,
so once an attempt has run `value(full health) − value(best)` frames it has lost whatever happens next. The
recorder raises at that point. It is lossless and evaluated live. Level 8's Gleeok was the case that hurt — a
1,985-frame win on the board and five scouts grinding 6,000-frame budgets at ten minutes an attempt; with the cut
the same search found 1,252. Level 7 → Level 8's boss, 25,000 frames of game, searched in 13 minutes of wall clock.

## Where the 41 minutes go, and what is next

Human records are under 30. The gap now is mostly fights and fixed costs, not wandering:

* Open-room fights (Darknuts, Wizzrobes) are 1,300–1,900 frames each and there are a dozen. An A/B against the
  old planner from run 2's states was mixed (new faster in one room, slower in three); a bias in the lattice
  distance (leftward/upward progress under-credited by up to 8 px) is fixed behind `WALK_INTERP` and looked
  better than "new" in 3 of 4 rooms, but it is not enough data to switch a whole run on.
* On open screens the NEW navigator now beats the damage-aware planner it was once replaced by (Spectacle Rock:
  270–311 frames against 424–810). `enter_L9` and the other `make_lareach_policy` walks should let the search
  try both.
* Overworld bomb waits now stop when the rock opens (−110 frames at Level 9's door; not in this run).
* The red candle costs ~2,400 frames in Level 7 and exists only to burn Level 8's bush; the blue candle is 60
  rupees and the run reaches the shops with 55 to spare after arrows and bait.

## The tail

The finished 41:45 pass had an 800-frame hole two segments from the end. After the Triforce of Power Link walked
to the wall under Ganon's north door in 96 frames - and stood there dithering until the planner's 900-frame
budget ran out, when the last-resort "line up and push" walked him out. The planner's holds are 8 frames = 12 px,
and from x=112 that cycles 124 → 128 → 116 → 112: never the door's column, 120. `walk_out_policy` now tries the
straight pixel walk first, on a scratch copy of the state, and only plans when that fails: 1,087 → 272 frames.
With the navigator-first approach to Level 9's door (1,105 → 673) and a Level 9 searched with full hearts, the
redo from Spectacle Rock took 24 minutes of wall clock and thirty seconds off the run.

## What the trace says is left

`idle_report.py` / `still_report.py` over the recorded trace: of 151,768 frames, **40% is not play at all** -
room scrolls (~172 frames each, ~250 of them), subscreens, caves, fanfares, the ending. Of the play frames 29%
is standing still, and almost all of that is now accounted for: ~29 subscreen trips to change the B item
(3,664 frames), bomb fuses / recorder tunes (2,822), old men's text typing itself out with Link frozen in the
doorway (Level 4's 00, Level 7's 28, Level 9's 06: 120-150 frames each), Triforce fanfares. The unexplained
remainder is small. So the next minutes are not in tightening, they are in **fewer rooms** (every room is ~172
frames of scroll before a step is taken) and **shorter fights** (a dozen Darknut/Wizzrobe rooms at 1,300-1,900
frames each - bounded by the White Sword until twelve hearts).

The overworld is the largest single block: **51,852 frames, 35% of the run, 138 screen entries over 74 distinct
screens** (`seg_costs.py`, and the per-level revisit listing in this session's notes). The longest legs are
Level 5 → shops → Level 6 (whirlwind to Level 4's island, raft, 4 screens to the shops, then 13 screens round
through the Lost Woods: 4,005 frames from the bait shop to Level 6's door) and the 0x0F money detour (~2,900
frames for 100 rupees). Three guessed shortcuts were probed and are all walls (0x34 has no west exit, nor has
0x44; 0x27 has no west exit). The right tool is an **overworld router**: decode all 128 screens from the ROM,
build the connectivity graph with the whirlwind's stops as edges, and search it for the cheapest order of
errands - instead of probing guesses one at a time.

**A fight-planner bug found afterwards (fixed for the next run, not in this one).** Six open-room fights came out
slower than in the second run (the two Level 5 staircase rooms +507 and +633, Level 6's 28 +400). The new
walking-distance field pulled Link toward all four sides of every target - including a Darknut's FRONT, where the
shield eats every swing; the old straight-line shaping left that spot out. With the field built by the same
facing rule (`SPOT_FACING`), from the second run's states: Level 8's 3F 1,751 → 1,479 frames (old planner 1,625),
Level 5's staircase room 1,925 → 1,847 (old 1,523 - still a gap there). Four seeds a side, so indicative only.

**A fix that bit back.** Chasing the Ganon's-room stall I first blamed the walking-distance field and made
`plan_reach` fall back to straight-line shaping whenever Link's START was not on the lattice. That was not the
cause (the real one was the 12-px holds), and the fallback fired on every screen Link ENTERS from an edge
(y=221 is off the lattice): at the White Sword cave it sent him straight at a wall for 5,000 frames, 35 of 60
attempts, and the fourth run stopped there. Removed. What stays from that hunt is general: within 28 px of a
goal `plan_reach` now tries a single-frame pixel walk on a scratch copy of the state and plays it if it lands
unhurt - the planner's coarse holds no longer have to hit a 6-px tolerance by luck.

## A fourth run, and what it showed

With the fixes above (Darknut facing, the block pushes from the first room on, a 1.6x deeper search on long
rooms) a fourth run was started from power-on as a bonus. It confirmed the fixes - Level 5's two staircase rooms
1,694 → 1,205 and 1,540 → 1,188, Level 4's ladder staircase 1,181 → 798, Level 6's 28 1,886 → 1,495 - and it
showed the two things that still decide a run:

* **Boss variance swamps tightening.** Level 4's Gleeok took 1,951 frames (697 in the third run) and the whole
  1,554-frame lead was gone in one room. At Level 7 the two runs were 300 frames apart.
* **Bombs are not guaranteed by the route.** Different kills, different drops: the fourth run left Level 6 with
  ONE bomb where the third had seven, and stopped at Level 7's second wall with none (`l7_1a`: 60x "could not
  select bombs"). The route needs a bomb budget the way it has a key budget: success tests that refuse to
  commit a segment which leaves fewer bombs than the walls ahead need, and drop-grabbing weighted by that need.

The fourth run was discarded (`logs/archive/fourth_run_partial_20260919`); the delivered run is the third.
