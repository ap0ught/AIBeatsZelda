# Run ideas

Everything below was worked out against this checkout on 2026-09-25, and the file
is kept as written rather than rewritten. What has changed since is marked where
it changed: the Gleeok idea has been **run and banked** (`runs/gleeok_dragon`), and
the "~search" column below has proved optimistic by a wide margin — see "What it
actually cost" under that section. Costs marked
"model" come from `route_planner.py`, which is planning arithmetic on the decoded
overworld map and needs no emulator; it predicts route 3 at 41.33 min against
41.26 actual, so it is good to about half a minute. Costs marked "~search" are
scaled from run6's own `search_log.txt` (324 segments, 10,257 attempts, ~4.5 h
for the whole game).

## Baseline: what is already proven

`runs/run6` replays from power-on and is byte-exact:

```
replayed 136526 frames -> f136526 mode=13/04 L9 room=32 pos=(136,136) dir=2 hp=8.5/13 rup=29 sword=3 lag=23405
  ram sha1 3115e31ff1a9b16e732160f81fe478a5052668ff
  MATCH
```

That is the fingerprint in `runs/run6/VERIFICATION.txt`. Two different numbers
describe it and both are right: 136,526 frames at the NES's 60.0988 Hz is 37:52
of emulated time, and the game's own in-game timer reads 37:02.

**Since 2026-10-02 there is a second one.** `runs/gleeok_dragon` is route 5 from
power-on, 60,589 frames and 161 segments, replaying to work-RAM SHA-1
`575771d9bd7ca936b157d6c6f5d9ae43aa5e9331`. It is the Gleeok idea below, run and
banked. Read its `VERIFICATION.txt` before citing it: 75 of its 161 segments were
taken unpolished under `ACCEPT_AFTER`, and the route is wrong one segment past
its end. It is not a finished route-5 run and it is not the whole game.

## Dungeon order is the main lever

| route | order | model | actual |
|---|---|---|---|
| route 3 (default) | `3-1-4-2-5-6-7-8-9` | 41.33 min | 41:15 |
| route 4 (`ZELDA_ROUTE=4`) | `3-1-4-8-2-5-7-6-9` | 39.24 min | **37:02** ← run6 |

Route 4's gain is mostly L8 pulled forward: it nets +2 keys early, which funds
every key purchase after it. Re-running `python3 route_planner.py 150` from
scratch independently rediscovers the same order (best 39.17 min over 4 seeds,
~1.4M candidates each), so this was the planner's answer, not a hand-pick.

## Candidate runs

| idea | legal? | cost | verdict |
|---|---|---|---|
| **Gleeok (L4) then L1** | yes | 14.06 min stop, +14 s on the full route, ~127 seg / 3,636 att / **~1.6 h** | **best story-per-hour** |
| Speedrun to L1 boss | yes | 9.4 min stop, 91 seg / 2,468 att / ~1.1 h | validates the pipeline fastest |
| All eight dungeons, no Ganon | yes | 30.9 min stop, 289 seg / 8,912 att / ~3.9 h | Ganon itself is only ~0.6 h |
| Beat the dragon, go home to the Old Man | yes | +3,856 frames (~1.1 min) return walk to 0x77 | see "the dragon" below |
| Naive `1-2-3-4-5-6-7-8-9` | yes, but | 47.87 min model, **+8.6 min** vs route 4 | rejected |
| Straight for L9 | **no** | — | the game's gate, not ours |
| Fairy before the sword | legal, unprofitable | — | see "fairies" |

## Gleeok (L4) then L1 — the one worth running

This is route 4 with the L1 and L4 blocks transposed, i.e. the reverse of the
order run6 actually used.

| | after White Sword | after Gleeok (L4) | after L1 | full route |
|---|---|---|---|---|
| route 4 | 6.32 min | 13.71 min | 9.10 min (L1 was first) | 39.24 min |
| swapped | 6.32 min | **11.39 min** | **14.06 min** | 39.48 min |

