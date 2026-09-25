# 30 — The Silver Arrow

**Where we are:** Level 9, holding the Magical Sword and the Silver Arrow — the only weapon in the game
that can finish Ganon. Replayed from power-on in a fresh emulator, all 360,119 frames match.

## The Patra
Guarding the way was a Patra: a big eye with eight smaller eyes orbiting it, swinging out wide and
snapping back in. Before touching it, the AI tried every weapon from every angle on saved copies:

- **Only the sword hurts it.** Bombs, arrows, the boomerang and the recorder did nothing at all.
- **Standing still and swinging gets Link killed** — the ring of eyes sweeps straight through him.

So it let the look-ahead planner fight: try every move a few frames into the future, keep the one
that hurts the Patra without getting hit. It won in seven seconds without taking a single hit.

## The hidden pocket
Under the Patra's left block, a staircase led somewhere the AI's map of the dungeon said couldn't
exist: a two-room pocket in the top-left corner with no doors to anywhere else. The walkthroughs call
it "the upper left corner." The AI's door map had listed those two rooms weeks ago — it just never
connected them to anything. One bomb up through the wall, a room full of Wizzrobes, a pushed block,
and stairs down.

## The cellar that lied
At the bottom, the Silver Arrow sat on a ledge. The AI's cellar routine had fetched the raft, the
ladder, the candle and the recorder without trouble. This time it failed forty times, three ways at once:

1. It decided "item taken" by checking a flag became 1. Link already *had* wooden arrows — the flag
   was already 1. So it thought it had the Silver Arrow before walking over to it.
2. At the foot of the ladder, the look-ahead kept stepping sideways instead of climbing.
3. It only knew how to wait for the climb out of *Level 3's* cellar.

All three fixed, and tested on the real cellar before the real run used them: the arrow is taken,
Link climbs out, and the run moves on.

## Next
Back through the pocket, north through three rooms, a staircase hidden under a blade trap — and then
the last Patra, standing right below Ganon.
