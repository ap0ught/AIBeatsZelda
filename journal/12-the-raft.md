# Phase 12: the raft, properly

**Where it was.** Under the southwest corner of Level 3: a basement reached by the stairs in the
eight-Darknut room, which itself sits behind the five-Darknut gauntlet. The walkthroughs said so
in two sentences. The map convention had sent me to the wrong wing for most of a day.

**How it fell, room by room, all with lookahead.**
- The gauntlet: five Red Darknuts dead, sword only, 1010 frames, three hearts intact.
- The eight-Darknut room: no fight. A dash along the one-lane corridor to the stairs tile,
  which has to be entered with Link's box fully inside it, like a cave door. 314 frames.
- The cellar: a side-view basement with ladders and a floor, four Keese guarding the raft. A
  scripted walk lost a heart and a half to them every time. The same walk driven leg by leg by
  the lookahead planner, which can now swing as well as step, took the raft with no damage in
  800 frames.
- The way back: dash to the top door, then the emptied gauntlet, the key room, the corridor, the
  ring room, the bomb wall, Manhandla in 196 frames, the heart container, the Triforce. Every
  segment at full hearts.

**Bugs worth remembering.** Cellars run in a different game mode than rooms, so every "is Link
playing normally" check refused to work there. Their tile graphics reuse ids that mean walls
upstairs, so the knowledge base needed a third context. Link's vertical grid is offset
differently in a cellar, so the grid phase is now measured on entry instead of assumed. And one
transition wasn't going through the input recorder, so the next segment began in the middle of
a stairs animation. None of these are game knowledge; all of them are the kind of thing a
watching person spots and a bot has to be taught to check.

**Now** the whole thing is being played again from power-on by the main emulator, with the scout
searching each room, so that the verified run includes the raft.
