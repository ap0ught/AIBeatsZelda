# `test_value_of.py`

The ranking function, the two prices it reads, and the predicates that feed them.

`search.value_of` (`search.py:281-291`) is what a segment's whole patience search optimises. Two
numbers in it decide the run's frame count: `HEART_VALUE = 1800` frames for the first four hearts,
and the `(cliff - h) * 4000` penalty below `cliff = min(4.0, max(1.5, 0.5 * containers))`. The
comment above `HEART_VALUE` records what 600 was worth: the White Sword screen (0x0A) has a Blue
Lynel on it, the sword beam only fires at `hearts >= containers`, route 5 arrived at 3.5/5 and
found no winning line in 40 attempts, and the same approach from 4.5/5 succeeds about one time in
sixty. The single heart that made the difference was sold by `c0f_0f`, a plain walk across the
overworld, to save at most 600 frames. So these are not round numbers and they are not arbitrary.

Three of the things below are findings about the *test suite*, not about the code, and they are
stated here because a test file that hides them is worse than no test file:

  * **`search.CONVERGE[0]` is set to `False` by `testing/test_search_machinery.py:51` and no test
    anywhere re-enables it.** `search.py:615-651` - the convergence stop *and* the `HEART_FLOOR`
    suppression that is meant to stop it - is therefore entirely untested. That suppression exists
    because convergence "counts FRAMES and nothing else, on purpose", and on 2026-10-02 it banked
    `ow1_38` at 3.0 hearts on the fourth attempt after three scouts independently produced 208,
    217 and 227 frame lines. Five half-hearts later the run stood on the White Sword's screen with
    1.5 of 5. Nothing here fixes that - it is the other file's global, and editing that file is
    not this file's business - but it is the largest untested mechanism in the search and it should
    be the next one.
  * **`testing/test_search_machinery.py:127`'s `attempts0 == 30` is load-bearing on arithmetic
    nothing tests.** That assertion is about how many attempts a `patience=14`, `accept_after=0`
    search spends, which is decided by the tiering at `search.py:688-703` (unhurt -> `patience`;
    nearly dead -> `tries`; in between -> `patience * 2`; plus two long-room widenings). The
    assertion would pass identically if that arithmetic were wrong, because nothing in the file
    checks *which* limit applied - only that 30 attempts ran. This file checks the ranking those
    attempts are ranked by, and deliberately does not duplicate the count.
  * **Four seeds cannot rank 2/4 against 3/4.** `journal/49` says so about the shield-aware A/B and
    it is the reason nobody has re-run it. The same honesty applies here: these checks fix what
    `value_of` computes for a given pair of attempts, which is a claim about the function, and say
    nothing about whether any search found anything.

Ten checks, each printing the number or the boundary it established:

  1. the marginal price of a heart, heart by heart     6. `caution` at all five of its boundaries
  2. the cliff, and its exact size at 8 containers     7. ...including the one that cost a run
  3. the cliff is a RATE change, not a step           8. `must_kill` is three conjuncts
  4. bombs are worth 220 each, capped at 8            9. `Goal` is a square, inclusive, tol 8
  5. frames are worth exactly 1 frame each           10. `goal_distance`'s two branches are NOT
                                                            on the same scale, and that is pinned

WHAT IT DOES NOT CLAIM.

* **No attempt is run and no search is driven.** `Attempt` here is a dataclass with `frames`,
  `hearts`, `bombs` and `bonus` filled in by hand; `value_of` is a pure function of those and one
  container count. So this proves the RANKING, which is the part that can be got wrong silently -
  and it says nothing about whether a real attempt's `hearts` is right, which is `State.parse`'s
  claim (see `testing/test_state_parse.py`) and the cartridge's on top of that.

* **The constants are pinned, not justified.** `1800`, `900`, `360`, `220`, `8` and `4000` are
  checked against the arithmetic they produce and against each other (a heart must be worth more
  than `CONVERGE_TOL = 20`, a bomb more than a frame, the cliff more than the heart value). That
  they are the *right* numbers is a measurement against rooms with knights on them, and the numbers
  are pinned here so that a retune is a visible edit rather than a drift.

* **The cliff is continuous, and the word "cliff" is doing work.** There is no discontinuity in
  `value_of`: at exactly the cliff the penalty is zero, and one tenth of a heart below it costs 400
  frames. What "cliff" means is that the *slope* goes from 1,800 frames a heart to 5,800 - so the
  ranking will take a longer line to keep a heart rather than gamble below the floor. Check 3 pins
  that reading, and it is the honest one; a test asserting a step discontinuity would be asserting
  something the code does not do.

* **`HEARTS_FREE` is exercised for its own sake only** - a boss segment prices health at nothing and
  a flat 200 for surviving. It is restored in a `finally`, because it is a module-level list and
  ordering between checks must never matter.

* **`Goal` and `goal_distance` are geometry, and `goal_distance`'s 100.0 is a magic number.** With
  a `.target` the distance is real Manhattan distance and stays non-zero inside `tol`; without one
  it is 0.0 or 100.0. So the two branches are on different scales - inside a tolerance a goal reads
  as 16 frames away, and a predicate goal that is satisfied reads as 0 - and a caller comparing the
  results across branches is comparing two things. That is what check 10 pins, and it is a property
  of the code rather than a criticism of it.

* **The Lattice, `plan_fight` and `plan_reach` are not here at all.** They need a screen, a tile map
  and an emulator; see `test_derive_and_intent.py`'s note about `head.floor_spot` for the same
  boundary.

Run:  python3 testing/test_value_of.py

---

    python3 testing/test_value_of.py          # any cwd; the bootstrap chdirs to the repo root

## What it touches

- writes `journal/`

## See also

- [`test_ram_addresses.py`](test_ram_addresses.md)
- [`test_ips_patch.py`](test_ips_patch.md)
- [`test_combat_reach.py`](test_combat_reach.md)
- [`probe_old_man.py`](probe_old_man.md)

---

*Generated by `testing/make_doc.py` from the script's own docstring and code. Regenerate with `python3 testing/make_doc.py`; do not hand-edit - `git log` on this file says when.*
