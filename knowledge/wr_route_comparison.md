# The human record route against the third run (researched 2026-09-19)

## The leaderboard and its rules (speedrun.com/the_legend_of_zelda, API v1)
* **Any% No Up+A, First Quest**: 1. Schicksal 27:40 (2026-02-13), 2. Greenmario 27:42 (2025-01-19), 3. Antlerz44 27:53,
  4. lackattack 27:57 (2020), 5. rcdrone 28:15. All on real NES/Famicom hardware.
* **Timing**: "begins with control of Link on the Overworld. Timing ends with loss of control upon standing next to
  Zelda." Our run by that clock: first overworld control at frame 278, ending trigger at 148,766 = **41:10.7**
  (41:15 from power-on).
* **Glitches are allowed** in Any% No Up+A: screen scroll, block clipping, recorder wrong warp (Zelda Dungeon wiki).
  Only the controller-2 Up+A save-and-quit is banned.
* **Extreme Rules** is NOT plain glitchless: "Timing ends the instant Link holds up the Triforce in Gannon's room.
  No Glitches, No block clips, No Swords, No Extra Hearts." (record 1:08:07). The owner does not want it attempted;
  he had hoped it was a glitchless any%. There is no plain glitchless category on the board.

## The current record route: "Three First Blue Candle" (Order of the Ate, advanced routes)
Wooden sword -> **screen scroll to Level 3** -> Level 3 -> Level 4 -> Level 1 (leave with ~30 rupees and 5-8 bombs)
-> heart container at the heart rock -> 30-rupee secret to the east -> **buy the BLUE CANDLE** east of Level 5 ->
screen scroll to Level 5 -> recorder to Level 3 -> the 100-rupee secret north-west of Level 3 (our 0x62 tree) ->
**world wrap south** for the ladder heart and the raft heart -> 30-rupee secret at Level 2's Armos (our 0x3D) ->
scroll to Level 2 -> recorder to Level 4, buy MEAT and ARROWS (the same shops we use) -> Level 7 ->
graveyard: **MAGIC SWORD** (6 dungeons + 3 overworld hearts + 3 = 12) -> recorder: Level 6, Level 8, Level 1's
door, walk to Level 9.
The red-candle variant notes "a bomb shortage going from Level 5 to Level 7" and "a tough spawn pattern in the
Level 7 wallmaster room". A Raft Skip was found in October 2025. Per-level maps on that site are images.

Differences from our route (3-1-WS-4-2-5-shops-6-7-8-heart-MS-9):
* No White Sword at all (ours costs ~17 extra overworld screens + the cave, ~5,500 frames).
* Magical Sword BEFORE Levels 6, 8 and 9 (ours: only before 9).
* Blue candle bought; Level 7's red candle never fetched (ours: ~2,400 frames in Level 7; we were 5 rupees short).
* Overworld legs kept short by order + recorder; ours is 138 screen entries / 51,852 frames.

## Mechanics worth modelling (redcandle.us/The_Legend_of_Zelda#Drops)
* **Forced drops**: 10 kills in a row without being hit (a Bubble or the whirlwind counts as a hit) force a drop on
  the 10th: 5 rupees - or **BOMBS if the 10th kill is made with a bomb**. 16 in a row forces a fairy (if that enemy
  can drop at all). A forced drop resets the 10-counter, not the fairy one: 10, (16), 26, 36... Gels from Zols and
  Keese from Vires do not advance the counter; simultaneous kills cannot pass 10.
* Ordinary drops: four enemy groups A-D with 31/41/59/41 % drop chance, item chosen by the kill counter's position.
* A just-hit enemy can be walked through without damage or knockback (if it is not knocked back or split).
* Bombs hurt a Darknut depending on Link's facing when he lays the bomb and the Darknut's facing at the blast.
* Recorder: facing Up/Right steps the destination counter up, Down/Left down (matches our $523 finding).

Sources: speedrun.com API (games/the_legend_of_zelda/categories, leaderboards/.../category/wdmw952q),
sites.google.com/view/orderoftheate/the-legend-of-zelda (advanced-routes/three-first-blue-candle, three-first-red-candle),
redcandle.us/The_Legend_of_Zelda, zeldadungeon.net Speedrun:The_Legend_of_Zelda_Any%_No_Up+A, guinnessworldrecords.com 110314.

## The drop system, from the disassembly (Z_01 HandleMonsterDied, Z_04 drop routine) - 2026-09-19
RAM: HelpDropCount $50 (kills in a row, caps at 10), HelpDropValue $51 (set when the 10th kill's damage type was
BOMB), WorldKillCount $627 (16 -> fairy), WorldKillCycle (column 0-9 of the table below).
* When HelpDropCount reaches 10 the dying monster's drop is GUARANTEED: bombs if $51 != 0, else a 5-rupee. Both
  counters then reset. Otherwise the drop is the table entry for (monster group row, WorldKillCycle), made only if
  Random < rate (row 0: 0x50/256, row 1: 0x98, rows 2-3: 0x68).
* Rows by monster type - row 0: 07 08 0E 04 0F 23; row 1: 21 22 0D 10 13 28 2A 27 16; row 2: 09 0A 03 01 12 06
  0B 24 30; row 3: everything else.
* DropItemTable (22 heart, 18 rupee, 0F five rupees, 23 fairy, 21 clock, 00 BOMBS):
  row 0: 22 18 22 18 23 18 22 22 18 18     row 1: 0F 18 22 18 0F 22 21 18 18 18
  row 2: 22 00 18 21 18 22 00 18 00 22     row 3: 22 22 23 18 22 23 22 22 22 18
  -> ordinary bomb drops only come from row-2 monsters (blue Octoroks, blue Moblins, blue Lynels, Vires, red
  Goriyas, red Darknuts, blue Wizzrobes, Gibdos) at cycle 1, 6 or 8.
* So: with $50 == 9, kill the next monster WITH A BOMB -> four bombs back for one. With the sword -> five rupees.
  A hit on Link resets $50, $51 AND $627 (Z_01 Link_BeHarmed - the whirlwind's 'harm' too), so a streak is
  worth protecting when bombs or rupees are short. Dodongo's death SETS $50=$51=10: the next kill after
  Level 2's boss drops bombs for certain.
* The kill cycle ($52A) is advanced FIRST, then used as the table column (Z_07 ~5465): a row-2 monster can drop
  bombs when the cycle BEFORE its death is 0, 5 or 7 (41 % of the time). Child Gels (14), red Keese (1C) and type
  5D do not advance the cycle; Zoras advance it but do not count toward the room's kills.
