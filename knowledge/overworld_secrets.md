# Overworld secrets verified by screenshot (2026-09-15)

Found with zelda/secrets.py after fixing its bomb-doorway blindness, then walked into and
photographed (harness/shots/). Grid squares use the top-down convention the ROM's dungeon doors
confirm: room = ((number - 1) << 4) | (letter - 'A').

| What | Screen | Square | How | Shot |
|---|---|---|---|---|
| MAGICAL SWORD (needs 12 heart containers) | 0x21 | B3 | gravestone at tile (row 5, col 9): middle row, 3rd from the left. Stand (144,157) below it, push UP; keep holding Up and Link walks down the stairs | grave_21_found.png |
| Heart container (or red potion) | 0x2C | M3 | BOMB from (176,157) facing Left -> doorway (144,157); walk up into it from (144,173) | problem_5_inside_2c_cave.png |
| Heart container (or red potion) | 0x47 | H5 | BURN from (176,157) facing Down -> staircase at (176,173); walk onto it | cave_47_inside.png |
| Cave, contents not yet photographed | 0x7B | L8 | BOMB from (144,93) facing Up -> doorway (144,77) | secret_7b_bomb.png |

Inside the two heart-container caves the old man says TAKE ANY ONE YOU WANT: red potion on the
LEFT, heart container on the RIGHT. Take the right one - the other choice is gone for good.

The graveyard is tile 0xBC gravestones in a 4x3 grid on screens 0x21, 0x31, 0x40, 0x41 (0x20 and
0x30 are uncached). 0x21 is its top-right screen. From Level 6's door: 22 -Down-> 32 -Left-> 31
-Up-> 21. Touching graveyard stones calls Ghinis.

Still from the guides, unverified: heart containers at P3 = 0x2F (raft island, open cave) and
P6 = 0x5F (lying in the open, needs the stepladder).
