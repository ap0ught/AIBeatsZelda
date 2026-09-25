# 25 — The detector that couldn't see

**Where we are:** deep inside Level 9 with all eight Triforce pieces, the White Sword and eleven
heart containers. The Magical Sword — the strongest sword in the game — needs twelve.

## The question
Level 9 has no heart containers, so the twelfth has to come from Hyrule's secret caves. The guides
agree there are five on the overworld. The AI's own secret-finder had already swept two of the
candidate screens and reported *nothing there*.

## The mistake worth watching
Instead of trusting that, the AI pointed the finder at a rock it had *personally blown open* an hour
earlier to get into Level 9. The finder said "nothing opened" there too — 220 bombs' worth.

Three bugs were stacked on top of each other:
1. It only recognised a cave doorway with an arch drawn above it. A bombed rock face leaves a bare
   black doorway with no arch — so every bomb secret on the map was invisible. (The AI had written
   this exact fact down weeks ago, when it opened Level 9's door. It just never told the finder.)
2. It walked to each spot ignoring enemies, so on Lynel-infested screens Link died on the way to
   the one spot that mattered — and that spot was quietly counted "unreachable".
3. When it was taught to clear the screen first, it took its snapshot *after* the fight — so when
   Link died clearing, every later trial started from a corpse.

**Lesson:** test your instrument on a question you already know the answer to before you believe its
"no".

## What the fixed finder found
- **Screen 0x2C** — bomb the giant rock's bottom-right: "TAKE ANY ONE YOU WANT", a heart container.
- **Screen 0x47** — burn a tree: another heart container.
- **Screen 0x7B** — the seashore doorway (contents not yet seen).
- **Screen 0x21** — the graveyard's top-right corner, middle row, third gravestone: pushed up, it slides
  away and Link walks down the stairs to an old man and **the Magical Sword**.

Every one was walked into and photographed before a single line of the real run was written.

## Also figured out: where Ganon lives
Two walkthroughs, the cartridge's door table and an old man's riddle ("EYES OF SKULL HAS THE
SECRET") all point at the same three rooms: a Patra room, Ganon above it, and Zelda above him —
sealed off from the rest of the dungeon, reachable only by one staircase.

## Next
Walk out of Level 9, ride the recorder's whirlwind to three dungeon doors, take two heart
containers and the Magical Sword, then come back for the Silver Arrow and Ganon.
