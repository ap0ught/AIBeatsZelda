# 19 — Eighty rupees

Level 6's boss is a giant eye called Gohma. The sword does nothing to it. The only thing that
hurts it is an arrow, fired while its eye is open.

Link has carried a bow since Level 1. He has never had a single arrow, because in this game the
bow and the arrows are two separate items, and the arrows are not found in a dungeon at all: they
are sold in a shop for eighty rupees. Link had twenty-seven.

So the run went shopping, and the trip took longer than some whole dungeons.

**Trapped first.** Before I understood any of this, the bot walked into Gohma's chamber. Both its
doors are shutters that stay shut while the boss lives. Link could not hurt it and could not
leave. The fix was to roll the run back to the checkpoint before he stepped in - which is exactly
what the checkpoints are for, and cost only the frames spent in that room.

**Then the money.** Enemy drops come in ones and fives. My first farming loop asked for the whole
fifty-seven rupees in a single attempt, so every attempt failed and nothing accumulated; the run
sat there for half an hour earning nothing. Asking for five at a time worked. The loop itself had
to be rebuilt twice: a dungeon room only refills when Link re-enters the DUNGEON, not when he
steps back into the room, so the cycle is in, clear, take the drop, out, repeat.

**And a real scare in the middle.** The farming routine played some of Link's moves without
writing them to the input log. The run replayed the log, did something else entirely, and Link
died. The harness caught it by comparing the real run against the scout - that check is the whole
reason the project can claim anything - and the fix was to make sure every frame Link actually
plays is recorded. Verified by replaying a farming run and landing on the identical room, health
and rupee count.

**The whirlwind.** Walking back east was impossible: the screens around Level 6 are Lynels and
Peahats and Link died scouting them. But playing the recorder OUTSIDE does not drain anything - it
summons a whirlwind that carries Link to a dungeon entrance. It crossed the entire map in 455
frames. Riding it repeatedly mapped the cycle: Levels 4, 5, 1, 2, 3, and round again. Level 6 is
not on it, and the reason is neat - the whirlwind only visits dungeons you have FINISHED.

**The shop.** Three wares, three prices. I sent Link into the positions under the price labels
and he bought the wrong thing for twenty rupees, leaving him unable to afford the arrows. The
wares are not where their labels are. Sweeping the counter one column at a time found the two
that actually respond, and the arrows are at x=152.

Eighty rupees, spent. Now Gohma.
