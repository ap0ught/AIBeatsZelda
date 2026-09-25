# Money: where Hyrule keeps it, and how to make the game hand it over

Written after the run twice ground to a halt for want of 60 rupees. Farming a dungeon's entrance
rooms works but costs about ten thousand frames and several hearts per twelve rupees, so the
secret caves are worth finding properly.

## The tool

`zelda/secrets.py sweep(emu, nav)` finds a screen's hidden entrance by trying everything:

* **bomb** every rock face (2x2 blocks of tiles C4-C7), standing one tile away and two - a bomb
  lands about a tile in front of Link, so pressed right up against the rock the blast can land
  past it;
* **push** every gravestone / Armos-like block (C0-C3, CE-D3, E0-E3) from all four sides;
* **burn** every tree (D8-DF) with the candle, from all four sides.

Every trial reloads an in-memory snapshot, so a whole screen is swept for no bombs and no game
time. It is validated: run blind on screen 0x34 it rediscovered the gravestone that hides the
food shop (push from (48,125) facing Right), which had been found by hand an hour earlier.

## Coordinates

The community maps write a square as `<number><letter>` (7C) or `<letter>-<number>` (E-5). Both
count the **number as the row from the TOP, starting at 1**, and the letter as the column A-P:

    room = ((number - 1) << 4) | (letter - 'A')

Verified against three things this run has actually stood on: the wooden sword cave 8H = 0x77
(the starting screen), the White Sword 1K = 0x0A, and the arrows shop E-5 = 0x44.

## The list (from the community maps, converted)

| Amount | Squares | Rooms |
|---|---|---|
| 100 | 1P, 7C, 7L | 0x0F, 0x62, 0x6B |
| 30 | 2D, 3I, 3N, 4N, 5I, 7H, 8B | 0x13, 0x28, 0x2D, 0x3D, 0x48, 0x67, 0x71 |
| 10 | 5O, 6B, 6G, 6L | 0x4E, 0x51, 0x56, 0x5B |
| gamble | 2A, 2G, 2P, 8G, 8M | 0x10, 0x16, 0x1F, 0x76, 0x7C |

## What the sweeps have established so far

| Screen | bomb | push | burn | result |
|---|---|---|---|---|
| 0x62 (100) | 31 spots, entering from the west and from the north | no targets | no candle yet | not found |
| 0x28 (30) | 84 spots | no targets | no candle yet | not found |
| 0x48 (30) | 60 spots | no targets | no candle yet | not found |
| 0x34 (shop) | no targets | **FOUND** (48,125) Right | - | the food shop |

So **none of the rupee caves tried so far is a bomb secret**, and the only method left untested is
the candle. That is not a coincidence: most of Hyrule's "IT'S A SECRET TO EVERYBODY" caves are
under a burnable tree. Link has never owned a candle in this run.

**The Red Candle is Level 7's own item**, in a cellar behind the hungry Goriya. So the order is:
finish Level 7, take the Red Candle, then sweep the screens above for burns. After that the money
problem is solved for good - and Level 8's front door, which is a burnable bush on square N-7
(room 0x6D), opens with the same item.

One caveat measured on 0x62: that screen is a canyon whose east and west halves do not connect on
screen, so a sweep entered from the west can only reach half of it. Where a screen is split, sweep
it from both sides.

## Swept and measured, 2026-09-15 (trust this table, not the community map)

| Screen | Community map | What the sweep found | Measured payout |
|---|---|---|---|
| 0x62 (7C) | 100 rupees | **NOTHING.** 92 reachable spots bombed, pushed and burned | - |
| 0x0F (1P) | 100 rupees | **UNREACHABLE.** Screen 0x0D's east side is solid mountain; the walk dead-ends | - |
| 0x67 (7H) | 30 rupees | BOMB from (112,93) facing Up -> opening (112,77) | being measured |
| 0x28 (3I) | 30 rupees | BURN from (208,141) facing Down -> opening (208,157) | **+30 in 1,150 frames** |

That is 38 frames per rupee against roughly 620 for farming a dungeon's entrance rooms - sixteen
times cheaper - and it is why the re-run deletes both farms.

The community map has now been wrong about 0x62 (nothing there), 0x0F (cannot be reached at all) and
three earlier screens. The ROM's own secret table at file offset 0x18690 is the authority for whether
a screen has anything: 0x03 means the entrance is already drawn, bit 6 set means a hidden secret,
bit 6 clear means nothing. The amount, though, is not in that table - only walking in and reading
$066D tells you what it pays.

