# 35 — Cutting the grind

2026-09-15

The run is beaten and recorded, and the verdict on it was fair: impressive in places, silly in
others. Three specific complaints, all correct:

- the video never says *why* the bot does anything;
- Link stands motionless for a minute after the Level 4 boss;
- he walks in and out of Level 6 repeatedly, and buys bombs in a shop when monsters drop them.

And a target: beat the game in under an hour. The first run took 1:43.

## Where the time actually went

Before changing anything I counted. 372,090 frames, broken down by what the segment names say they
were doing:

| | |
|---|---|
| dungeon interiors — the actual game | 34.7 min |
| **earning rupees** | **16.4 min** |
| the supply trip for bombs | 4.8 min |
| whirlwind rides | 3.0 min |
| Gleeok | 1.7 min |

A quarter of the run is Link killing the same two rooms over and over for pocket money. That is the
thing to fix, and it is exactly what the complaints were pointing at from the outside.

## The map lies, and this time it cost a plan

A multi-agent audit proposed funding the route from a 100-rupee cave on screen 0x0F. I went to look.
Screen 0x0D's east side is solid mountain — 0x0F cannot be reached on foot at all. The other
100-rupee cave, 0x62, is crossed five times by the route, so I swept every reachable spot on it:
92 places bombed, pushed and burned. Nothing there.

That is the fifth time the community map has been wrong in this project. So I stopped reading and
started opening. Four caves later:

- **0x28** — burn, **+30 rupees**, 1,150 frames.
- **0x67** — bomb, **+30 rupees**. "IT'S A SECRET TO EVERYBODY."
- **0x1A** — push, and it is the *other* kind of old man: "PAY ME AND I'LL TALK", −5, −10, −20.
  A cave that takes money. Worth knowing precisely so the route never walks into it.

Three probes read "+0" on caves that plainly pay, which taught me something about how the game
stores things: Link enters a cave at the bottom, the money sits in the middle, and the item slot
reads empty for an old man's gift. Every probe concluded there was nothing to collect and stood in
the doorway. The fix is to walk north and watch the rupee counter instead of trusting the slot.

## The constraint nobody wrote down

Then the real problem surfaced. Money is not fungible in this route, because the *tool* that opens a
cave arrives at a fixed time. Burn caves need the candle, which is in Level 7. But the 80 rupees for
arrows must be spent before Level 6, because Gohma cannot be killed with anything else.

That is *why* the first run farmed. At that point Link has no candle, and every cave I now know
about needs one — except 0x67, which needs a bomb, and Link is carrying six when he walks across
that very screen on the way to Level 1.

So: the second farm is deleted outright, the first shrinks from nine targets to two small top-ups,
and a cave that costs about 1,100 frames replaces roughly ten minutes of grinding. 609 segments
became 587.

## Gleeok, and a lesson about where to measure

The stalling after the Level 4 boss looked like a stuck death-check. It wasn't. Replaying the
winning inputs into the main emulator clears the room at frame 2,336 — and the search had recorded
6,020. The scout and the main emulator do not always agree: the planner branches through hundreds of
in-memory savestates, and replaying only its chosen moves can win sooner than the live attempt did.

So the fix isn't in the boss code at all. The run now replays each winning attempt into the main
emulator and stops the moment the segment's own success test holds three times running — never while
an item is still on the floor, and never for segments whose last frames are load-bearing. Dead air
gets cut where it is actually measurable, which is the log that becomes the video.

## The overlay

The feature that was asked for is in: every room now carries a heading and a reason, held steady
under the objective line rather than fading. Building it turned up two bugs in the video I had
already sent. The captions were gathered from every checkpoint on disk, including abandoned attempts
— so some named rooms the bot never entered — and each one was keyed to the frame where its segment
*ended*, meaning every caption described the room Link had just left.

587 segments, 47 with hand-written reasoning, none left blank.
