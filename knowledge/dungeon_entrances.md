# Overworld locations of all nine dungeons (first quest)

Grid squares from the community maps count rows from the BOTTOM, our room ids count from the top,
so square (letter L, number N) is room id `((8 - N) << 4) | (L - 'A')`. Verified against the three
entrances this run has already used: Level 1 H5 = 0x37, Level 3 E1 = 0x74, Level 4 F4 = 0x45.

| Level | Square | Room | How to get in |
|---|---|---|---|
| 1 Eagle | H5 | 0x37 | walk in |
| 2 Moon | M5 | 0x3C | kill the middle Armos of the top row; the entrance is under it |
| 3 Manji | E1 | 0x74 | walk in |
| 4 Snake | F4 | 0x45 | raft from the dock at 0x55 |
| 5 Lizard | L8 | 0x0B | through the Lost Hills |
| 6 Dragon | C6 | 0x22 | walk in |
| 7 Demon | C4 | 0x42 | play the WHISTLE to drain the pond |
| 8 Lion | N2 | 0x6D | burn the lone bush with the CANDLE |
| 9 Death Mountain | F8 | 0x05 | bomb the right-hand rock |

Consequences for the route: Level 7 needs the whistle (Level 5's item), Level 8 needs a candle,
Level 9 needs bombs and the silver arrows (Level 9's own item) to finish Ganon.

Sources: honestgamers overworld guide, thonky overworld maps, Hyrule Archive.

## Finding the whistle pond (2026-09-14)

Playing the recorder at 0x42 once looked like a failure - a whirlwind came - so the run went
looking elsewhere and found nothing. Two independent checks now say 0x42 is right after all:

1. **Cached tile maps.** Of the 84 overworld screens the explorer has walked, exactly three
   contain a pond that never touches a screen edge, and all three are the same 82-tile shape:
   rooms 0x39, 0x42 and 0x43.
2. **The cartridge.** The overworld's six 128-byte tables sit at file offset 0x18410, immediately
   before the dungeon tables at 0x18710. The sixth of them (0x18690) is the screen-secret table:
   value 0x03 appears at exactly the twelve screens with an open staircase, including all six
   walk-in dungeon doors (0x22, 0x37, 0x74, 0x45, 0x0B, 0x3C). Level 9's bombable rock at 0x05 is
   0x45 and Level 8's burnable bush at 0x6D is 0x49 - both with bit 6 set, i.e. hidden.
   **Room 0x42 holds value 0x01, which appears nowhere else on the map.** A one-of-a-kind secret
   on one of the three pond screens is the whistle pond.

So the plan for Level 7 is: stand on 0x42, play the recorder, and look for staircase tiles
(0x70-0x73) rather than for the absence of a whirlwind.

### Walking route from Level 6's door to the pond
Taking a Triforce warps Link out to the dungeon's own entrance screen, so Level 7 starts at 0x22.
The explorer's cached screen graph gives a clean way down the west side:

    22 -Down-> 32 -Left-> 31 -Down-> 41 -Left-> 40 -Down-> 50 -Down-> 60 -Right-> 61
       -Right-> 62 -Up-> 52 -Up-> 42

The last two hops are the only ones that matter: 0x42 is a dead-end pocket whose single cached
exit is south to 0x52, so the pond must be entered from below. (0x32 -Down-> 0x42 and
0x41 -Right-> 0x42 both fail - mountain.) 0x61 is the Lost Woods, which the run already knows how
to cross.
