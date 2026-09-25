# 42 — Thirty-nine fifteen

Fourth full run, the first on ROUTE 4: **Zelda at frame 141,549 = 39m15s of game time** (39:10.6 by speedrun.com's
clock), 144,551 frames with the ending, replayed from power-on, RAM fingerprint `8dc42b04…` — MATCH. Glitchless,
341 searched segments. The route planner had predicted 39.24 minutes. The run came in at 39.25.

| | run 3 | run 4 |
|---|---|---|
| White Sword | 7:47 (after Level 1) | 6:28 (before it) |
| Level 4 done | 12:45 | 13:49 (with L1, two extra hearts, the candle and 100 rupees already banked) |
| Level 8 done | 33:33 | 18:04 (it is next door to Level 4's dock once the candle is bought) |
| Magical Sword | 34:53 (before Level 9 only) | 30:00 (before Level 6 too) |
| Level 9 entered | 35:52 | 33:43 |
| Zelda | 41:15 | 39:15 |

Order: L3, heart rock 0x2C, the hidden hundred at 0x0F, BLUE CANDLE at 0x0C, White Sword, L1, heart tree 0x47, L4,
the hundred under 0x6B's tree, L8, L2, L5, wind to the shops (arrows, bait), L7 without its candle cellar, Magical
Sword, L6, wind, L9. Built in `route4.py` from route 3's own tested segment tuples plus pinned connectors;
`ZELDA_ROUTE=4` selects it.

Where the two minutes came from (frames): overworld and errands -3,262; Level 7 -2,329 (no candle cellar);
Level 6 -1,165 (Magical Sword); Level 4 -1,045; Level 1 -413 (White Sword: far less than the model's -1,540);
Levels 2, 8 and 9 +1,272 between them (fewer hearts in 8, variance in 9).

## What went wrong on the way (three stops, all lanes)
* `l2w07_5d`: a REUSED unpinned crossing. Coming from the south, the navigator left 0x5B by the nearest exit - the
  bottom lane of 0x5C, which is a dead end. The router had said "top lane, y=93". Every reused crossing that is
  approached from a new side now gets the router's pin (`route4.lane`).
* `l2b_5d`: the planner measured the leg from Level 8's DOOR, but the Triforce warp sets Link down at (96,93), WEST
  of the stairs - and the only way east from there is over the stairs, back into the dungeon: 60 of 60 attempts
  "crossed" into room 7E. Levels 7 and 8 both come out at (96,93); legs must start from where the warp really puts
  him.
* The Level 4 ring shortcut needs two bombs and Link had one, so both roads are in the list behind `when()` guards
  and the run took the old one. Bombs are still the constraint on shortcuts.

## Engine changes that rode along
Bombs in the search's ranking (220 frames each); the ten-kill forced-drop logic (bounded, per attempt); sword-beam
rollouts at full hearts (per attempt; Vire room -21 %, Keese room +15 % in the A/B); `OverBudget`.

## What is left, honestly
The owner's hope is 33-35. Route order is now spent: the planner's optimum IS this run. The rest is inside the
dungeons - 97,417 of the 141,549 frames - and it is fighting (about half of that) and bombs (which gate every
remaining room shortcut). 35 needs roughly 15,000 more frames: a fifth of all fight time, or the equivalent.
