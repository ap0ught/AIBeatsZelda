# Phase 1: building the hands, and the first sword

**Goal.** Before an AI can speedrun anything it needs hands and eyes. Hands: a way to press
controller buttons one frame at a time. Eyes: a way to know what is happening in the game.

**How.** I did not build an emulator; I used BizHawk, the emulator the tool-assisted speedrun
community already trusts. I wrote a small script that lives inside BizHawk and listens on a local
network socket. My Python code sends it commands: hold these buttons for this many frames, tell
me the game state, save a bookmark, load a bookmark, take a screenshot.

For eyes I do not look at pixels at all. The game keeps everything that matters in 2 kilobytes of
memory: where Link is, which screen he is on, how many hearts, whether he has the sword. I read
those bytes directly. The addresses came from fan-made memory maps, and several of them were wrong
or mislabelled, which I found out by testing.

**What went wrong.**
- The title screen ignored my Start press. I pressed it a few frames after power-on; the game
  needs about two seconds before it listens. Fix: keep tapping until the screen changes.
- Pressing Select three times to reach "register your name" put me in Elimination mode. With no
  save file the cursor already starts on register, so I overshot.
- A blank name is silently rejected. Nothing on the wikis says so.
- The wiki's table of game modes has two values swapped. My code waited for the wrong number.
- BizHawk remembers the cartridge's battery save between launches. After one successful
  registration every later run skipped the menus, which would have made runs non-reproducible.
  Now the launcher wipes the save before every run.
- The sword. Link stood directly under it for 500 frames and nothing happened. I tried every
  button, every horizontal offset, and long waits. The answer: the item is only collected when
  Link walks up into it from below, passing through one specific row. Standing on the top row
  under it, which looks like touching it, does nothing.

**Result.** Power-on to sword and back outside in 1036 frames. The whole run replays from
power-on byte-for-byte, exports as a standard BizHawk movie, and BizHawk plays that movie to the
same final state. That is the verification standard every later result has to meet.
