# Phase 4: the first dungeon, and learning not to fight

**Goal.** Walk into Level 3 and get through it. Dungeons are a different world from the
overworld: rooms instead of screens, doors instead of open edges, and enemies packed tight.

**What broke immediately.**
- The dungeon draws its rooms with a different set of tile graphics, so tile ids the bot had
  learned as "walkable dark ground" outside are solid walls inside. It walked confidently into
  walls until I split its tile knowledge into an overworld book and a dungeon book.
- It found a phantom key in the entrance room. The item-slot memory holds stale values from the
  previous screen; a separate status byte says whether the slot is live. Now it checks that.
- I had the enemy type table off by one byte. Every enemy's type was paired with the next
  enemy's position. Nothing about the overworld had exposed this because it never fought. The
  disassembly of the game's code gave the correct address.
- The first time it swung the sword, nothing happened. Link was standing in the doorway, and the
  game silently disables attacking there. Every human player knows this without knowing it.
- Then it did fight, chased five Zols around the room for eight seconds, never landed a hit, and
  died. Zols hop, and each one splits into two Gels when struck. A room with five of them is a
  terrible first sword fight.

**The lesson that mattered.** The speedrun guide for Level 3 says the first key is taken
"without fighting." The fast play in that room is to dodge, grab, and leave. So instead of a
better fighter, the bot got a better dodger: paths that cost more near enemies, replanned every
two steps as they move, and a rule to hold still for a moment when something is right where the
next step lands. With that, it took the key on the first try in 74 frames without being touched.

The bot can swing the sword now, and I can see the blade extend in memory, but aim and reach are
not calibrated yet. That comes when a door forces a fight.
