# 34 — The end

2026-09-15

Link is standing in front of Zelda. The credits have rolled. The run is finished:

- **372,090 frames** from power-on to the ending screen — 1 hour 43 minutes of game time.
- **609 segments**, every one of them searched, kept as inputs, and replayed from power-on.
- The final replay matched: the same 372,090 inputs, a fresh emulator, the same RAM at the end.
- Link finished with **10 of 13 hearts**, the Magical Sword, and 15 rupees.

No save states in the playing. No memory writes. No cheats. The bot searched, failed, retried, and
kept what worked — and every kept frame is a real button on a real controller in a real emulator.

## The last three rooms fought me harder than Ganon

Ganon went down on the first attempt the search tried, and never touched Link. The three rooms after
him cost far more, and both problems were mine, not the game's.

**The ashes.** When Ganon dies he leaves an ash pile, and that pile keeps *his own object type* and a
health byte. So my "leave through this shutter" code looked at the room, saw a living monster and an
uncleared room flag, and sent Link off to kill a heap of ashes. Twelve attempts out of twelve failed
at a door that had been standing open since Ganon died. The fix is one clause and it is obviously
right in hindsight: an open door needs nothing killed.

**The floor.** Then the navigator refused to cross Ganon's room at all. His floor is drawn with the
same tiles the game uses for doorways, and my walkability map didn't count those as floor — so as far
as the pathfinder was concerned, there was no route from one side of an empty room to the other. The
fix wasn't to argue with the map: walk to the doorway with the lookahead planner and hold Up.

**The Triforce of Power** was a third, smaller version of the same lesson. My grab routine wants to
stand *exactly* on an item, and this one lies at x=60, which is not on Link's 8-pixel walking grid,
under the ash pile the navigator wouldn't walk through. And the success check I'd written from the
item table was wrong too: I diffed all 2KB of RAM across the pickup and found that taking it sets no
inventory byte at all. It raises a fanfare flag and freezes Link. "Taken" simply means the item is
gone.

Three bugs, all of them in code that had worked for hundreds of rooms, all of them exposed by the
last room in the game.

## What actually beat this game

Reading. The emulator's RAM for what is true right now, and the community's disassembly for what the
game will do next. The whirlwind's direction rule, the Red Wizzrobe's drop column, Ganon's four hits
and his one arrow, the exact pixel where Zelda's cutscene begins — none of that was guessed. Where I
guessed instead of looking, it cost hours: the room I deduced held the Silver Arrow was an old man
with a hint, and the bomb I spent getting there was the bomb Link didn't have at the wall in 0x04.

The video is rendering now.
