# Level 1 and the White Sword (the fix for Gleeok)

Why: Gleeok needs 16 wooden-sword hits and Link had 4 hearts. The White Sword does double damage
(8 hits) and Aquamentus hands over the 5th heart container that the White Sword requires. Every
walkthrough arrives at Level 4 with both. Sources: TheRewster's guide, Mariner's speed FAQ.

## Level 1 (Eagle), entrance at overworld room 0x37 (square H-4)
Rooms decoded from the ROM (zelda/romdata.py); the walkthrough's prose matches exactly.

| Room | N | S | W | E | Item |
|---|---|---|---|---|---|
| 73 ENTRANCE | locked | open | open | open | - |
| 72 | wall | wall | wall | open | KEY #1 when all Keese die |
| 74 | wall | wall | open | wall | KEY #2 carried by a Stalfos |
| 63 | open | locked | wall | wall | Stalfos |
| 53 | bombable | open | open | open | KEY #3 after clearing |
| 43 | open | bombable | open | locked | map |
| 33 | locked | open | wall | wall | KEY #4 |
| 23 | wall | locked | locked | wall | KEY #5 after clearing (Goriyas) |
| 22 | wall | wall | wall | locked | blade traps; push a block -> stairs -> cellar 7F = **BOW** |
| 54 | bombable | wall | open | wall | compass (Keese) |
| 44 | wall | bombable | locked | open | **BOOMERANG** after clearing (Goriyas) |
| 45 | locked | wall | open | wall | KEY #6 (Wallmasters: they teleport Link to the entrance) |
| 35 | wall | locked | wall | shutter | **AQUAMENTUS**, then heart container |
| 36 | wall | wall | open | wall | **TRIFORCE #1** |

ROUTE: 73 -> W 72 (clear, key) -> E 73 -> E 74 (kill the Stalfos with the key) -> W 73 ->
unlock N 63 -> N 53 (clear, key) -> bomb N 43 (map) -> N 33 (key) -> unlock N 23 (clear, key) ->
unlock W 22 (dodge traps, push the block, stairs) -> cellar 7F BOW -> back 22 -> 23 -> S 33 ->
S 43 -> S 53 -> E 54 (compass) -> bomb N 44 (clear -> boomerang) -> E 45 (kill Wallmasters, key)
-> unlock N 35 AQUAMENTUS -> heart container -> E 36 TRIFORCE.

BOMBLESS VARIANT (what this run uses; it arrived at Level 1 with no bombs): both bombed walls have
a locked-door alternative, so the whole dungeon can be done on keys alone.
  53 -> W 52 -> unlock N 42 -> E 43 (map) -> N 33 -> unlock N 23 -> unlock W 22 -> BOW cellar ->
  back to 43 -> unlock E 44 (boomerang) -> E 45 -> unlock N 35 Aquamentus -> E 36 Triforce.
Keys: 6 collected (72, 74, 53, 33, 23, 45), 6 locks used (73N, 52N, 33N, 23W, 43E, 45N). Exact.
Aquamentus: 6 wooden-sword hits; at full hearts just stand back and throw sword beams at it.
Wallmasters must die first in room 45 or they drag Link back to the entrance.

## White Sword: overworld room 0x0A (square K-1)
A cave at the top of the screen, guarded by a Blue Lynel (the strongest overworld enemy; avoid it)
and a Zora. Link can only take the sword with **5 heart containers**, which he has after
Aquamentus. Double damage, and the full-health beam doubles too.

## Then Level 4
With the White Sword, Gleeok's two heads are 5 + 3 hits instead of 10 + 6, and Link has 5 hearts.

## Taking the White Sword (mechanics the bot learned the hard way)
- Room 0x0A's cave mouth is at (32, 77); Link arrives from the south-east at (208, 221), so the
  whole screen has to be crossed past the Blue Lynel. Do not fight it: two hearts a hit.
- The approach runs on the damage-aware planner, which stalls at a safe distance if the Lynel
  camps. plan_reach now gets impatient: the enemy-proximity penalty decays and the pull toward the
  goal grows as the attempt burns frames.
- The planner stops within a few pixels of the mouth. A cave only swallows Link when he is on its
  x exactly, so square up on ex before holding UP.
- Entering is three stages: mode flips to 0x0B while Link is still outside, then the room swaps in
  (Link appears on the bottom row, y > 190), then submode drops to 0. Reading the object slots
  before that returns the overworld's enemies.
- Link takes a scripted step or two inside, then freezes for the old man's text. "Did he move?" is
  not a good enough test - hold UP until he is actually above y=200.
- Item position: the old man's two torches are object type 0x40; the item is the other object on
  the item row (y 112..136). Line up at y=173, walk to that x, then walk UP through y~157.
