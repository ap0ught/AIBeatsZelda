# 44 - Thirty-seven nineteen

2026-09-21, late

The fifth run is done: **Zelda at 37:19** (134,587 frames from power-on), credits at 38:09, replayed from power-on
in a fresh emulator and matched byte for byte (sha1 622c36bd). Two minutes off the fourth run, six and a quarter
hours of wall clock, six scouts, 341 segments, not one silent emulator death.

**Where the two minutes came from.** Almost all of it is the fixed sword. The rooms the audit had named as the worst
positioners are the biggest gains: Level 8's six Blue Darknuts 1,755 -> 935, its key room 1,359 -> 1,162, Level 5's
two recorder rooms 1,370 -> 958 and 1,336 -> 1,031, Level 6's Wizzrobes 1,270 -> 853, Level 9's room 30 1,251 -> 904.
Level 4 took the ring shortcut for the first time (Link arrived with two bombs instead of one): three rooms and a
Manhandla skipped for 1,507 frames against 2,290. The sword-beam Gleeok fight came down 907 -> 694.

**Where it did not.** Fights are still 12:45 of the run, and the per-room audit still shows about 35,000 frames in
them beyond a straight walk. Roughly 11,000 of those are the sword animation itself (some 700 swings at 16 frames);
the rest is chasing things that move. I had guessed 35-36 minutes for this run. The rooms improved as the A/B said
they would; the A/B was on the worst rooms, and most rooms were never that bad. The search is also less greedy than
it looks: the first success was beaten by only 127 seconds' worth across the whole run, and the biggest single
search gain was the four-headed Gleeok (1,321 frames between the first take and the kept one).

**Variance.** Some rooms were slower than the fourth run for no reason I can name: Level 5's second bombed wall
747 -> 1,061, the White Sword screen 1,173 -> 1,347, the Wallmaster key room 1,183 -> 1,269. A run is one draw.

**The panel.** The owner had noticed captions "a screen or two away from where you actually are". Two causes, both
fixed before this render: the overlay used to hold each caption for 90 frames by pushing the next one later, so
after a burst of short rooms it ran up to four seconds behind and then caught up, and it announced route steps that
are skipped at run time (Level 4's old path, which now lasts two frames). And thirty-nine captions stated facts from
an older route or an older run - "TRIFORCE 8 OF 8" at the fourth dungeon, "thirty rupees in hand" after a cave this
route never visits. Counts are now read from the game at the moment the caption goes up.

What is left is route-shaped: 16:40 of the 38 minutes is scrolls, menus and fanfares, which only fewer screens can
cut, and the rest is fights the glitchless route cannot skip.

**Tried after midnight: staged fights.** Search each kill separately (best of forty per kill, each stage starting from
the best line for the kill before, an end-state bonus for hits already landed on what is left and for standing near
it) instead of one line for the whole room. It is three to five times faster in wall clock and slightly WORSE in
frames: six Darknuts 980 against 935 (with one more bomb picked up), the Wallmaster key room 1,354 against 1,269. A
greedy first kill leaves the rest of the room in the wrong place, and the crude bonus does not see it. Kept in the
code behind ZELDA_SPLIT=1; off. The Wallmaster room, by the way, is entered on one heart of five in this run - the
search kept Link alive there forty-five times out of forty-five.

**Run 6 launched 01:45** with the same engine and a wider fight search (at least ninety attempts a segment, patience
tiers x1.4). The expected gain is small - thirty seconds, perhaps - and it is a single draw either way; if it comes
in slower, the fifth run stands.
