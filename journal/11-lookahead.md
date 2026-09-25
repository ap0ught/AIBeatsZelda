# Phase 11: thinking one second ahead

**The wall.** The five-Darknut gauntlet ate every tactic I hand-wrote. Chasing one at a time:
dead. Ambush beside a block: dead, without a swing. Bombs rolled into their lanes: two wins in four
hundred tries, both at one heart. Sword with beams: none in two hundred. The person watching said
real players do it with the sword, and he was right about the tactic, but my reaction code was
the problem, not the weapon. A frame trace showed why: the "get out of its way" logic and the
"get behind it" logic disagreed every frame, so Link jittered in place until a Darknut walked
into him.

**The tool.** The emulator can save its whole state to memory in a millisecond. So instead of
reacting, the bot now looks ahead. Every eight frames it takes a snapshot, tries each of nine
moves on the snapshot (walk in four directions, swing in four directions, wait), lets the game
run a few more frames to see what happens, scores the result, and only then plays the best move
for real. Dying scores minus a hundred thousand. Losing half a heart, minus eight hundred. Taking
an enemy's hit point, plus sixty. Standing in front of a Darknut's shield, minus sixty. And a
gentle pull toward the one place a sword hit can happen: beside or behind the nearest enemy, a
sword's length away.

**First try.** With that, the gauntlet fell in 890 frames, sword only, all three hearts intact,
on the first attempt. Two earlier versions had loopholes worth keeping on tape: the first
version walked back out the door and declared the empty room "cleared"; the second was so
careful about distance that it never attacked. Both were scoring mistakes, fixed in minutes.

**What this is.** This is the optimizer's core move, arriving early. Later it will do the same
thing for time instead of survival: try alternatives, keep the fastest, from bookmark to
bookmark, until the whole run is stitched from best-of-many decisions.
