# 14 — The sword that was worth ten screens of walking

Gleeok beat me five different ways in Level 4. Every time, the arithmetic was the same: two heads,
sixteen wooden-sword hits, and four hearts of margin. I kept rewriting the tactics. The tactics
were not the problem. The sword was.

The White Sword does double damage. It sits in a cave at overworld square K-1, and the old man
will only hand it over once Link carries five heart containers. Level 1 gives the fifth one, along
with the bow and a Triforce piece. So the fix for a boss in Level 4 was to go back and play
Level 1 properly, then walk ten screens north-east.

Level 1 went clean: six keys, six locks, no bombs, no wasted hearts. Then the ten screens, nine of
which were ordinary. The tenth, room 0x0A, has a Blue Lynel on it — the hardest thing on the
overworld map, two hearts a hit — and a Zora spitting from the water.

Two things broke there, and they broke differently.

**The Lynel.** My first instinct was to fight it. That is wrong: Lynels are on the do-not-chase
list now, alongside Zoras and Peahats, because chasing a thing that out-damages you is just a
slower way to die. Instead the approach to the cave mouth runs through the damage-aware planner —
it branches over moves, rolls each one forward, and scores a lost half-heart at eight hundred
points against it. It still dies most of the time. That is fine. The scout runs the screen sixty
times and the run only keeps the attempt that survives.

**The cave.** Getting inside was the easy part, and then the bot stood in the doorway doing
nothing. The routine that walks up to an item in a cave had been written months ago against
exactly one cave — the one where Link gets his first sword — with the item's x hard-coded to 120
and a fixed waypoint at y=189. In the White Sword cave that waypoint is inside the entrance
corridor, so the walk stalled with the sword three tiles away.

The fix is the sort of thing I should have done the first time: read the item's position out of
the object table instead of remembering it. The old man, his two flanking torches, and the item
all live in the same twenty object slots. The torches are type 0x40; the item is the odd one out
on the item row. Find it, line up beneath it at y=173, and walk up through its pickup box.

Twelve frames of holding UP later, RAM $0657 went from 1 to 2.

Gleeok is now five hits and three hits, with five hearts to spend instead of four.
