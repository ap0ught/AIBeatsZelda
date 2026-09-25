# Phase 7: Level 3, room by room

**Reading the dungeon from the cartridge.** After days of bumping into walls, I found the game's
own room tables in the ROM: for every room, one byte for the north and south doors, one for east
and west, one for the monsters, one for the item. Decoding them against the doors the bot had
already walked through gave the codes: 0 open, 1 wall, 4 bombable, 5 locked, 7 shutter. With
that, the fastest route through Level 3 was obvious and most of the rooms the bot had been dying
in were not on it at all. The three-Darknut room drops bombs when cleared, and the map room's
east wall is bombable straight into the boss. That is the speedrun route, derived, not copied.

**Darknuts, properly.** The human on the project gave two rules from experience: they take zero
damage from the front, and they only turn when exactly on a tile. A per-frame trace of a fight
confirmed the facing byte matches their movement, and showed both hits were contact: once Link
stood still mid-swing while a Darknut walked down his row into him, once the bot walked Link
sideways into the target's column. So the fighter now predicts where every Darknut will be over
the next dozen frames, and no step or swing is allowed to end inside that path. Second attempt
after that change: all three Darknuts dead, no damage, eight bombs.

**Three bugs that cost hours.**
- A leftover bomb-smoke object counted as an enemy, so the planner refused to walk through the
  hole it had just blown. Real monsters have low type numbers; effects don't.
- The boss fight read a "bomb burning" flag that was stale from the wall bomb, so the bot politely
  waited for a fuse that didn't exist and never pressed a button.
- The boss room floor is a tile the bot had never explicitly confirmed, and its knowledge base only
  ever recorded what was solid. Every step was refused. Now successful steps teach it walkable
  tiles too.

**Manhandla.** Five objects, four heads and a core, four health each. A bomb deals four, so any
part inside a blast dies at once. The bot leads the boss's drift by the bomb's fuse and drops the
bomb where the core will be. The search killed it on attempt eleven, in 199 frames, with one bomb
and no damage. Then the heart container, the shutter, and the Triforce. Level 3 is done.

**Traps, as coached.** Blade traps trigger only when Link is nearly exactly in their row or
column, narrower than I first assumed. The bombing spot for the east wall sits outside the
right-hand traps' column, so that wall needs no juke at all. The planner keeps trap lines as
near-forbidden and treats a trap that has left its corner as a fast enemy.
