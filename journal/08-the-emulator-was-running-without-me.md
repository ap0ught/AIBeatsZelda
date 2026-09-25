# Phase 8: the emulator was running without me

**The symptom.** The first full Level 3 run from power-on kept "desyncing": the scout emulator
would find a clean crossing of a screen, the main emulator would play exactly those inputs from
exactly that saved state, and come out with a hit and a half of damage and in the middle of a
scroll. Same state, same inputs, different result. That should be impossible in a deterministic
emulator, and the deterministic emulator was the one thing I had been trusting completely.

**Chasing it.** I tested replay directly: the same inputs from the same bookmark, twice in one
instance, in a second instance, and in a recording instance. Every hash matched. So the emulator
was innocent. Then I counted frames. Python had stepped the main run 1690 times, but the game
was at frame 1987. Three hundred frames had happened that nobody asked for.

**The cause.** My bridge script inside BizHawk waited for commands by yielding back to the
emulator every 50 milliseconds. While it yielded, the emulator kept running the game. Whenever
Python was busy for more than a moment, which is exactly what happens while the scout searches
a room for a minute, Link stood in the overworld with no buttons held and the enemies kept
moving around him. The milestones before this one only verified because Python never paused.

**The fix** is a one-liner: block for the next command instead of yielding. The emulator window
looks frozen while idle, and nothing advances unless a command says so. Six seconds of idle: zero
frames. The rule this leaves behind is written into the harness: every frame of the run must be
one the script explicitly asked for.
