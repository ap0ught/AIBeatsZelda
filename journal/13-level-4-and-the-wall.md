# Phase 13: Level 4, and hitting a wall called Gleeok

**What went right.** Level 4 needed a lot of new machinery and most of it worked first or second
try: riding the raft from a dock (a pier tile sticking into the sea), finding dungeon entrances by
their doorway tiles instead of hard-coded coordinates, crossing a water chasm with the stepladder,
bombing through walls, a second item cellar, and a shortcut the walkthrough does not take. From
power-on to the boss door: eight and a half minutes, no damage taken, replays exactly.

**Three bugs worth keeping for the video.**
- A room full of treasure read as a room full of monsters. The game stores a ten-rupee cache in the
  same object table as enemies, so the bot refused to walk through its own reward. It now tells
  them apart by branching on a savestate, watching whether an object moves, and rewinding, which
  costs the run nothing.
- The invincible Bubbles meant "kill everything in this room" could never be satisfied. Unkillable
  things now do not count.
- The stepladder was treated as letting Link walk on any water. It only bridges gaps exactly one
  tile wide, which is why the bot kept planning routes across a lake.

**The wall.** Gleeok is the first thing this bot cannot beat. Its body and neck cannot be hurt at
all; only the far end of the neck can, and that head is not in the game's object table, so a normal
enemy scan does not see it. Worse, killing the first head does not end the fight: a second head with
six fresh hit points takes its place, which my scoring first read as the boss healing. Sixteen sword
hits, in a small room, against fireballs that cannot be blocked, with four hearts.

I tried five approaches: full search (survives, far too slow), a direct fighter (fast, dies in
seconds), verify-then-act (best of both, still dies), bombs (four bombs is exactly enough damage,
but placing one safely never passed its own safety check), and keeping distance. The best attempt
got the boss two hits from death.

**The diagnosis is not the tactics, it is the equipment.** Every walkthrough arrives at Level 4
with eight or more hearts and the white sword, which does double damage: eight hits instead of
sixteen, and twice the margin for error. This run skipped both because it took the speedrun's
dungeon order. Now that the goal is to finish the game rather than to be fast, the right move is
the one a human would make: go and get the white sword and another heart container first, then
come back. That is the next phase.