## The constraint that decides which caves are worth anything (2026-09-15)

Money is not fungible across the route, because the TOOL that opens a cave arrives at a fixed time:

* **Bombs** arrive in Level 3/Level 1 - early. A bomb cave can fund anything.
* **The candle** arrives in LEVEL 7 (the Red Candle). Every burn cave - including the verified
  100-rupee tree on 0x6B and the 30 rupees on 0x28 - is therefore unreachable until after Level 7.
* **Walk-in caves** (ROM secret byte 0x03, entrance already drawn) need no tool at all.

The 80 rupees for ARROWS must be spent BEFORE Level 6, because Gohma cannot be killed without them.
That is precisely why the first run farmed: at that point in the route Link has no candle, and the
only money it knew about was behind one.

So the caves that can actually replace the first farm are, in order of value:
1. **0x1A** - the ROM marks it 0x03 (walk-in). The route already crosses it early, twice, in the
   Level 4 travel chain (l4w00_1a, l4w02_1a). A walk-in cave here costs a detour of zero.
2. **0x67** - a BOMB secret, confirmed by the sweep at (112,93) facing Up, and bombs are available
   early. Three probes have opened it and reached the mouth; none has yet read the payout, because
   both cave policies bail on their own success tests. Worth one more careful probe.
3. 0x28 / 0x6B (burn) - real money, but only after Level 7. They can fund the bomb capacity upgrade
   and the monster bait, not the arrows.

## What is actually inside the two early caves (screenshots, 2026-09-15)

* **0x1A - "PAY ME AND I'LL TALK." (-5 / -10 / -20).** This is the information old man: he TAKES
  money. The ROM secret byte 0x03 only means "there is an entrance here", never that it pays. The
  route must not walk into this one. The entrance is a PUSH secret at (96,141) facing Up, which is
  worth knowing only so it can be avoided.
* **0x67 - "IT'S A SECRET TO EVERYBODY."** The giving old man, with the payment on the floor in
  front of him. Opened with a BOMB from (112,93) facing Up - and bombs arrive early, so this one can
  fund the arrows.

Why three probes read "+0 rupees" on a cave that plainly pays: Link enters a cave at the BOTTOM of
the room, the money sits in the middle, and `read_room_item` returns None for these old-man gifts -
so every probe concluded there was nothing to walk to and stood still at the doorway. The fix is to
walk north up the middle and watch $066D, not to trust the item slot.

## MEASURED: 0x67 pays 30 rupees, and it is EARLY money (2026-09-15)

    rupees 7 -> 37 (+30), opened with a bomb from (112,93) facing Up, money collected 222 frames
    after walking in.

This is the one that matters, because screen 0x67 is already on the Level 3 -> Level 1 walk
(segment ow1_67, 380 frames) - long before the 80 rupees for Gohma's arrows have to be spent, and
long before the candle exists. Bombs are all it needs.

Income the route can now count on, in the order it becomes available:

| When | Source | Amount | Cost |
|---|---|---|---|
| On the way to Level 1 | 0x67 cave (bomb) | 30 | ~1,100 frames |
| After Level 7 (candle) | 0x6B cave (burn, already in the route) | 100 | 1,127 frames |
| After Level 7 (candle) | 0x28 cave (burn) | 30 | 1,150 frames |

That is 160 rupees against a bill of 240 (arrows 80, monster bait 60, bomb capacity upgrade 100),
plus whatever drops off monsters along the way. The honest conclusion: the SECOND farm (fd40-fd61,
21,705 frames) can be deleted outright, and the first farm shrinks from nine targets to a single
top-up before Level 6 - it no longer has to earn 80 rupees from scratch, only the gap.

## THE AUTHORITATIVE LIST - Zelda Dungeon wiki "The Legend of Zelda Secret Rupees" (read 2026-09-16)

The owner pointed out 14 first-quest caves worth 550 rupees and that farming is unnecessary. Routes on
that page are given as screen moves from the START screen (0x77; right = +1, up = -0x10), converted:

