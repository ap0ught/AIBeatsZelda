# 43 - The sword that went sideways

2026-09-21

The owner watched the 39:15 run and said two things: Link paths around monsters instead of killing them and walking
through, and he "sits there and thinks". I measured it before arguing. Of the 40 minutes, 23:24 is play; 14:21 of that
is in rooms where something has to die; and in those rooms only about three minutes is walking that gets Link across
and two is sword animation. About EIGHT minutes is positioning - circling, backing off, waiting for an opening. He was
hurt only 36 times in the whole run. Everything pointed at cowardice, and I told the owner so: I had priced a lost half
heart at up to thirteen seconds.

**The first experiment said I was wrong.** Pricing damage at a quarter, or a twentieth, of what it was made the worst
rooms 0-12% faster, and the reckless setting was *slower*: a hit is a knockback, and a knockback is time. The price of
damage is not where eight minutes went.

**So I printed every decision of one fight.** Six Blue Darknuts, 2,246 frames. For 160 of them Link zig-zagged between
two Darknuts that were each exactly one sword-length away, flank exposed - and every swing the planner simulated at
them scored as a miss. Link at (158,149), Darknut at (154,125) walking left: swing Up, nothing.

**Why.** Zelda moves Link on an 8-pixel grid. To turn from a horizontal walk to face up, he must stand on a grid line;
if he does not, the game first SLIDES him along his old axis to the nearest line - still facing left or right - and only
then turns him. My swing was "press the direction for one frame, press A". Off the grid, that one frame is a sideways
slide, so the sword came out sideways. A walking stride of eight frames is 12 pixels, which lands on a grid line every
other stride: about half of all perpendicular swings, bombs and arrows in ten days of play went out in the wrong
direction. The search quietly filtered the failures out, which is why nothing ever "broke" - the planner just learned
that flank attacks mostly do not work, and circled.

**Fix.** `face()`: hold the direction until Link's facing byte says he faces it (at most four more frames), then strike.
Applied to the fight planner's swings, bombs and arrows, the boss planner, the fighter, the cellar beam and Gohma's bow.
Also new: the planner now tries "walk 8 or 16 frames, THEN swing" so it can see a hit one move ahead instead of only
the hit available this instant, and a hold that only grid-snaps Link against a wall is priced as the waste it is.

**Numbers.** Mean frames for a single unrehearsed attempt at the room (six seeds each), from run 4's own states:

| room | before | facing fixed | + walk-then-swing | run 4 kept (best of 50-60) |
|---|---|---|---|---|
| Level 8, six Blue Darknuts (r8_3f) | 2,342 | 1,628 | **1,306** | 1,755 |
| Level 8, key room (l8_5e_key) | 2,121 | 1,850 | **1,363** | 1,359 |
| Level 5, recorder room (l5_rec_st) | 1,778 | 1,741 | **1,332** | 1,370 |
| Level 9, room 30 (g9_30) | 1,410 | 1,439 | **1,063** | 1,251 |
| Level 6, Wizzrobes (l6_28) | 1,321 | 1,247 | **1,055** | 1,270 |
| Level 7, room 0C (l7_0c) | 1,484 | - | **1,196** | 961 |
| Level 3, room 59 (59_fight) | 1,320 | 849 | 1,008 | 879 |

An average FIRST TRY now beats what fifty rehearsals used to find. Hits land 30-46 frames apart, against the 32 the
game allows (a struck monster is untouchable for 32 frames; measured from $4F0). Bosses too: Gohma went from
1,508 / 629 / one failure in three tries to 245, 245, 267 - every arrow used to have a coin-flip chance of leaving
sideways. Manhandla 343 -> 227.

Tried and dropped: a three-step look-ahead (no better than two, costs more), steering away from monsters that are
still flashing (no effect), a lookahead "dash" through dungeon rooms instead of the navigator (better in some rooms,
much worse in others - kept as one attempt in four so the search can pick it where it wins).

Also gone: the two idle "settle" frames at the head of every one of 341 segments - eleven seconds of standing still
that nothing needed.
