# 17 — Level 5, and four checks that lied to me

Five Triforce pieces now, eight hearts, and the recorder. Level 5 took longer than the four
dungeons before it put together, and almost none of that was the game being hard.

**The overworld said no.** Level 6 was meant to be next. It sits at the top-left of the map and
the entire north-west quadrant turned out to be sealed: every screen along that frontier is solid
mountain, which I confirmed by reading tile maps rather than trusting the planner's "no path". The
two underground passages that reach it are hidden behind a bomb or a candle the run does not have.
So I reordered. Level 5 was reachable and holds the recorder, which is what opens Level 7.

**The Lost Hills.** A maze screen that loops you back on yourself. I probed it, watched three
norths break out, and wired in three norths. It failed. The truth is four: the savestate I had
measured from had already walked one north before I loaded it, so my measurement was confidently
off by one. Measuring from a state whose history you have not checked is not measuring.

**The recorder is not a floor item.** I scanned the cartridge's item table for it, picked the
likeliest id, sent the bot to that room, and watched it pick up five rupees. The room table is
shared across six dungeons, so scanning it for "which room has the recorder" was never going to
work. The real answer, from a guide and then confirmed in game: bomb west twice, clear a room of
Blue Darknuts, push a block, take a staircase - which turns out to be a passage, not an item room -
unlock a door, clear six more Blue Darknuts, push another block, and descend again.

**And then three checks of my own that threw away real progress.**

The passage walker always crossed to the same corridor. Fine going in; coming back, Link entered
by that very corridor and climbed straight out where he started.

Coming back through, rooms had repopulated. Room 66 was empty on the way out and had three Blue
Darknuts and a closed shutter on the way back. The plain fighter failed every attempt and cost
four hearts each time; the lookahead planner cleared it four times out of four untouched.

Worst of the three: Digdogger. The fight was being won every single attempt - recorder, split,
sword - and my success check counted the projectiles still in flight after its death as living
enemies. Three wins in a row discarded because of a line I wrote.

There is a pattern here worth saying out loud. Every one of these bugs made the bot look worse at
playing than it was. It is much easier to believe "the fight is hard" than to suspect the thing
doing the judging.

Level 7 is next, behind a pond that only drains when the recorder is played.