| Rupees | Room | Opens with | Guide's note |
|---|---|---|---|
| 100 | **0x0F** | NOTHING | reach it by walking UP from 0x1F just right of the cave entrance there - NOT east from 0x0D (why my probe hit a wall) |
| 100 | 0x6B | candle | third tree from the left, bottom row of the central trees (verified +100) |
| 100 | 0x62 | candle | third tree from the top - my sweep burned only the reachable half of this split canyon |
| 30 | 0x48 | candle | top-right tree |
| 30 | **0x2D** | bombs | rocks at the top of the screen |
| 30 | **0x3D** | NOTHING | touch the Armos on the right |
| 30 | 0x70 | bombs | rocks just right of the rigid area |
| 30 | 0x67 | bombs | middle of the top wall (verified +30, taken early in the route) |
| 30 | (NE of Level 6, relative directions from the graveyard) | bombs | top-left rocks |
| 10 | 0x56 | candle | lone tree bottom-left |
| 10 | 0x51 | candle | lone tree bottom-right |
| 10 | (SE of Level 4, Armos) | nothing | Armos on the right |

WHAT THIS MEANS FOR THE ROUTE: before the candle (which is behind Level 7's Goriya) the free and bomb
caves 0x0F + 0x3D + 0x2D + 0x67 are worth 190 rupees, against 140 needed (arrows 80, monster bait 60).
All sit near the Level 2 -> Level 5 stretch the route already walks. No farming is needed at all.
The candle caves (0x6B 100, 0x62 100, 0x28 30, 0x48 30) then fund the bomb capacity upgrade.

## Probed on the route, 2026-09-16
- **0x3D: +30 rupees, CONFIRMED.** Push from (144,109) facing Down reveals the stairs (this is the
  guide's "touch the Armos"); the route already walks through this screen (segment l5w02_3d), so it
  costs only the cave itself. Rupees 52 -> 82.
- 0x2D (30, bomb): the bomb spot is (112,77) facing Left, found when arriving from 0x2C on the LEFT.
  Arriving from below (the route's l5w03_2d), the navigator could not reach the spot.
- 0x0F (100, no item): leaving 0x2D upward at the navigator's default column lands Link at (32,221) on
  0x1D with no path east - a pocket. Being re-probed at other exit columns.

## 0x0F - THE 100-RUPEE CAVE, FOUND (2026-09-16), and what the other probes settled

**How to get there** (none of this is visible to the navigator, which is why it took six probes):
1. From 0x2D go UP leaving at column **x=120**. The default column lands at (32,221) on 0x1D, in a
   pocket with no way east.
2. From 0x1D go Right to 0x1E, Right to 0x1F. Arrive at (0,189).
3. On 0x1F, walk to **x=128 near the top and HOLD UP**. The tile map shows unbroken rock and
   nav.exit_screen refuses every column, but Link walks straight through into 0x0F, arriving at (128,221).
   (harness: fullgame.hold_through_policy.)
4. On 0x0F the staircase is already drawn at **(128,125)**, inside the middle tree stump - a walk-in
   cave, no item needed. "IT'S A SECRET TO EVERYBODY." (harness: secret_cave_policy method "walk".)
5. The hundred is COUNTED UP one rupee at a time - a probe that stopped watching early read +46.

**Other findings:**
- 0x1F's visible stump cave is the **gambling game** ("LET'S PLAY MONEY MAKING GAME") - one probe won
  +20 by luck. Not a money source.
- 0x3D (push the Armos from (144,109) facing Down): +30, but only ~1 attempt in 3 gets in - acceptable
  inside a 30-try search.
- 0x2D (bomb from (112,77) facing Left): the sweep opened it once; the recorded policy went 0 for 6
  across two versions. Left out of the route for now.
- Money plan without any farming: Link reaches 0x3D with ~51; +30 (0x3D) +100 (0x0F) = ~181 before the
  shop, against 140 for arrows and monster bait - plus every drop he can now see.

## CORRECTIONS 2026-09-16 (ROM decode + RPGClassics + in-game probe) - see knowledge/money_ring_boomerang.md
- 0x70 in the table above is WRONG: 0x70 is a pay-me hint cave. The +30 bomb cave is 0x71 (wall (80,80)).
- "NE of Level 6" = 0x13 (bomb the wall at (32,80)); 0x22 has no north exit, so it is ~6 screens on foot.
- "SE of Level 4, Armos, 10" = 0x4E (right Armos, (160,109)).
- 0x62's tree is (128,96) and the flame reaches it ONLY from (96,93) facing Right or (160,93) facing Left;
  the sweeps stood 16 px too close. probe_cave_62b.py took +100 from the west pocket.
- 0x2D: bomb from (80,93) facing Up (the (112,77) spot needed x<112).
- 0x7C is a gambling game; the Blue Ring (250) is sold only at 0x34.
