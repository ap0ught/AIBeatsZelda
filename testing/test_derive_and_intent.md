# `test_derive_and_intent.py`

Two places where nothing is real: the head's phase, and the panel's captions.

`zelda/head.py` opens by saying what is *not* in the ROM: no head item, no carry animation, no code
path anywhere in Z_01 or Z_04 that would know what to do with one. So the head is harness state, and
the phase is not a flag that gets set and cleared - it is **derived** from where the run is in its
own segment list. `sync(done)` is a pure function of `done` and nothing else, and the docstring at
`head.py:69-74` argues why in terms of a bug this project keeps running into:

    a scout attempt that half-succeeded, or a checkpoint written before the commit, leaves the flag
    set for a Link who is not carrying anything, and then a note says it. `done` only grows when a
    segment has been played into MAIN and verified there, and it is restored from the checkpoint's
    own segment list on resume, so it is the one piece of run state that has never yet lied.

`zelda/intent.py` is the same kind of thing with a different failure mode: the video's panel says
what the bot is trying to do, and the owner's note after the first run was that they wanted the
*why*. 244 of the run's segments fell through to exactly the raw segment name before `for_segment`
got its four ordered fallbacks. So the fallbacks are a ladder and the ORDER is the behaviour - a name
that matches three of the rules must come out of the top one.

Eleven checks, each printing the number or the string it established:

  1. sync() is a pure function of `done`      6. `left_test` and `delivered_test` cannot both hold
  2. ...including BACKWARDS, which is the point   7. both read RAM only - no flag is consulted,
  3. `done` order does not matter, so a           and none is needed
     resumed run cannot disagree with a       8. for_segment's four fallbacks, IN ORDER: caption,
     fresh one                                 INTENT, narration, suffix, room, family
  4. it never returns the raw segment name    9. ...and an unknown name still gets a caption
  5. the delivery spot is remembered, and 0   10. _N's six spellings, and where they stop
     counts                                   11. facts_from reads the game, and `fill` swallows

WHAT IT DOES NOT CLAIM.

* **`_SPOT` is not recoverable across processes, and that limits the "delivered at x=120" claim.**
  `_SPOT[0]` is a module-level list filled by `remember_spot` when the White Sword is taken
  (`head.py:16-18, 59-62`). A fresh process starts at `None`, and both `delivered_test` and
  `deliver_policy` then fall back to a hardcoded **120**. So the archived run's "delivered at
  pos=(120,141)" line is two copies of one number agreeing, not two independent measurements - and
  a run whose sword pickup was never recorded would deliver to 120 and *also* report x=120, which
  looks identical. That is a limitation to state, not a bug to fix here, and check 5 pins the
  fallback's shape rather than pretending it is a measurement.

* **`floor_spot`, `take_policy`, `deliver_policy` and `leave_policy` are not tested at all.** They
  need a `Screen`, a `TileKB` and a live emulator - `floor_spot` reads the room's tiles to find the
  nearest walkable lattice point to (124, 141), and the whole reason it is cached per (level, room)
  is that it costs a TileKB plus a 960-byte bus read per call. `deliver_policy` drives
  `plan_reach`, which is a Lattice machine. None of that is emulator-free, and pretending otherwise
  would mean testing a copy of the function rather than the function.

* **`sync` is not tested against `runner.Run`.** The claim "`done` has never yet lied" is a claim
  about `runner.Run.segment` and `resume`, which need the filesystem and a checkpoint. What is
  checkable here is the consequence: if `sync` is a pure function of a list, then no sequence of
  crashed attempts, stale checkpoints or half-succeeded segments can leave the phase wrong, whatever
  `done` contains. Check 2 walks the ladder backwards to make that concrete.

* **The captions are not checked for being TRUE, only for being reachable and formatted.** No room
  is entered here. What is checked is that a segment name never comes back as itself, that the
  fallback order is the order the docstring claims, and that the six `_N` spellings work.

* **`fill`'s `except (ValueError, IndexError, KeyError)` swallows into an unformatted caption, and
  that is stated rather than tested around.** `intent.py:288-289` returns `text` unchanged when the
  format blows up, so a caption with a stray `{` or an out-of-range index silently shows the braces
  to a viewer instead of raising. Check 11 pins that swallow because *hiding* it would be worse than
  naming it - but a test that treats "no exception" as success for a broken caption would be
  endorsing a bug. Read the message: `{unclosed` in, `{unclosed` out.

* **`_WORDS` has 17 entries and stops there.** `{x:w}` on 17 prints `17`, not `seventeen`. Which is
  a fact about the word list, not a design decision: a caption that ever wanted seventeen heart
  containers would get a number, and that is the intended fallback rather than an IndexError.

Run:  python3 testing/test_derive_and_intent.py

---

    python3 testing/test_derive_and_intent.py          # any cwd; the bootstrap chdirs to the repo root

## What it touches

- nothing at runtime; it exists to be read, or to be applied once

---

*Generated by `testing/make_doc.py` from the script's own docstring and code. Regenerate with `python3 testing/make_doc.py`; do not hand-edit - `git log` on this file says when.*
