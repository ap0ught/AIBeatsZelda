# 41 — A map on the table

The owner watched the 41:15 run, asked what the record holders have that the bot does not, and then said what the
next goal is: *"if you could get to 33-35 minutes, that would be incredible."* Still glitchless - he had hoped
speedrun.com's "Extreme Rules" was a glitchless any% (it is not: no glitches, but also no swords and no extra
hearts, record 1:08:07) and does not want that attempted.

## What the record actually is (knowledge/wr_route_comparison.md)
Any% No Up+A, 27:40 (Schicksal, February 2026). Clock: first control on the overworld to Zelda - by that clock the
third run is **41:10.7**. Screen scrolling and block clipping are allowed and used from the first minute ("screen
scroll to Level 3"). The route ("Three First Blue Candle") is 3-4-1-5-2-7-MS-6-8-9: no White Sword at all, blue
candle bought, three overworld hearts, Magical Sword before Levels 6, 8 and 9, the recorder for every long haul,
and bombs on demand from the game's forced drops (the 10th kill in a row without being hit drops bombs if it is
made WITH a bomb).

## Tools built today (no emulator involved: arithmetic on the cartridge's own map)
* `zelda/owmap.py` - decodes all 128 overworld screens from the ROM into the same 22x32 tile grid `read_cells()`
  gives, plus each screen's cave, shop wares and secret. **98 of 98 screens the bot has walked decode exactly.**
  Full table: `knowledge/overworld_screens.txt`. First-quest shops: candle 0x0C 0x5E 0x66; arrows 0x25 0x44 0x4A
  0x6F; bait 60 at 0x34 (100 at 0x26/0x46/0x4D); hearts 0x2C(bomb) 0x2F(raft) 0x47(burn) 0x7B(bomb) 0x5F(ladder);
  +100 at 0x0F 0x62 0x6B; +30 at 0x13 0x28 0x2D 0x3D 0x48 0x67 0x71; warp caves 0x1D 0x23 0x49 0x79 (bracelet 0x24).
* `zelda/owroute.py` - Dijkstra over Link's 8 px lattice across the whole map with the navigator's own hitbox,
  ladder bridges, the two mazes as the game plays them, raft rides, the hidden road 0x1F->0x0F. Calibrated on the
  third run's 110 crossings: a screen change costs 135 frames sideways, 106 up/down, on top of the walking.
* `route_planner.py` - errands (dungeons, swords, shops, secrets, hearts) in an order, walked by the router with
  the whirlwind (the disassembly's `WhirlwindPrevRoomIdList`: the wind sets Link down on the LEFT EDGE of the
  dungeon's screen at the height he played) and dungeon times from the third run split walk/fight, fights scaled
  by sword. **It reproduces the third run at 41.33 min against the real 41.26.**

## What the planner says
Best order found (5M candidates a seed, four seeds agree to within 0.2 min): **39.2 min, about two minutes off.**
L3 -> heart rock 0x2C (+ money) -> WHITE SWORD at five hearts, before Level 1 -> L1 -> (heart tree 0x47) -> L4 ->
blue candle -> **L8 straight after L4** -> L2 -> L5 -> wind, arrows and bait -> L7 (no red-candle cellar) ->
MAGICAL SWORD (twelve hearts) -> L6 -> L9. The warp caves never pay for the bracelet.

So the order of errands is worth two minutes, not six. The dungeons are 28 of the 41 minutes, and that is where
the rest has to come from.

## And the dungeons
Order of the Ate's Level 4 map: humans go 20 -> 21 -> (bomb north) 11 -> (bomb east) 12 -> Gleeok. The ROM's door
table agrees those walls are bombable. The third run went 20 -> 10 -> 00 -> 01 -> 02 -> 12: three more rooms, a
fight, an old man's 150-frame speech, a locked door and a key - about 1,500 frames - because bombs were scarce
when that route was drawn. Bombs are only scarce if drops are luck.

Next: a dungeon path optimizer over the ROM's door tables with a bomb and key budget; the kill counter from RAM
so the tenth kill is made with a bomb when bombs are wanted; then the new route, probes, and a fourth full run.

## Bombs, first steps (same day)
The drop system is fully in the disassembly (knowledge/wr_route_comparison.md has the tables): `$50` counts kills
in a row since Link was last hit, the tenth is a guaranteed drop - five rupees, or BOMBS if the killing blow was a
bomb's (`$51`) - and `Link_BeHarmed` zeroes it. Dodongo's death sets both to ten: the next kill after Level 2's
boss drops bombs for certain. Ordinary bomb drops only come from "row 2" monsters (blue Octoroks, blue Moblins,
blue Lynels, Vires, red Goriyas, red Darknuts, blue Wizzrobes, Gibdos) on kill-cycle 1, 6 or 8.

A probe through Level 1 watched the counter climb 0-3-8-9 exactly as documented. Making the planner hold the tenth
kill for a bomb is another matter: with fast enemies no bomb rollout ever showed the kill, and the first version
dithered 300 frames waiting for one. It is now bounded (0, 8 or 16 decisions, chosen per attempt) and the SEARCH
decides: every bomb in hand is worth 220 frames in the ranking (`search.BOMB_VALUE`, capped at 8), so of sixty
attempts at a room the one that came out with four more bombs wins unless it cost more than ~900 frames. That
alone changes what the run carries: until now a bomb drop picked up or walked past made no difference to which
attempt was kept.

Level 4's shortcut, glitchless: humans go through room 21's centre; from the island there are TWO squares of
water to the north wall and the ladder spans one, so that is a clip. The honest way is 20 -E-> 21 on the outer
ring, round to the north wall, bomb, 11, bomb east, 12. Probe `l4_ring`: 20->21 in 395 frames, 21->11 in 590-830.
About 1,000 frames saved against 10-00-01-02, for two bombs.
