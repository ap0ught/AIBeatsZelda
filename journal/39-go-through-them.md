# 39 — Go through them

The owner watched the 58-minute run frame by frame and sent a list: Link "sits there attacking the air for about
15 seconds", gets "stuck in the dark room ... nearly 30 seconds", "struggles navigating the walkway", walks all
the way round five Zols, stands for ages before bombing a wall, takes keys he never uses, fights eight Pols Voices
with a sword. And the principle behind all of it: *"you should generally just go through them and kill them if
they get in the way rather than avoid them. your pathing takes longer than just killing them."* Human records are
under 30 minutes; the target is to get into that neighbourhood.

A quarter of the 58-minute run (49,851 frames) was Link **standing still in normal play**. Every item on the
owner's list turned out to be a mechanism, not bad luck:

| What the owner saw | What it was | Fix |
|---|---|---|
| attacking the air, 15 s (l4w04_18) | the navigator decided a **burrowed Leever** was "blocking the only lane" and swung at it 60 times; the game does not even collision-check a Leever unless its state is 3 | `Navigator.threats()`: only what can hurt *now* (ROM damage table at 0x72CA; Leever/Zora/Wizzrobe states) |
| long stand before bombing (l8_3c, s9_05) | 600 frames "waiting" for an **old man's flame** to move away from the next step | never wait (except a sliding blade trap); swing at what is directly in the way |
| walking round everything | path penalty 120 within 24 px of any enemy = a 960-px detour is "cheaper" than a pass | penalties scaled by real contact damage: 5/1.5 per half-heart |
| stuck in the dark room, the walkway, the ladder rooms (L4) | the tile knowledge base had **learned water as walkable** (Link "stood on it" - on the stepladder), so the planner routed straight across four tiles of water and burned attempts on BLOCKED moves; plus a bug that treated a horizontal ladder crossing as "stuck in scenery" | water is never floor; ladder axis rule; l4_02 went 0/6 -> 6/6 at 469 frames |
| stuck on a wall piece swinging at nothing (g9_41) | lookahead shaping was **Manhattan distance**: with a block in the way every hold was "blocked" or "further", and a swing (cost 5.6) was the best move | `Lattice`: BFS walking distance over the room; swings offered only with something in reach |
| slow, timid fights | half a heart cost 800-1600 points against 0.5 per frame regardless of health | `caution()`: full price when low, ~1/3 when healthy, ~1/8 before a Triforce refill (only with health to spend) |
| the whirlwind sits there (wl8_3c) | the destination counter is RAM **$523**; each note moves it one owned level (facing Right/Up = +1), even with a wind on screen, and the game - the wind too - **freezes for the $98-frame tune**. The old policy pressed again inside the freeze (lost notes), so every ride moved one level, and it spent a whole ride "learning" the counter | read $523, play N notes back to back, one ride. ms_w22: 2,082 -> 905. Also: items cannot be used in the screen's border strip; the wind MISSES Link while he is flashing from a hit, so walk to meet it |
| extra keys (finished with 6) | keys were taken wherever the first exploration found them | door-table audit (below) |
| Pols Voices with the sword | an arrow branch looked 26 frames ahead; the arrow had not landed yet, so every shot scored as a miss | 44-frame arrow rollout - and then the room was skipped entirely |

## The door tables had more to say

Reading the cartridge's door table against the route found whole loops that existed only because the first run
explored that way:

* **Level 8**: the passage surfaces in 4C among eight Pols Voices, and 4C's *north wall is the boss room's south
  wall*. Dash, bomb, dodge the fuse, go: ~810 frames with no damage (4/4), against 4,121 for shooting all eight
  and going round. 5E's north shutter opens straight onto 4E, so the 5D-5C-4D loop goes too.
* **Level 6**: 28's east wall is 29's west wall. One bomb skips the Gleeok mini-boss, a locked door and the
  1A-1B-0B excursion to an old man's dead end - about 7,000 frames.
* **Level 7**: the 3A key detour was unnecessary, and *re-entering 39 afterwards is what spawned the Digdogger*.
* **Level 5**: 77's key detour, the 56/57 excursion and clearing 65 were all residue. 66's key is a floor key.
* **Level 1**: with Level 3's bombs in hand, bomb 53's north wall (280 frames) instead of the keys-only loop.
* Keys whose ROM flag says "lying on the floor" are grabbed, not fought for (L4's dark room: 1,579 -> 606).
* Rooms whose exit is open or locked are crossed, not cleared (l7_19: 2,653 -> 452).

## And four scouts

`parallel_search`: K emulators, one thread each (emulation is socket I/O, so the GIL is not in the way).
With the faster policies the third run reached Manhandla - 10,514 frames of game - in under four minutes of wall
clock. The scripted Manhandla bomber then died 60 times out of 60; the lookahead fighter with bombs free killed
it 8 of 8 in ~200 frames, so it has the job now.

## Left for next time
* L5 -> shops by whirlwind to Level 4's island (two notes) instead of 17 screens on foot: ~3,000 frames.
* L7 0D: push the block from the corridor side so Link is next to the stairs when they appear (~200).
* L4 10 -> 11 -> 12 by bombs worked 1 of 3; not worth two bombs.
