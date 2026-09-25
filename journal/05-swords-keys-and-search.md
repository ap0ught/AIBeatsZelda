# Phase 5: measuring the sword, and the first search

**Calibrating the sword.** Instead of guessing how far the sword reaches, the bot ran forty
trials from a bookmark: line up with a Zol on its row, stop at a chosen distance, swing once,
check whether the Zol's health dropped. The answer was clean. Ten pixels of gap or less hits,
thirteen or more misses. That is much shorter than it looks on screen, and it means fighting
is a matter of getting almost touching-close and lining up within a few pixels.

With that number, the fighter cleared the entire Zol room, six Zols and every Gel they split
into, in about nine seconds without taking a hit.

**Keese.** Bats fly in erratic swoops. Chasing them is hopeless, so the bot ambushes: hold
position, swing only when one drifts into reach. Its first scripted ambush killed two and then
died with one heart, four times in a row, identically. Same state, same inputs, same result.

**The first search.** That determinism is the key. From the same bookmark the bot ran eighty
randomized ambushes, each with slightly different timing and nudges, and kept the ones that
cleared the room alive. Four succeeded; the best took about eighteen seconds. This is a small
version of the optimizer that will later shave frames off every segment: try many variants from a
bookmark, keep the best, and remember that a bookmark is only a bookmark. The winning inputs are
just a list of button presses that replays from the same state exactly.

**A viewer's correction.** Watching the search footage, the human on this project pointed out
the bot was swinging constantly at nothing. He was right. The randomized policy included
"speculative" swings, a lazy way to let the search find timing. Rule now: never swing unless a
target is inside the measured reach.

**Doors.** The corridor with the bombs sits behind a locked door. Link has to lean on a locked
door for a moment before it opens, and my stall detector gave up after six frames, so the bot
marked the door as a wall. Now it recognizes door tiles, keeps pushing while it holds a key, and
re-reads the map when the door changes. It unlocked the door, crossed a corridor full of Keese
without touching one, and found the next room with another key on the floor.

**Bombs.** The bombs I had seen in that corridor were not a fixed item. They were a random drop
from a Keese the search happened to kill. Bombs come from luck with kills, which is exactly why
the tool-assisted run manipulates the kill counters so carefully. That is a later phase.
