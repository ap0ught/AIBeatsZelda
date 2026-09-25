# Enemy and mechanics playbook

Sources: Speed Demos Archive run notes, TASVideos submission 5236 notes, ZeldaSpeedRuns tech pages,
plus the bot's own measurements (marked *measured*). Several wikis block automated reading, so this
grows as sources become available and as the bot learns.

## Sword (*measured*)
- At FULL hearts the sword fires a beam: same damage, straight line, any range (human reminder,
  2026-09-12). Use it on anything aligned on a row/column; Darknuts, Pols Voice, Armos and
  Bubbles are projectile-immune. One more reason a no-damage run is also a faster run.
- Wooden sword connects when the gap between Link's box and the enemy's box is <= 10 px on the
  facing axis and the boxes overlap on the other axis. Misses at 13+ px. So fighting = get almost
  touching-close, align within ~4 px, swing.
- A swing commits Link for ~12 frames. Attacking is disabled while standing in a doorway.
- Never swing unless a target is inside reach (viewer's correction, 2026-09-11).

## Drops and counters (community rules, to be verified in RAM)
- $50 counts kills toward a forced "help" drop every 10 kills; the 10th kill must be by an enemy
  that can drop items or the counter "locks" (the TAS exploits this on purpose).
- Consecutive kills without being hit: 10 -> blue rupee (a bomb if the 10th kill was by bomb),
  16 -> fairy (full heal), then every 10th -> blue rupee/bomb.
- Enemies sit in four drop groups; the bomb-dropping group drops bombs at kill 1, 6 and 8 of the
  cycle. Which enemies are in which group: still to confirm.
- A drop uses the room-item slot ($AB id, $83/$97 position, $BF status FF = empty). Bombs are id
  0x00, heart 0x22, fairy 0x23, key 0x19, rupee 0x18, five rupees 0x0F, clock 0x21.

## Enemies
- **Zol** (2 hp): slow hopper; one wooden-sword hit splits it into two Gels (1 hp). Fast route
  avoids fighting them. Easy kills for counter management.
- **Gel** (1 hp): tiny, slow. Cannot drop items ("no-drop" enemy) — use for counter locking.
- **Keese** (1 hp): erratic fliers, half-heart contact. Don't chase. Ambush: hold position, swing
  when one drifts into reach. *Measured*: scripted ambush is fragile; randomized search from a
  bookmark clears a 5-Keese room in ~1100 frames.
- **Red Darknut** (4 hp) / **Blue Darknut** (8 hp): shield blocks frontal blows; hit from the side
  or behind. A bomb works only if it registers a side/back hit. One heart of contact damage.
  The bot now reads their facing ($98+slot) and refuses frontal swings.
- **Blade trap** (type 0x49): unkillable corner blades; slide at Link when he enters their row or
  column, then crawl back. Juke: step into the line to trigger, step out, cross while it resets.
  The planner treats trap rows/columns as a cost band.
- **Bubble**: touching it disables the sword for a while. Avoid; standing on a ladder blocks it.
- **Wizzrobe**: teleports and fires magic the small shield can't block. Bombs; precise positioning.
- **Manhandla** (Level 3 boss): *measured* five objects of type 0x3C (4 heads at +/-16 px around a
  core), 4 hp each. Bomb power 4 = any part in the blast dies; blast on the core kills all. It
  drifts slowly (~0.5 px/frame) toward Link. Fireballs are type 0x56, straight lines from a head to
  where Link stood; dodge perpendicular early (human coaching). Bomb lands ~18 px in front of Link,
  blast ~78 frames after B. Winning attempt: lead its drift by ~80 frames, one bomb, 199 frames.
- **Blade trap** *measured*: does NOT trigger at 15 px off its column; the trigger band is narrow
  (near-exact tile alignment). Bombing Level 3's east wall from x=184 stays clear of the traps.
- **Aquamentus** (Level 1 boss): fireballs; sword or bombs from the side.

## Never chase (*measured* 2026-09-12)
Zora (0x11) and Peahat (0x1A) are killable in principle but must never be chased: the Zora
submerges in water Link cannot enter, and the Peahat is invulnerable while airborne. The bot died
on the way to the White Sword trying to kill a Zora that was "blocking the lane". Route around
them; they still count for the path-cost penalty.

## Room rule: avoid unless the route says fight
Default for every room is AVOID: path around enemies, kill only what stands in the way. Fight only
when (a) the doors are shutters that need the room cleared, (b) the route needs a drop (bombs,
a key carried by an enemy), or (c) killing is cheaper than dodging. Every room gets one of these
tags before it is played.

| Level 3 room | Tag | Why |
|---|---|---|
| 7C entrance | avoid | empty |
| 7B Zols | avoid, grab key | key lies on the floor; Zols split when hit |
| 6B Zols | avoid | pass-through |
| 5B three Red Darknuts | avoid (optional: kill one for a bomb chance) | doors open without kills; guide uses it for bombs |
| 5A traps + Keese | avoid, grab compass | traps can't be killed; juke their lines |
| 4B Zols | avoid, unlock left door | needs one key |
| 4A Keese corridor | avoid | fliers; ambush only if forced |
| 49 Bubbles/Zols/Keese | avoid, grab key | Bubble contact disables the sword |
| 59 five Red Darknuts | MUST CLEAR | shutter room (confirmed by the human) |
| beyond 59 | unknown | exploration continues after 59 |

## Cellars (*measured* 2026-09-12)
Cellars run in game mode 9 (not 5). Level 3's raft cellar is shared-grid room 0F. Entered by
walking fully onto the stairs tile (70-73) at (208,141) in room 69.

## Fights: use lookahead (2026-09-12, *measured*)
zelda/lookahead.py: every 8 frames, branch on an in-memory savestate over 9 macros (4 holds, 4
swings, wait), roll out ~14 frames, score (death -100000, half-heart -800, enemy hp -1 +60, kill
+150, in front of a Darknut -60, pull toward side/back strike spots). Five-Darknut gauntlet:
cleared in 890 frames at full hearts, first try, sword only. Hand-written reactive fighters never
managed it. Use lookahead for every non-trivial fight and for dashes (plan_reach).

## Darknut rooms with several of them (walkthroughs, 2026-09-12)
- Human correction 2026-09-12: prefer the SWORD; the beam (full hearts) DOES damage Darknuts when
  it hits their side or back. Bombs are a fallback, not the plan. Reference: LackAttack's runs
  (100% no up+A WR 35:15, https://www.youtube.com/watch?v=4tdjN3I1i2I); *measured*: 400 bomb-tactic
  attempts gave 2 successes, both at 1 heart.
- Bombs kill a Red Darknut outright (power 4 = its hp). In the five-Darknut gauntlet use bombs:
  drop one in a Darknut's lane as it approaches, sidestep out of its line. Keep 2 for the wall and
  Manhandla; the corridor Keese (4A) drop 4 bombs when cleared, so clear it first.
- Alternative (TheRewster): lie in wait beside a block and hit them as they pass, before they turn.
- Chasing one Darknut in a crowd fails: the others walk into Link. *Measured* five times.

## Darknut technique (human coaching, 2026-09-11)
- Zero damage from the front. Only side or back hits count.
- Never retreat in a straight line down their facing; they catch up. Sidestep perpendicular.
- Set up beside them relative to their facing and strike when they are at 90 degrees to you.
- They walk on the 16 px tile grid and can only turn when exactly centred on a tile. Between tile
  centres their path is guaranteed. Link moves freely, so: read the lane, stand beside it a tile
  ahead, strike as they pass, before the next centre. Move in committed 8 px steps, not per-frame
  direction flips.

## Level 3 map (nesmaps.com, first quest; room ids row/col = y/x)
```
      x=9      x=A        x=B        x=C        x=D
y=2   -        2A Keese,key,raft   2B old man   -          -
y=3   -        -          3B Zols    -          3D TRIFORCE
y=4   49 Bubbles/Keese/key  4A Keese corridor  4B Zol ring, key, LOCKED doors L+R  4C Keese/Zols, map  4D MANHANDLA + heart
y=5   59 5 Darknuts  5A traps/compass  5B 3 Darknuts  5C Darknuts  5D Keese/Bubbles
y=6   69 5 Darknuts  -     6B Zols (key carried)  -          -
y=7   -        -          7B Zols, key  7C ENTRANCE (statues)  -
```
Door types read from the ROM tables (zelda/romdata.py): 0 open, 1 wall, 4 bombable, 5 locked,
7 shutter. Verified against every door the bot walked through.

| Room | N | S | W | E | Item |
|---|---|---|---|---|---|
| 7C entrance | wall | open (exit) | open | wall | - |
| 7B | open | wall | wall | open | key on floor |
| 6B | open | open | wall | wall | key (after clear) |
| 5B 3 Darknuts | open | open | open | bombable (to 5C) | BOMBS after clear |
| 4B Zol ring | locked (3B) | open | locked (4A) | locked (4C) | key (after clear) |
| 4C map room | wall | open (5C) | locked | bombable (to 4D!) | map |
| 4D Manhandla | shutter (3D) | shutter (5D) | bombable | wall | heart container |
| 3D | wall | open | wall | wall | TRIFORCE |
| 59 gauntlet | open | shutter | wall | locked | - |
| 5C | open | wall | bombable | shutter | - |
| 5D | shutter | wall | shutter | wall | rupees |

RAFT (corrected again 2026-09-12, from GameFAQs answers + ROM): the raft is in a CELLAR in the
southwest, entered by stairs on the right side of room 69, below the five-Darknut gauntlet 59.
59's south door is a shutter: the five Darknuts must die. The north wing (3B/2B/2A) has no raft;
2A's floor item is just a key. Level 3's cellar list in the ROM header is empty, so the stairs in
69 are part of its layout, not a block secret.
FAST ROUTE: 7C -> 7B (key #1) -> 6B -> 5B: CLEAR 3 Darknuts, bombs appear -> 4B: unlock WEST ->
4A corridor -> 49 (key #2) -> 59: CLEAR 5 Darknuts -> 69 -> stairs -> cellar: RAFT -> back up
69 -> 59 -> 49 -> 4A -> 4B: unlock EAST -> 4C: BOMB the east wall -> 4D: bomb Manhandla ->
3D: Triforce. (Milestone 3's first verified run skipped the raft.)
Rule (human, 2026-09-12): waiting in place is not progress. If an enemy blocks the only lane,
detour; if there is no detour, kill it (it is "in the way").
No-bomb alternative: 4C south -> 5C clear -> 5D clear -> 4D. Two extra shutter fights; slower.
Off-route entirely: 5A, 4A, 49, 59, 69, 2A, 2B, 3B.

## Level 3 notes (from exploration)
- 7C entrance -> 7B Zol room (key on floor, take it by dodging) -> 6B Zols -> 5B three Red
  Darknuts -> 5A traps + Keese (compass) -> 4A Keese corridor (bombs may drop) / 4B Zols with a
  locked door to 4A -> 49 Bubbles+Zols+Keese (key) -> 59 five Red Darknuts (gauntlet).
- 5A's left door is locked and opens straight into the trap lines: juke required.

## Bombs are a resource, not a weapon (human note, 2026-09-13)
Never bomb an ordinary enemy. A Stalfos, a Goriya, a Zol all die to the sword for nothing, and the
bombs are needed elsewhere: Dodongo can only be killed with them, and several routes need a wall
blasted. The lookahead planner only offers a bomb when one blast covers three or more enemies at
once, or when the caller says the target ignores the sword (`use_bombs="free"`, e.g. Dodongo).
Even then a bomb costs 320 points in the scoring, so it has to pay for itself in kills.
