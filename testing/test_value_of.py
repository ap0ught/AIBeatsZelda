"""The ranking function, the two prices it reads, and the predicates that feed them.

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
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from zelda import lookahead, search
from zelda.emulator import State
from zelda.search import Attempt, BOMB_CAP, BOMB_VALUE, CONVERGE, CONVERGE_TOL, HEART_VALUE, \
    HEART_VALUE_MID, HEART_VALUE_TOP, HEARTS_FREE, value_of


def attempt(frames=100, hearts=4.0, bombs=0, bonus=0.0):
    return Attempt(seed=1, frames=frames, hearts=hearts, bombs=bombs, bonus=bonus)


def cliff_for(containers):
    """The cliff, written out from search.py:287-289 rather than imported, so the test can be wrong
    about it and say so."""
    return min(4.0, max(1.5, 0.5 * containers))


# ------------------------------------------------------------------ 1. the marginal price of a heart
assert (HEART_VALUE[0], HEART_VALUE_MID[0], HEART_VALUE_TOP[0]) == (1800, 900, 360), \
    (HEART_VALUE, HEART_VALUE_MID, HEART_VALUE_TOP)
# The marginal price, heart by heart. Read at ONE container so the cliff is out of the way - with
# containers=1 the cliff is 1.5, so every heart from 2.0 up is priced on the tiers alone.
marginal = []
prev = None
for h in (2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0):
    v = value_of(attempt(0, h), 1)
    marginal.append(None if prev is None else v - prev)
    prev = v
assert marginal == [None, 1800.0, 1800.0, 900.0, 900.0, 900.0, 360.0, 360.0], marginal
# below the cliff the price is 5,800 a heart, so HALF a heart costs 2,900 there and 900
# above it. 1.5 IS the cliff at one container, which is why the last half step is cheap.
assert value_of(attempt(0, 1.5), 1) - value_of(attempt(0, 1.0), 1) == 2900.0, "half a heart"
assert value_of(attempt(0, 2.0), 1) - value_of(attempt(0, 1.5), 1) == 900.0, "half a heart"
# 1800 a heart for the first four, 900 for five through seven, 360 above that - where "a heart is
# genuinely just margin", as the comment says. The tiers are where the boundaries are, so each is
# pinned by the pair that straddles it.
TIERS = ((2.0, 3.0, 1800.0), (3.0, 4.0, 1800.0),     # still in the 1800 tier
         (4.0, 5.0, 900.0), (6.0, 7.0, 900.0),       # five through seven at 900
         (7.0, 8.0, 360.0), (8.0, 9.0, 360.0))       # above seven at 360
assert len(TIERS) == 6, len(TIERS)
for lo, hi, want in TIERS:
    got = value_of(attempt(0, hi), 1) - value_of(attempt(0, lo), 1)
    assert got == want, (lo, hi, got, want)
# and the absolute price of the first four, which is what the White Sword comment is about
for h, want in ((2, 2 * 1800), (3, 3 * 1800), (4, 4 * 1800), (5, 4 * 1800 + 900),
                (7, 4 * 1800 + 3 * 900), (8, 4 * 1800 + 3 * 900 + 360)):
    assert value_of(attempt(0, float(h)), 1) == want, (h, value_of(attempt(0, float(h)), 1), want)
# a heart is worth more than the convergence tolerance by a factor of 90 - which is exactly why
# convergence, which counts FRAMES, cannot see a heart being given away (see the module docstring)
assert HEART_VALUE[0] / CONVERGE_TOL[0] == 90.0, (HEART_VALUE[0], CONVERGE_TOL[0])
print(f"marginal price of a heart above the cliff: 1800 for hearts 1-4, 900 for 5-7, 360 above; "
      f"HEART_VALUE/CONVERGE_TOL = {HEART_VALUE[0] / CONVERGE_TOL[0]:.0f}")

# ------------------------------------------------------------------ 2-3. the cliff
#
# `cliff_for` is the cliff written out LONGHAND, so the expectations below are a second copy of the
# formula and not a view of it - which is only worth having because check 2 also pins the same three
# facts through `value_of` itself, on the far side of the function. Read those three, not this list.
BARS = (1, 2, 3, 4, 5, 6, 8, 12, 16)      # every shape of bar the run reaches
assert len(BARS) == 9, BARS
assert [cliff_for(c) for c in BARS[:8]] == [1.5, 1.5, 1.5, 2.0, 2.5, 3.0, 4.0, 4.0]
assert cliff_for(16) == 4.0, "the high end is capped at 4.0, not 8.0"
# Both ends of the cliff are pinned THROUGH value_of as well, because a helper written beside the
# code is a second copy of it and proves nothing on its own. Twelve containers is the case where the
# upper cap binds: without the cap the cliff there would be 6.0 and 2.0 hearts would cost 16,000
# frames of penalty instead of 8,000.
assert value_of(attempt(0, 2.0), 12) == 2 * HEART_VALUE[0] - (4.0 - 2.0) * 4000, \
    "the cliff's upper cap is 4.0 even at twelve containers"
assert value_of(attempt(0, 2.0), 1) == 2 * HEART_VALUE[0], \
    "the cliff's floor is 1.5 even at ONE container, so a full 2-heart bar is above it and free"
assert value_of(attempt(0, 1.0), 1) == 1 * HEART_VALUE[0] - (1.5 - 1.0) * 4000, \
    "and one heart on a one-container bar costs 2,000 frames of penalty"
# THE assertion. At 8 containers the cliff is exactly 4.0, and 4.0 beats 3.5 at the same frame
# count by 2,900 frames - which is 2,900x what a frame costs, and 145x the convergence tolerance.
at4, at35 = value_of(attempt(300, 4.0), 8), value_of(attempt(300, 3.5), 8)
assert at4 > at35, (at4, at35)
gap = at4 - at35
assert gap == 2900.0, gap
assert gap == 0.5 * HEART_VALUE[0] + 0.5 * 4000, (gap, "half a heart at 1800 plus half at the 4000 rate")
assert gap > 1000 and gap / CONVERGE_TOL[0] == 145.0, gap / CONVERGE_TOL[0]
# at 5 containers the cliff is 2.5, so 4.0 and 3.5 are BOTH above it and the gap is only the heart
assert value_of(attempt(300, 4.0), 5) - value_of(attempt(300, 3.5), 5) == 900.0, \
    "same hearts, different bar: the cliff is what makes 3.5 vs 4.0 worth 2,900 and not 900"
# and it is a RATE change, not a step: the penalty is exactly zero at the cliff and linear below
assert value_of(attempt(300, 4.0), 8) == 4 * HEART_VALUE[0] - 300, "at the cliff, penalty zero"
just_under = value_of(attempt(300, 3.9), 8) - value_of(attempt(300, 4.0), 8)
assert just_under == -580.0, just_under          # 0.1 heart below, at 5,800 frames a heart
assert value_of(attempt(300, 4.0 - 1e-9), 8) < at4, "a hair below the cliff already costs something"
# the slope is 1800 above the cliff and 5800 below it: 1800 + 4000
assert 1800 + 4000 == 5800
print(f"cliff = min(4.0, max(1.5, containers/2)): 1.5 up to 3 containers, 4.0 from 8; at 8 "
      f"containers 4.0 beats 3.5 by {gap:.0f} frames ({gap / CONVERGE_TOL[0]:.0f}x the convergence "
      f"tolerance), and the slope goes 1800 -> 5800 rather than stepping")

# ------------------------------------------------------------------ 4. bombs
assert BOMB_VALUE[0] == 220 and BOMB_CAP[0] == 8, (BOMB_VALUE, BOMB_CAP)
for n, want in ((0, 0), (1, 220), (4, 880), (8, 1760), (9, 1760), (12, 1760), (255, 1760)):
    assert value_of(attempt(100, 8.0, bombs=n), 8) - value_of(attempt(100, 8.0), 8) == want, (n, want)
# a bomb is worth 220 frames and a heart 1,800, so eight bombs (1,760) are worth almost exactly one
# heart - which is what "a wall bombed saves 500+" is arguing, one bomb at a time
assert abs(BOMB_CAP[0] * BOMB_VALUE[0] - HEART_VALUE[0]) == 40, \
    "8 bombs = 1,760 frames against 1,800 for a heart: close enough that the cap is the decision"
# bombs do not move the cliff, and a bomb cannot buy back a heart below it
assert value_of(attempt(300, 2.0, bombs=8), 8) - value_of(attempt(300, 2.0), 8) == 1760
assert value_of(attempt(300, 2.0, bombs=8), 8) < value_of(attempt(300, 2.5), 8), \
    "1,760 frames of bombs is not a heart: 2.0 + 8 bombs still ranks below 2.5 with none"
print(f"bombs: 220 frames each, capped at {BOMB_CAP[0]} = {BOMB_CAP[0] * BOMB_VALUE[0]} frames, "
      f"which is 40 frames short of one heart - and eight bombs do not lift 2.0 hearts past 2.5")

# ------------------------------------------------------------------ 5. frames, and HEARTS_FREE
assert value_of(attempt(301, 4.0), 8) - value_of(attempt(300, 4.0), 8) == -1.0, "a frame is a frame"
assert value_of(attempt(300, 4.0, bonus=250.0), 8) - value_of(attempt(300, 4.0), 8) == 250.0, \
    "EXTRA_VALUE's staged-fight bonus is additive, in frames-equivalent"
try:
    assert value_of(attempt(300, 0.0, bonus=99999.0), 8) > value_of(attempt(0, 12.0), 8), \
        "an enormous bonus beats a full bar, which is what 'extra frames-equivalent worth' means"
    # a boss: health is worth nothing at all, and surviving with 2 hearts is worth a flat 200
    HEARTS_FREE[0] = True
    free = lambda h, f=100: value_of(attempt(f, h), 8)
    assert free(4.0) == -100.0 + 200 + 0, free(4.0)
    assert free(1.5) == -100.0 + 0, free(1.5)
    assert free(0.0) == -100.0, "a refill is coming, so even dying cheap is not priced in health"
    assert free(12.0) == free(4.0), "every bar above 2 hearts is worth the same 200 on a boss"
    assert free(4.0, 150) - free(4.0, 100) == -50.0, "frames still cost frames"
    # ...and the cliff is not consulted at all while it is on
    assert free(0.0) > free(0.0) - 1, "no cliff, no hearts"
finally:
    HEARTS_FREE[0] = False
assert value_of(attempt(300, 4.0), 8) == at4, "restored"
print("frames cost exactly 1 frame each; bonus is additive in frames-equivalent; with HEARTS_FREE "
      "(a boss) health is worth 0 and 2+ hearts is worth a flat 200, cliff not consulted")

# ------------------------------------------------------------------ 6-7. caution
def hp_state(hearts, containers=8, **kw):
    """A State whose `hearts` and `containers` are exactly the two numbers asked for."""
    full, rest = int(hearts), float(hearts) - int(hearts)
    frac = 0x00 if rest == 0 else (0x80 if rest >= 1.0 else 0x40)
    return State(hp=((max(1, containers) - 1) << 4) | (full & 0x0F), hpfrac=frac, **kw)


assert lookahead.OLD_PLANNER[0] is False, "the A/B default is the cautious planner"
OLD, OVERRIDE = lookahead.OLD_PLANNER[0], lookahead.CAUTION_OVERRIDE[0]
# all five branches, and every boundary between them, at 8 containers
assert lookahead.caution(hp_state(0.0)) == 1.5, "no hearts: every half heart is 1.5x"
assert lookahead.caution(hp_state(2.0)) == 1.5, "the low branch is <= 2.0"
assert lookahead.caution(hp_state(2.5)) == 1.0, "and the middle is <= 3.5"
assert lookahead.caution(hp_state(3.5)) == 1.0
assert lookahead.caution(hp_state(4.0)) == 0.55, "between 3.5 and the 3/4 bar: 0.55"
assert lookahead.caution(hp_state(4.5)) == 0.55
assert lookahead.caution(hp_state(5.0)) == 0.55, "5.0 of 8 is 0.625 of the bar, under 0.75"
assert lookahead.caution(hp_state(6.0)) == 0.3, "6.0 of 8 IS 0.75 - the boundary, inclusive"
assert lookahead.caution(hp_state(7.99)) == 0.3, "under 8 but three quarters full"
assert lookahead.caution(hp_state(8.0)) == 0.3, "the top branch is >= 8"
assert lookahead.caution(hp_state(12.0, 12)) == 0.3
# ...and caution is NOT monotone in the fraction full at a small bar, because the two low-health
# branches are checked FIRST. A full bar of three containers reads 1.0, not 0.3. That is not a bug -
# it says a lost half heart is still expensive at 3 hearts - but it means "full bar" and "cautious"
# are not the same predicate, and the loop below is the fact rather than the slogan.
for containers in range(1, 16):
    got = lookahead.caution(hp_state(float(containers), containers))
    want = 0.3 if containers >= 5 else {1: 1.5, 2: 1.5, 3: 1.0, 4: 0.55}[containers]
    assert got == want, (containers, got, want)
assert lookahead.caution(hp_state(3.0, 3)) == 1.0, "a FULL three-container bar is priced 1.0"
assert lookahead.caution(hp_state(5.0, 5)) == 0.3, "and a full five-container bar is priced 0.3"
# a bar of 0 is treated as a bar of 1, rather than dividing by zero
assert lookahead.caution(hp_state(0.0, 0)) == 1.5, "containers is max(1, ...)"
try:
    # 7. THE ONE THAT COST A RUN. The override used to be gated on "there is health to spend",
    # which is the wrong condition: the Triforce piece behind the boss restores every heart whether
    # or not Link has any left. Gated, the override switched itself off at 3.5 hearts and the
    # planner became MORE careful the lower he got, inside a fight where damage costs nothing.
    lookahead.CAUTION_OVERRIDE[0] = 0.0
    for h in (0.0, 0.5, 1.0, 2.0, 2.5, 3.0, 3.5, 4.0, 8.0):
        assert lookahead.caution(hp_state(h)) == 0.0, (h, "a full refill is worth nothing at any health")
    lookahead.CAUTION_OVERRIDE[0] = 0.25
    assert lookahead.caution(hp_state(0.0, 0)) == 0.25, "and at zero hearts and zero containers"
    # ...and it beats the ordinary tiers wherever they would have said otherwise
    assert lookahead.caution(hp_state(0.5)) == 0.25 < 1.5, "0.25 where the table would have said 1.5"
    lookahead.CAUTION_OVERRIDE[0] = None
    assert lookahead.caution(hp_state(0.5)) == 1.5, "restored"
    # OLD_PLANNER is the other knob: flat prices, and it is checked first, so it beats the override
    lookahead.OLD_PLANNER[0] = True
    lookahead.CAUTION_OVERRIDE[0] = 0.25
    assert lookahead.caution(hp_state(0.0)) == 1.0, "OLD_PLANNER short-circuits to 1.0"
finally:
    lookahead.OLD_PLANNER[0], lookahead.CAUTION_OVERRIDE[0] = OLD, OVERRIDE
assert (lookahead.OLD_PLANNER[0], lookahead.CAUTION_OVERRIDE[0]) == (False, None)
print("caution: 1.5 at <=2.0, 1.0 to 3.5, 0.55 between 3.5 and three-quarters of the bar, 0.3 at or "
      "above 6/8 or 8 hearts; and it is NOT monotone at a small bar - a FULL 3-container bar reads "
      "1.0 because the low-health branches are checked first; containers 0 is read as 1")
print("caution's override is NOT gated on having health left: it returns its own value at 0 hearts, "
      "which is the bug search.py/lookahead.py:52-58 says cost a Gleeok attempt")

# ------------------------------------------------------------------ 8. must_kill
# The owner's rule, verbatim: "anytime he has a full health and the white sword he must kill the
# lynol." Three conjuncts, and each one on its own turns the answer off.
assert lookahead.must_kill(0x01, hp_state(8.0, 8, sword=2)) is True
assert lookahead.must_kill(0x02, hp_state(8.0, 8, sword=2)) is True, "both Lynels"
assert lookahead.must_kill(0x01, hp_state(8.0, 8, sword=1)) is False, "wooden sword is not enough"
assert lookahead.must_kill(0x01, hp_state(7.0, 8, sword=2)) is False, "a heart short of full is not full"
for t in (0x13, 0x0B, 0x0C, 0x03, 0x03, 0x00):
    assert lookahead.must_kill(t, hp_state(8.0, 8, sword=3)) is False, f"only the Lynels: {t:#04x}"
# it is deliberately about STATE and not about a segment: the same enemy is the objective on the way
# out and nothing on the way in, with no route edit, because the sword and the bar changed
on_the_way_in = lookahead.must_kill(0x01, hp_state(4.0, 8, sword=1))
after_the_boss = lookahead.must_kill(0x01, hp_state(8.0, 8, sword=2))
assert on_the_way_in is False and after_the_boss is True, "the condition switches itself on"
print("must_kill is 0x01/0x02 AND sword >= 2 AND hearts >= containers: three conjuncts, each "
      "independently enough to turn it off, and the same Lynel flips with no route edit")

# ------------------------------------------------------------------ 9-10. Goal and goal_distance
g = lookahead.Goal(100, 100)
assert (g.target, g.tol) == ((100, 100), 8), (g.target, g.tol)
# a square, and INCLUSIVE on both axes: |dx| <= tol and |dy| <= tol, not "and"
assert g(100, 100) and g(108, 108) and g(92, 100) and g(100, 92) and g(108, 108)
assert not g(109, 108) and not g(117, 100) and not g(91, 100), "one pixel outside is out"
assert not g(200, 200)
assert lookahead.Goal(50, 60, tol=0)(50, 60) and not lookahead.Goal(50, 60, tol=0)(51, 60)
# the corner, which an L1 distance would get wrong
assert g(108, 92) is True, "the tolerance is a square, not a diamond"
assert lookahead.goal_distance(g, hp_state(0, 8, x=108, y=92)) == 16, "Manhattan inside a square"
# 10. the two branches of goal_distance are NOT on the same scale, and that is pinned here rather
#     than left to be discovered by a planner that suddenly prefers one goal shape to another
assert lookahead.goal_distance(g, hp_state(0, 8, x=100, y=100)) == 0, "on the target: 0"
assert lookahead.goal_distance(g, hp_state(0, 8, x=108, y=108)) == 16, \
    "SATISFIED and still 16 away: goal_distance does not know about tol"
assert lookahead.goal_distance(g, hp_state(0, 8, x=130, y=60)) == 70, "70 frames away, Manhattan"
pred = lambda x, y: x == 5
assert lookahead.goal_distance(pred, hp_state(0, 8, x=5, y=0)) == 0.0, "a bare predicate, satisfied"
assert lookahead.goal_distance(pred, hp_state(0, 8, x=6, y=0)) == 100.0, "and 100.0, the magic number"
assert lookahead.goal_distance(pred, hp_state(0, 8, x=500, y=500)) == 100.0, "100.0 is not a distance"
# a Goal has no way to be targetless, so the 100.0 branch is only reachable with a bare callable
assert hasattr(g, "target") and not hasattr(pred, "target")
print(f"Goal is an inclusive square of tol {g.tol} - the corner (108,92) is inside - and "
      f"goal_distance reads {lookahead.goal_distance(g, hp_state(0, 8, x=108, y=108)):.0f} for a "
      f"goal that is satisfied, because it does not consult tol; a bare predicate reads 0.0 or "
      f"100.0 instead")

# ------------------------------------------------------------------ the untested mechanism
#
# `search.CONVERGE[0]` and `search.HEART_FLOOR[0]` are module-level lists, and
# `testing/test_search_machinery.py:51` sets the first to False at import time and never restores it.
# So in every process that has run that file, `search.py:615-651` - the convergence stop AND the
# HEART_FLOOR suppression that exists to override it - has never executed. The DEFAULTS are pinned
# here so that a change is visible, and the fact that they are unreachable under test is a finding
# rather than a check: see the module docstring. Restoring the flag belongs to the other file.
assert CONVERGE == [True], f"CONVERGE default is {CONVERGE}; test_search_machinery.py:51 turns it off"
assert CONVERGE_TOL == [20], CONVERGE_TOL
assert search.HEART_FLOOR == [0.0], search.HEART_FLOOR
assert search.ACCEPT_AFTER[0] > 0, search.ACCEPT_AFTER
# the number the convergence stop compares against is 90x below what one heart is worth, so a search
# can settle on a line that is 20 frames slower and half a heart poorer without noticing
assert CONVERGE_TOL[0] * 90 == HEART_VALUE[0], (CONVERGE_TOL[0], HEART_VALUE[0])
print(f"untested by construction: CONVERGE={CONVERGE} CONVERGE_TOL={CONVERGE_TOL} "
      f"HEART_FLOOR={search.HEART_FLOOR} ACCEPT_AFTER={search.ACCEPT_AFTER} - "
      f"test_search_machinery.py:51 sets CONVERGE[0]=False and nothing re-enables it")

print("all checks passed")