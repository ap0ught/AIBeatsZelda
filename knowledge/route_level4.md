# Level 4 route, walkthrough cross-checked against the ROM room tables

Room ids are the ROM's (row = high nybble, col = low nybble). Door types from zelda/romdata.py.
Level 4's header lists exactly one cellar: room 60, which the ROM item table says holds the LADDER.
Dark rooms do not matter to the bot: it reads the tile map from memory, not the screen.

| Room | N | S | W | E | Item / note |
|---|---|---|---|---|---|
| 71 ENTRANCE | open | open | open | wall | - |
| 70 | wall | wall | wall | open | KEY #1, appears when all Keese die (special 7) |
| 61 | open | open | wall | locked | three Vires |
| 62 | wall | wall | locked | wall | compass (skip) |
| 51 | wall | open | open | wall | KEY #2 |
| 50 | open | wall | wall | open | dark, Vires |
| 40 | open | open | wall | wall | KEY #3, Zols |
| 30 | locked | open | wall | locked | Vires + Bubbles; north blocked by water until the ladder |
| 31 | locked | wall | locked | shutter | Vires on walkways; killing all opens the east shutter |
| 32 | wall | wall | open | wall | Bubbles, Zols, LIKE LIKES; clear, then push the block -> stairs |
| 60 CELLAR | - | - | - | - | **STEPLADDER** |
| 20 | open | locked | wall | open | Vires; safe to stand on water with the ladder |
| 21 | bombable | locked | open | wall | map, dark, Gels |
| 11 | bombable | bombable | bombable | bombable | 10 rupees; west is Manhandla, skip |
| 01 | wall | bombable | locked | open | KEY #4, Keese, needs the ladder |
| 02 | wall | open | open | wall | dark, blade traps |
| 12 | open | wall | bombable | shutter | five Vires; move the WEST block to open the east door |
| 13 | shutter | wall | shutter | wall | **GLEEOK**, then heart container |
| 03 | wall | open | wall | wall | **TRIFORCE** |

ROUTE: 71 -> W 70 (kill Keese, key #1) -> back 71 -> N 61 (kill 3 Vires) -> N 51 (key #2) ->
W 50 -> N 40 (kill Zols, key #3) -> N 30 -> unlock E 31 (kill all Vires -> shutter) -> E 32
(clear all but the Bubbles, push the block) -> stairs -> cellar 60 LADDER -> back 32 -> W 31 ->
W 30 -> unlock N 20 -> E 21 (map) -> bomb N 11 -> bomb N 01 (key #4) -> E 02 -> S 12 (kill 5
Vires, push the WEST block) -> E 13 GLEEOK -> N 03 TRIFORCE.

Keys: 4 collected, 2 spent (30 east, 30 north). Bombs: 2 needed (21->11, 11->01).

## Enemies new in this level
- **Vire** (type 0x12): hops; splits into two red Keese when killed with the wooden/white sword, so
  it never drops items. Kill it near a wall/block so the Keese appear together and one swing takes
  both (Mariner).
- **Like Like** (type 0x17): slow tube; if it swallows Link it eats the magic shield (we have none,
  so the cost is only time and damage). Kill with beams/arrows from range, never walk into one.
- **Bubble** (types 0x2B-0x2D): invincible, disables the sword on contact. Always avoid; they do
  not count for "kill all" shutters.
- **Gleeok** (2 heads here): each head breathes unblockable fireballs. Four sword hits per head
  (Mariner) / ten then six (Red Candle). A destroyed head detaches and flies around invulnerable,
  still shooting, so spread hits between heads and keep moving.

## Reaching Level 4 on the overworld
The raft dock is at map square F-6 = room 0x55; stepping onto the dock auto-sails Link north to the
island F-5 = room 0x45, which holds the dungeon entrance. Level 3's entrance is E-8 = room 0x74,
which confirms the square->room id mapping (column letter A..P = low nybble, row 1..8 = high nybble).

## Bombless variant (what this run uses)
The run reaches Level 4 with no bombs, and the walkthrough's path needs two (21->11, 11->01).
The ROM door table gives a way round that needs none:

  30 --lock N--> 20 --open N--> 10 (shutter: clear) --N--> 00 (shutter: clear)
     --lock E--> 01 --open E--> 02 --open S--> 12 (shutter: clear) --E--> 13 GLEEOK --N--> 03

Keys: three collected (70, 51, 40), three locks used (30 east for the ladder cellar, 30 north,
00 east). Exact, with nothing spare. Rooms 20 and 30 have water, so the stepladder has to come
first, which the 30-east lock pays for.
