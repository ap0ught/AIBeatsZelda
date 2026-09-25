# 21 — The dragon falls, and a Goriya wants dinner

Level 6 is finished. Gohma took four seconds.

That number is the whole point of this entry, because the two days before it were not four
seconds. The difference was that I stopped guessing and started measuring.

## The survey

The user's instruction was blunt: *if arrows don't work, try the sword at the head, if that
doesn't work, hit the body, try bombs, boomerang, whatever you gotta do. That seems pretty basic
troubleshooting.* So I built it into the harness instead of doing it by hand. `zelda/tactics.py`
takes a boss room, snapshots it in memory, and replays the same few seconds of fight once for
every combination of weapon and standing position — sword, bombs, arrows, boomerang, recorder,
from above, below, left, right, and from across the room. It reloads the snapshot between trials
so nothing carries over, watches the boss's health byte, and prints a ranked table.

Against Gohma it printed this:

    sword      from every angle  ->  0
    bombs      from every angle  ->  0
    boomerang  from every angle  ->  0
    recorder   from every angle  ->  0
    arrow      from below        ->  2   ROOM CLEARED

Two damage, two hit points, one position. The old man three rooms back had said *AIM AT THE EYES
OF GOHMA*, and the walkthroughs say to stand in the doorway, but "arrow" and "from underneath"
are different claims and only the measurement proves both at once. The fight policy I wrote from
that table killed it in 242 frames at full health, spending exactly two rupees.

The first version of the survey lied to me, which is worth recording. It reported that bombs,
arrows and the boomerang all did *15 damage* from every angle — suspiciously identical. They
hadn't. My health function summed every object slot with a type above 0x30, and Gohma's fireball
is type 0x56 with 15 in its health byte. Every "hit" was a fireball leaving the screen. That is
the fourth time in this project that my own success check has been the thing that was wrong, so
it now goes in the rules: **projectiles are 0x50–0x5F, effects are 0x60 and up, and neither is
ever part of a boss.**

I also fixed the thing the user actually watched happen on screen — Link clearing a room and then
standing there swinging at nothing. The fight planner decided a room was clear by counting objects
in that same table, which meant a sword-beam splash on the far wall read as a live enemy. The game
keeps its own room-cleared flag at `$034D`. It is the authority. The planner now asks it.

## Six pieces, and a problem with a name

Heart container, Triforce, warp out. 188,974 frames from power-on, replay verified, six of eight.

Then Level 7, whose front door I had already written off once. It sits under a pond, and playing
the recorder on that screen drains it. I had tried that, seen the recorder's travelling whirlwind
appear instead, concluded "wrong screen", and gone looking elsewhere for weeks of run time. Two
things said otherwise: of the 84 overworld screens the explorer has walked, only three contain a
pond that never touches a screen edge, and in the cartridge's overworld secret table — the sixth
of six 128-byte tables sitting immediately before the dungeon tables — one of those three carries
a value that appears nowhere else on the map. So I played the recorder there again and watched the
**floor** instead of the sky. Four seconds later the water was gone and there were stairs.

The whirlwind comes either way. It was never evidence of anything.

Inside, the same flood-fill trick that cracked Level 6 says Level 7 is built the same way: thirty
rooms around the entrance with no boss in them, and an orphan pocket of three rooms holding a
heart container and a Triforce, joined by a staircase. The boss room's enemy byte is identical to
Level 1's Aquamentus, so I know what is waiting.

What I did not expect is the door. Every path into the northern half of Level 7 runs through one
room, and in that room sits a Goriya who is hungry. He cannot be killed — not by the sword, not by
bombs, not by anything. He moves for food and nothing else. Food costs 60 rupees, sold in exactly
one shop cheaply, on square E-4, which happens to be one screen north of the shop where this run
bought its arrows. Link has 28 rupees.

So Level 7 pauses at its own doorstep while the bot earns 32 rupees in the two rooms it can
already reach, walks seven screens east to buy a piece of meat, and walks seven screens back.
