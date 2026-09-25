# 36 — Four ways to break your own run

2026-09-16

The re-run reached Level 4 and stopped there for five hours. Every blocker was mine, not the game's.
Writing them down because each one is a distinct kind of mistake.

## 1. The optimisation that cost a heart per room

I capped the search's health bonus at 90% of Link's containers, reasoning that health he doesn't
need isn't worth frames. Measured saving: about 1,100 frames.

What it actually did: with five containers the cap sits at 4.5, so a 5.0-heart finish and a
4.5-heart finish scored *identically* and the tie broke on speed. Every near-full segment quietly
preferred the faster, weaker line. Across forty segments between the White Sword and Level 4 the
erosion compounded — Link arrived on 2.5 hearts instead of 3.5, was on 1.0 by room 0x40, and then
died sixty times running in 0x32.

Reverted. The audit had flagged that exact change as its highest-risk item, and the code comment
beside it said this tuning had already gone wrong once before. Both were right.

## 2. At one heart, the planner stops playing

The next failure looked unrelated: 34 attempts out of 40 ending "gave up reaching the Left door",
with only three deaths. That is not a combat failure, it's a *refusal* — the damage-aware planner
will not route Link past anything when a single hit kills him. A near-dead Link doesn't lose, he
wedges, and every room after him wedges too.

Two fixes. That room now uses the planner that walks gaps rather than the navigator that declares
rooms impassable. And the search no longer settles for a win that leaves Link nearly dead: when the
best attempt is at or below a third of his containers, it spends the whole try budget looking for a
better one instead of stopping after sixteen.

## 3. The policy that trades damage for frames

Room 0x32 was the root cause of all of it. It used the plain clear-the-room policy, which swings
without weighing what it takes in return. Sixty attempts from 3.5 hearts never produced better than
one heart.

The same room with the damage-aware fighter: **1,657 frames, 4.5 hearts** — faster *and* healthier.
The old finished run took 4,906 frames there and came out on 2.0. Link even gained a heart on the
way through. Two segments later he was back to full, and the rooms that had wedged twice passed
without incident.

## 4. Killing a run badly starts a second one

Then I found four emulators running when a run uses two, and two `fullgame.py` processes alive at
once — both resuming the same checkpoint, both writing the same files, competing for the same CPU.

My doing, twice over. I killed a run by matching command lines containing `run_until.sh`, which also
matched the shells running my own background tasks. And when I killed the Python process without
killing its wrapper, the wrapper did exactly what it was written to do — noticed a silent death and
started a fresh one — while I had just deleted the lock directory that would have stopped it.

Kill the wrapper first, then the process, then the emulators, then clear the lock. In that order.

## The one that wasn't my fault

With all of that fixed, Gleeok still wouldn't die. A diagnostic of six attempts timed out with the
boss on 10, 8, 2, 10, 10 and 10 health — close, never finished. Then I looked at the run I had
already recorded: its four successful attempts landed at 6,019, 6,018, 6,012 and 6,020 frames
against a 6,000-frame budget.

This fight has never been won comfortably. It succeeds by arriving at the last possible moment, and
six attempts finding no success is ordinary luck rather than a regression — which also means the
budget cut I made earlier, on a misreading of the log, had turned a coin flip into an impossibility.

The window is now 10,000 frames. That costs search time, not video: the run trims each winning
attempt back to the frame the room actually clears.

**A rule I should have already had:** when a change makes things worse, revert it before reasoning
about it. I spent an hour theorising about trimming and drops while the real culprit was a
one-line ranking change I had made forty minutes earlier.
