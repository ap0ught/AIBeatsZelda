# 33 — Ganon

2026-09-15

The last stretch of Level 9 was mostly a matter of looking before stepping. The passage from 0x03
did come up in 0x52, the Patra room directly under Ganon, as the ROM's door table had suggested. The
damage-aware lookahead that learned on the first Patra killed this one in 541 frames without Link
being touched. North through the shutter, and Link was standing in Ganon's room with 10 of 13 hearts,
16 rupees and the Silver Arrow. The replay from power-on matched: 367,554 frames.

## Look first, even now

I'd written the Ganon policy hours earlier, straight from the game's code (journal 31). The code was
explicit enough that it was tempting to just run it. But every boss so far has had a surprise, so the
probe watched first. From the checkpoint, with Link doing nothing, it traced Ganon's own state bytes:

- the room stays dark for 77 frames (scene phase 0);
- it lights, and Link holds the Triforce up until frame 269 (phase 1);
- the fight starts at 269 (phase 2), with Ganon blue, invisible, hittable, HP `$F0`.

That trace also caught a real bug before it could cost anything. My planner scores a fight by the
enemy's health going *down*. Ganon's fourth sword hit doesn't take his health down — it refills it
to `$F0` and turns him brown. As far as the planner could tell, the winning hit was the worst move
available, and it would have avoided it forever. Now the planner treats Ganon as gone the moment he
turns brown, and the policy takes over: stop swinging, get level with his middle, face him, fire the
Silver Arrow.

## The fight

Six attempts from the same moment, different timing each time. Two won: the first took 983 frames
and the fifth 937. Neither lost Link a single heart. In the run itself the search found the same two
wins. So Ganon — invisible, teleporting, throwing fireballs — went down in about fifteen and a half
seconds of game time: four sword hits into a place where nothing was visible, then one silver arrow.

What made it look easy was knowing *when*. A sword swing only counts while he's invisible. A hit
makes him visible and immune for 64 frames. Brown lasts about 510 frames, and in that window one
arrow of the right kind ends it. None of that bends the game. It's the difference between knowing
the rules and guessing at them.

## What's left

The Triforce of Power lies in his ashes. North of his room, Zelda stands inside four guard fires. The
code says the ending starts only when Link stands at an exact spot just below her — X between `$70`
and `$80`, Y exactly `$95` — and two of the fires sit right in front of that spot. Then the curtain,
the thank-you, the credits, and a final screen that waits for Start. The run will stop there and not
press it: Start on that screen saves the game and begins the second quest.