It works because Gleeok needs the **White Sword, not the bow**, and 5 hearts is
reachable without L1 (`3 + L3 + h_2C`). The candle is bought before the sword, so
`h_47` can burn before L4 too. The swap costs 14 seconds on the whole game.

Build needed, **all three of which now exist**: `route5.py` (route 4 with the
two blocks transposed), the `ZELDA_ROUTE=5` branch at `fullgame.py:2332-2340`,
and `--until` at `fullgame.py:3124` so a run can stop after a named segment. The
branch also refuses anything that is not 3, 4 or 5: it used to match on `"4"`
alone, so `ZELDA_ROUTE=5` fell through to route 3 and ran a four-and-a-half-hour
dungeon order nobody asked for, with nothing but a log line to say so. The
fiddly part was the overworld connectors — route 4's `_lane(d, at)` coordinates
were pinned for its own order, so the two new legs (White Sword → L4's door, L4 →
L1's door) need coordinates read off the router. `route_planner.py` priced both
walks; the pinning was manual, and the return leg turned out to need eight
crossings rather than the raft (FINDINGS.md §14).

Start with `ZELDA_SCOUTS=4` (the default), not 6. Six concurrent emulators is the
workload that exposed the Mono/X11 crash — see `SETUP-LINUX.md`.

**What it actually cost.** The ~1.6 h above is scaled search arithmetic from
run6's log and it was low by a wide margin. One archived piece of the run,
`logs/archive/gleeok_pre_dragon_20261002_014549/gleeok_run8.log`, spans its own
attempt timestamps 2026-10-01 10:49:14 to 16:27:17 — 5 h 38 m of wall clock over
16 wrapper restarts — and the run carried on past that log before it stopped on
`l2_sail` at 20:59:47. The segment count moved the other way: ~127 predicted,
**161 banked**, because `revenge` (the Blue Lynel on 0x0A, after 50 crossings home)
and the leg out of the sword cave were not in the estimate. The comparison is
unfair in the direction that matters (the estimate counts search, the log counts
restarts and resumes too), but the order of magnitude gap is real and the table's
"~" column should be read as optimistic.

## "The dragon" was ambiguous — it has been picked, and paid for

- **Level 6**, which `fullgame.py` labels `# --- Level 6 (the Dragon)`. Stop at
  30.9 min, 289 seg / 8,912 att / **~3.9 h**. Not run.
- **Gleeok**, an actual dragon boss, which appears **twice** — L4 (segment
  `gleeok`, stop 13.2 min / ~1.6 h) and L8 (segment `l8_gleeok`, 17.1 min /
  ~2.1 h). Journal 13 is "Level 4, and hitting a wall called Gleeok"; journal 14
  says it beat him five ways before the White Sword made it tractable.

**L4 Gleeok is the one that got run, on route 5, and it is banked.** The run is
`runs/gleeok_dragon`: 161 segments, 60,589 frames, from power-on, MATCH on replay
to `575771d9…`, Gleeok dead at f43620 and the head delivered at f60589. It then
failed one segment later for a reason that has nothing to do with the dragon —
`deliver` walks *into* the sword cave and `l2_sail`'s policy wants a dock, and
there is no dock inside a cave. FINDINGS.md §14 has the fix and the measurement
for the leg after it (eight crossings, 2,555 frames walked for real from the
run's own bookmark). L6 and L8 Gleeok are still unrun.

The harness's own dungeon names are L2 = the Moon, L5 = the Lizard,
**L6 = the Dragon**, L8 = the Lion.

## Dead ends, with reasons

**Straight for L9 is impossible.** `route_planner.py:181` encodes
`9: len(levels) == 8 and bow and arrows and bombs`, and the planner rejects
`['L9']` and `['L1','L9']` with "L9 before its key item". Each dungeon holds a
piece of the Triforce of Power; you cannot assemble it without all eight. It is
only possible in the real game with glitches — screen scroll, block clipping,
recorder wrong warp — which this project's rules forbid. Their own
`knowledge/wr_route_comparison.md` notes there is no plain glitchless any%
category on the board; the closest is 1:08:07 "No Glitches, No Swords, No Extra
Hearts", against the 27:40 glitched record they cite.

**Naive 1-9 is legal but 8.6 minutes worse.** The dependency graph does not block
it: L1 first is fine, and the chain resolves (L1 → bow, L3 → raft+bombs,
L4 → ladder, L5 → recorder, L7 → candle, L8). What blocks it is the **rupee
budget**. Three attempts:

```
1-9, one rupee cave      INFEASIBLE: arrows: no money or already owned
1-9, rupee cave before L3 INFEASIBLE: r30_67 needs bombs        (bombs are L3's)
1-9, two rupee caves     feasible, 47.87 min
```

L8 dead last before Ganon means a thin key count carried through seven dungeons.
The keys/bombs budget must be re-budgeted per order (`knowledge/route4_plan.md`
says so, and notes "Level 8 early nets +2 keys" as the reason route 4 works).

## Open threads

**Fairies.** `fairy_policy` (`fullgame.py:909`) is a complete, carefully written
policy — it reads the fairy's live position from RAM and works around the pond
trap where the path planner cannot route Link out — and it is referenced by **no
route**. Dead code. The harness otherwise treats fairies reactively:
`zelda/combat.py:1136` only takes a drop "while hurt". They were tried and cut:
`testing/patch_single_l8_l9.py:10` describes a route that sailed across the lake and back
a third time, ~38,000 frames, and the replacement uses "no fairy detour".

The cheap place to try is *not* a pond — it is the pre-sword bomb stretch route 4
already runs (`L3 → h_2C → r100_0F → candle → WS`, with bombs from L3). Blocker:
`route_planner.py` has no fairy errand, so it cannot price one. ~20 lines to add.

**Rupees.** Sources are 7 per dungeon, 30-rupee secrets (`r30_*`, seven of them)
and 100-rupee secrets (`r100_*`, three). Prices: candle 60, arrows 80, bait
60-100. Route 4 peaks at **182** after `r100_6B`. So there is no 25-rupee pickup
(smallest secret is 30) and 225 is above the peak — reachable only by sweeping
secrets it does not already take.

**Those are displayed rupees, and the prices are confirmed.** RAM `0x66D` is the
count the HUD shows, not an internal encoding: at byte 2 the HUD reads `x2`, at
155 it reads `x155`. And every price in the planner's `PRICE` table was measured
off run6's own log — candle 106→46, arrows 161→81, bait 81→21. The Blue Candle
really does cost 60 here. An earlier note in this file doubted the units because
the candle was believed to have a 200-rupee sticker; that was wrong, and the
harness was right. See `FINDINGS.md`.

**Heart caves are not a fee.** The two overworld heart containers are
take-any-one caves: old man's red potion on the left (x=120) or heart container on
the right (x=152), and the other choice is gone for good. Nothing is paid —
`hc_cave_policy` defaults to `item_x=152` and all three call sites take the
container. The money caves are the mirror image: `burn_cave_policy` is "an old man
who hands over 30 or 100 rupees **for nothing**". The 20-rupee price people
remember is a shop — one arrow or one bait.

## How to run any of these

```
# watch the existing verified run
python3 watch_run.py

# a new route: write routeN.py, add a branch at fullgame.py:2272
ZELDA_ROUTE=5 ZELDA_SCOUTS=4 bash run_until.sh logs/run5.log 40
```

`run_until.sh` restarts on the emulator's silent deaths, stops on a real
`RuntimeError: segment` rather than looping, and takes an atomic lock at
`/tmp/zelda_run.lock`. It has no per-instance lock on `NES/SaveRAM`, so never run
two watchers at once. `run.finish()` verifies by replay from power-on and exports
the `.bk2` automatically.

Use `--fresh` with any new route: resuming a checkpoint from a different route
keeps the old input prefix and skips matching segment names, and the replay would
still say MATCH because the hybrid log is self-consistent.
