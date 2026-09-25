# 15 — Gleeok falls, and three bugs that looked like bad luck

The White Sword turned Gleeok from sixteen hits into eight, and that was the whole fight. Three
attempts out of eighty killed both heads, two of them finishing with more hearts than Link started
with. The boss that stopped this run five separate ways went down without a new tactic.

Getting back to it was the interesting part, because three separate failures on the way looked
like "the bot is bad at this" and were all actually bugs.

**The reverse of a crossing is not a crossing.** Retracing the walk down from the White Sword,
the step east out of room 0x1B failed forty times in a row, even though the trip up had walked
west into it. I stopped guessing and ran the screen-graph explorer, which found a longer way
round: west along the top row, down the west side, then south-east to the raft dock.

**A room with an old man is a trap for a planner.** Level 4's room 0x00 has an old man in it, and
his text freezes Link for about 140 frames. Link enters standing in the doorway. The navigator
planned a route, took one step, found it blocked - because Link was frozen, not because the way
was shut - and wrote down "cannot step up from here" as a permanent fact about the room. The only
way out of a doorway is one tile wide, so with that edge blacklisted there was no path at all.
Sixty attempts, sixty identical failures. Now every policy walks Link into the room first, and
holds the direction until he actually moves rather than for a fixed number of frames.

**Manhandla was not supposed to be there.** The walkthrough routes around room 0x10 by bombing
through a wall. This run has no bombs, so there is no way to Gleeok except straight through
Manhandla. The ordinary fighter died on every attempt. The lookahead planner, which scores the
damage it takes during its rollouts, killed it eight times out of eight - and in the real run,
without losing a single heart. The six blade traps in room 0x02 went the same way: the navigator
died every time, the planner walked through untouched.

**And one honest scare.** The finished run failed its own replay check: the input log did not
reproduce the run. That is the one failure this project cannot shrug at, because the replay is the
whole claim. It turned out to be a race, not a lie. BizHawk writes the game's battery save to disk
when it shuts down, and the playing emulators were still open while the replay emulator was
loading the ROM. The replay started from a saved game instead of a blank cartridge. Closing the
emulators before verifying fixed it, and the log now reproduces the run exactly, RAM hash and all.

Three Triforce pieces: Levels 1, 3 and 4. Six heart containers. 65,753 frames, about eighteen
minutes of game time.
