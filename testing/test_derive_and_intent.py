"""Two places where nothing is real: the head's phase, and the panel's captions.

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
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from zelda import head, intent
from zelda.captions import CAPTIONS
from zelda.emulator import State

TAKE, DELIVER, LEAVE = head.TAKE, head.DELIVER, head.LEAVE
GONE, CARRIED, DELIVERED = head.GONE, head.CARRIED, head.DELIVERED
assert (TAKE, DELIVER, LEAVE) == ("gleeok_head", "deliver", "head_exit"), (TAKE, DELIVER, LEAVE)
assert (GONE, CARRIED, DELIVERED) == (0, 1, 2), (GONE, CARRIED, DELIVERED)

# head.py keeps its phase, its delivery spot and what the HUD has been told in module-level lists,
# because it is imported by a long-lived runner rather than constructed. Every check below saves
# and restores them in a finally, so the order these run in cannot matter to each other.
_saved = (list(head._PHASE), list(head._SPOT), list(head._TOLD))


def fresh_phase():
    head._PHASE[0], head._SPOT[0], head._TOLD[0] = GONE, None, None


def restore_phase():
    head._PHASE[0], head._SPOT[0], head._TOLD[0] = _saved


# ------------------------------------------------------------------ 1-3. sync is a function of `done`
try:
    fresh_phase()
    assert head.phase() == GONE and head.carrying() is False and head.spot() is None
    assert head.phase_text() == "still lying in Level 4"
    head.sync([])
    assert (head.phase(), head.carrying(), head.phase_text()) == (GONE, False, "still lying in Level 4")

    head.sync([TAKE])
    assert head.phase() == CARRIED and head.carrying() is True, head.phase()
    assert head.phase_text() == "carried", head.phase_text()

    head.sync([TAKE, DELIVER])
    assert head.phase() == DELIVERED and head.carrying() is False, "carrying() is false once delivered"
    assert head.phase_text() == "left in the sword cave", head.phase_text()

    head.sync([TAKE, DELIVER, LEAVE])
    assert head.phase() == DELIVERED, "a later segment does not move it back"

    # DELIVER wins even when TAKE comes later in the list, and other segments are ignored: the
    # order in `done` is a history, not an instruction.
    head.sync([DELIVER, TAKE])
    assert head.phase() == DELIVERED, "DELIVER takes precedence over TAKE"
    head.sync([LEAVE, "gleeok", "r6_18"])
    assert head.phase() == GONE, "nothing head-shaped means not carrying"

    # 2. BACKWARDS, which is the whole point. A crashed attempt or a stale checkpoint restores a
    # SHORTER `done`, and a mutable flag could not survive that. This is what "the one piece of run
    # state that has never yet lied" buys, checked in the direction that matters.
    for done, want in (([], GONE), ([TAKE], CARRIED), ([TAKE, DELIVER], DELIVERED),
                       ([TAKE], CARRIED), ([], GONE), ([DELIVER], DELIVERED), ([], GONE)):
        head.sync(done)
        assert head.phase() == want, (done, head.phase(), want)

    # 3. order inside `done` cannot matter either, because the function only asks membership
    variants = [[], [TAKE], [DELIVER], [DELIVER, TAKE], [TAKE, DELIVER], [LEAVE, TAKE, DELIVER],
                ["gleeok", TAKE, "r6_18", DELIVER]]
    seen = {}
    for v in variants:
        head.sync(v)
        seen[tuple(sorted(v))] = head.phase()
    by_set = {}
    for v in variants:
        head.sync(list(reversed(v)))
        by_set[tuple(sorted(v))] = head.phase()
    assert seen == by_set, (seen, by_set)

    # and it only logs on a CHANGE, which is what makes the note worth reading
    said = []
    head.sync([TAKE], log=said.append)
    head.sync([TAKE], log=said.append)
    head.sync([TAKE], log=said.append)
    head.sync([TAKE, DELIVER], log=said.append)
    head.sync([], log=said.append)
    assert len(said) == 3, said
    assert said[0] == "Gleeok's head: carried" and said[1] == "Gleeok's head: left in the sword cave", said
    assert said[2] == "Gleeok's head: still lying in Level 4", said
    head.sync([TAKE], log=None)          # log=None must not raise
    print(f"sync() is a pure function of `done`: 3 phases, DELIVER beats TAKE regardless of order, "
          f"{len(variants)} orderings agree pairwise, and walking the ladder backwards "
          f"(take -> deliver -> take -> nothing) lands where it should every time")
finally:
    restore_phase()

# ------------------------------------------------------------------ 4-5. the spot, and the 120
try:
    fresh_phase()
    # 0 is a real x - the leftmost column - and `if x is not None` is what keeps it. A falsy check
    # would silently forget it and the head would go to 120 instead.
    head.remember_spot(0)
    assert head.spot() == 0, head.spot()
    head.remember_spot(140)
    assert head.spot() == 140, head.spot()
    head.remember_spot(None)
    assert head.spot() == 140, "None does not clear it - remember_spot only ever sets"
    head.remember_spot("112")
    assert head.spot() == 112 and isinstance(head.spot(), int), "and it coerces to int"
    fresh_phase()
    assert head.spot() is None, "a fresh process knows nothing"
    # the fallback, which is the limitation rather than a measurement: a state at x=120 on the item
    # row satisfies delivered_test when nothing was ever remembered
    in_cave = State(mode=0x0B, sub=0, level=0, room=0x0A, x=120, y=141, hp=0x34)
    assert head.delivered_test(None, in_cave) is True, "the 120 fallback makes this true"
    head.remember_spot(112)
    assert head.delivered_test(None, in_cave) is False, "and once a real spot is known it is not"
    assert head.delivered_test(None, State(mode=0x0B, sub=0, level=0, x=112, y=141, hp=0x34)) is True
    # ...and the tolerance is +/-2 px, which is the width of a tile plus a little
    assert head.delivered_test(None, State(mode=0x0B, sub=0, level=0, x=110, y=141, hp=0x34)) is True
    assert head.delivered_test(None, State(mode=0x0B, sub=0, level=0, x=109, y=141, hp=0x34)) is False
    fresh_phase()
    assert head.delivered_test(None, in_cave) is True, "back to the fallback"
    print("remember_spot(0) is remembered - 0 is falsy and the guard is `is not None` - and the "
          "delivered test is +/-2 px on x with the 120 fallback; a fresh process knows nothing")
finally:
    restore_phase()

# ------------------------------------------------------------------ 6-7. the two tests, and no flag
try:
    fresh_phase()
    OUTSIDE = State(mode=5, sub=0, level=0, room=0x0A, x=32, y=91, hp=0x34)
    IN_CAVE = State(mode=0x0B, sub=0, level=0, room=0x0A, x=120, y=141, hp=0x34)
    # 6. asymmetric ON PURPOSE (head.py:309-311): left_test wants room $0A in mode 5, delivered_test
    # wants mode $0B, so the two cannot both be true and neither segment can be satisfied by
    # standing still.
    for s in (OUTSIDE, IN_CAVE, State(mode=5, sub=0, level=4, room=0x0A, x=32, y=91, hp=0x34),
              State(mode=0x0B, sub=1, level=0, room=0x0A, x=120, y=141, hp=0x34)):
        assert not (head.left_test(None, s) and head.delivered_test(None, s)), s
    assert head.left_test(None, OUTSIDE) and not head.delivered_test(None, OUTSIDE)
    assert head.delivered_test(None, IN_CAVE) and not head.left_test(None, IN_CAVE)
    # left_test also insists on being ALIVE, so a run that delivered the head and then died has not
    # left the cave
    assert not head.left_test(None, State(mode=5, sub=0, level=0, room=0x0A, x=32, y=91, hp=0x00)), \
        "hearts > 0 is part of it"
    assert not head.left_test(None, State(mode=5, sub=0, level=0, room=0x0B, x=32, y=91, hp=0x34)), \
        "and the room must be $0A"
    # 7. NO FLAG IS CONSULTED, and none is needed: with the phase at GONE - Link is carrying nothing,
    #    the head is on the floor - delivered_test is still True for a RAM state that says otherwise.
    assert head.phase() == GONE and head.carrying() is False
    assert head.delivered_test(None, IN_CAVE) is True, "RAM only, in both directions"
    head.sync([TAKE, DELIVER])
    assert head.phase() == DELIVERED
    assert head.delivered_test(None, IN_CAVE) is True, "the phase changes nothing"
    print("left_test and delivered_test can never both hold (mode 5/room $0A against mode $0B), "
          "left_test wants hearts > 0, and delivered_test reads RAM only: it is True with the phase "
          "at GONE and at DELIVERED")
finally:
    restore_phase()

# ------------------------------------------------------------------ 8-9. for_segment, in order
#
# The ladder, from intent.py:216-243: CAPTIONS, then INTENT, then the old one-line narration, then
# the two suffixes, then the room pattern, then FAMILIES, then ("CROSSING", ...). Each rung below is
# tested against a name that satisfies it AND a lower one, because a name that only satisfies one
# rung cannot tell the order.
CROSSING = ("CROSSING", "Getting to the next room that matters.")
assert intent.for_segment("zzz_no_such_segment_9f3") == CROSSING, "the last rung"
assert len(intent.FAMILIES) == 45, len(intent.FAMILIES)
# rung 1: the fact-checked captions win, and 58 names are in both tables with 27 of them differing -
# so this is a real disagreement and not a formality.
both = [n for n in sorted(set(CAPTIONS) & set(intent.INTENT)) if CAPTIONS[n] != intent.INTENT[n]]
assert len(both) == 27, len(both)
for n in both:
    assert intent.for_segment(n) == CAPTIONS[n], f"{n} came from INTENT, not CAPTIONS"
assert intent.for_segment("dm9_w0b") == CAPTIONS["dm9_w0b"] != intent.INTENT["dm9_w0b"], \
    "dm9_w0b is in CAPTIONS, in INTENT and matches family 'dm9'; the top rung wins all three"
# rung 2: INTENT, against a name that also matches a family. Only 2 of the 88 INTENT entries are
# not also captions, and both match the family "farm" - so they are the only names where this rung
# can be told apart from rung 1 at all, and they are used for exactly that.
only_intent = sorted(set(intent.INTENT) - set(CAPTIONS))
assert only_intent == ["farm68", "farm80"], only_intent
for n in only_intent:
    assert intent.for_segment(n) == intent.INTENT[n], n
    assert any(n.startswith(p) for p, _, _ in intent.FAMILIES), f"{n} also matches a family"
# rung 3: the narration, against a name that is ALSO in INTENT - the narration must lose
for n in ("g9_ganon", "farm68", "l7_62", "cave_67", "l7_61"):
    got = intent.for_segment(n, {n: "NARRATED"})[0]
    assert got != "NARRATED", f"{n} took the narration over a hand-written entry"
assert intent.for_segment("ws_01", {"ws_01": "NARRATED"}) == ("NARRATED", ""), \
    "a name with NO hand-written entry DOES take the narration - the rung above the families"
assert intent.for_segment("ws_01")[0] == "WALKING TO THE WHITE SWORD", "and with no narration, the family"
assert intent.for_segment("zzz_unknown", {"zzz_unknown": "NARRATED"}) == ("NARRATED", ""), \
    "and narration beats the catch-all"
assert intent.for_segment("zzz_unknown", {}) == CROSSING
# rungs 4 and 5: the suffixes, BEFORE the room pattern - and both of these names match it
assert "7c_done" in intent.INTENT or True
assert intent.ROOM_NAME.match("7c_done") and intent.ROOM_NAME.match("4a_key"), "both are room-shaped"
assert intent.for_segment("7c_done")[0] == "A TRIFORCE PIECE", "_done beats the room pattern"
assert intent.for_segment("4a_key")[0] == "A KEY", "_key beats the room pattern"
# rung 6: the room pattern, before FAMILIES. "b7_x" is two hex digits and an underscore AND starts
# with the family prefix "b7", so only the order can say which head it gets.
assert intent.ROOM_NAME.match("b7_x") and any("b7_x".startswith(p) for p, _, _ in intent.FAMILIES)
assert intent.for_segment("b7_x") == ("LEVEL 3 - THE MANJI", intent.for_segment("b7_x")[1]), \
    "the room pattern wins, and the family 'b7' (BACK TO LEVEL 7) does not"
# rung 7: FAMILIES, first match wins - and "l9_x" matches both 'l9_' and the catch-all 'l'
assert intent.for_segment("l9_x")[0] == "LEVEL 9 - DEATH MOUNTAIN", "l9_ is before l"
assert intent.for_segment("l_x")[0] == "CROSSING", "the catch-all 'l' is second to last"
assert intent.for_segment("l7w03_52")[0] == "CROSSING HYRULE", "the name the docstring quotes"
assert intent.for_segment("ow_x")[0] == "CROSSING HYRULE", "and 'ow' is last of all"
# Every family prefix is reachable. `expect` is read out of FAMILIES, so on its own that loop only
# proves reachability - it would pass with every head rewritten. The longhand table below is the
# independent transcription, and it is what a reworded caption has to disagree with.
for prefix, expect, _why in intent.FAMILIES:
    head_text = intent.for_segment(prefix + "zz")[0]
    assert head_text == expect, (prefix, head_text, expect)
LONGHAND = {
    "ws_": "WALKING TO THE WHITE SWORD", "hills_": "THE LOST HILLS",
    "bwoods_": "THE LOST WOODS, GOING BACK", "woods_": "THE LOST WOODS",
    "back": "WALKING BACK", "bw": "WALKING BACK", "heal": "A FAIRY POND",
    "p7": "TOWARD LEVEL 7", "sh7": "UP TO THE ARROWS SHOP",
    "bait_": "THE GRAVEYARD SHOP", "fw7": "BACK ON THE ROAD WEST",
    "m7": "CROSSING TO THE SHOPS", "b7": "BACK TO LEVEL 7",
    "w7": "LEAVING LEVEL 7", "w8": "TOWARD LEVEL 8", "n8": "TOWARD LEVEL 8",
    "o8": "TOWARD LEVEL 8", "m8": "AROUND LEVEL 8", "s8": "TOWARD LEVEL 8",
    "dm9": "UP DEATH MOUNTAIN", "wl8": "TOWARD LEVEL 8",
    "n9": "TOWARD DEATH MOUNTAIN", "h9": "TOWARD DEATH MOUNTAIN",
    "x9": "OUT OF LEVEL 9", "r9": "BACK INTO LEVEL 9", "rb": "THE SUPPLY RUN",
    "ms_": "TOWARD THE MAGICAL SWORD", "m9": "LEVEL 9",
    "l7w": "CROSSING HYRULE", "l5w": "CROSSING HYRULE", "l4w": "CROSSING HYRULE",
    "l2w": "CROSSING HYRULE", "l3w": "CROSSING HYRULE",
    "warp_": "RECORDER WARP", "whirl": "RIDING THE WHIRLWIND", "enter_": "GOING IN",
    "hc_": "A HEART CONTAINER IN A CAVE", "farm": "EARNING RUPEES THE SLOW WAY",
    "fd": "EARNING RUPEES THE SLOW WAY", "shop": "WALKING TO THE SHOP",
    "l9_": "LEVEL 9 - DEATH MOUNTAIN", "s9_": "LEVEL 9", "g9_": "LEVEL 9",
    "l": "CROSSING", "ow": "CROSSING HYRULE",
}
assert len(LONGHAND) == len(intent.FAMILIES) == 45, (len(LONGHAND), len(intent.FAMILIES))
assert set(LONGHAND) == {p for p, _, _ in intent.FAMILIES}, \
    sorted(set(LONGHAND) ^ {p for p, _, _ in intent.FAMILIES})
for prefix, expect in LONGHAND.items():
    assert intent.for_segment(prefix + "zz")[0] == expect, (prefix, expect)
assert len({h for _, h, _ in intent.FAMILIES}) == 31, (
    "31 distinct heads over 45 prefixes - five share CROSSING HYRULE and six share TOWARD LEVEL 8, "
    "which is deliberate and is why the ORDER matters")
print(f"for_segment's ladder, in order: CAPTIONS beats INTENT on {len(both)} of "
      f"{len(set(CAPTIONS) & set(intent.INTENT))} names in both; narration loses to INTENT; the two "
      f"suffixes beat the room pattern; the room pattern beats FAMILIES ('b7_x' is room-shaped AND "
      f"starts with 'b7'); all {len(intent.FAMILIES)} prefixes reachable, "
      f"{len({h for _, h, _ in intent.FAMILIES})} distinct heads")

# 9. the promise at intent.py:217-219: never returns the raw segment name. 244 of the run's
#    segments did before the rules existed. Checked over every name in INTENT and a generated
#    cross-product of the family prefixes and the shapes the route actually builds.
probe = sorted(set(intent.INTENT) | set(CAPTIONS) | set(intent.FAMILIES and
                [p + s for p, _, _ in intent.FAMILIES for s in ("", "01", "03_52", "x", "_done",
                                                                "_key")]))
probe += [f"{r:02x}_{s}" for r in (0x00, 0x07, 0x0A, 0x4A, 0x69, 0x7C, 0xD8, 0xFF)
          for s in ("", "key", "done", "left", "0f")]
leaked = [n for n in probe if intent.for_segment(n)[0] == n]
assert not leaked, leaked[:8]
assert len(probe) > 200, len(probe)
for n in intent.INTENT:
    assert intent.for_segment(n)[0] == CAPTIONS.get(n, intent.INTENT[n])[0], n
print(f"never returns the raw name: {len(probe)} generated and real segment names, 0 leaked; "
      f"{len(intent.INTENT)} hand-written heads and {len(CAPTIONS)} captions all reachable")

# ------------------------------------------------------------------ 10. _N's six spellings
N = intent._N
assert len(intent._WORDS) == len(intent._ORD) == 17, (len(intent._WORDS), len(intent._ORD))
SIX = ("w", "W", "C", "o", "O")
assert f"{N(8)}" == "8", "no spec is the plain int"
assert [f"{N(8):{sp}}" for sp in SIX] == ["eight", "EIGHT", "Eight", "eighth", "EIGHTH"]
assert [f"{N(0):{sp}}" for sp in SIX] == ["zero", "ZERO", "Zero", "zeroth", "ZEROTH"]
assert [f"{N(12):{sp}}" for sp in SIX] == ["twelve", "TWELVE", "Twelve", "twelfth", "TWELFTH"]
assert [f"{N(16):{sp}}" for sp in SIX][0] == "sixteen", "sixteen is the last word"
assert f"{N(17):w}" == "17" and f"{N(17):o}" == "17", "and 17 is past the end of the list"
assert f"{N(-1):w}" == "-1", "negative falls through too"
# the fall-through keeps every other format spec, which is what lets _N be an int everywhere else
assert f"{N(8):03d}" == "008" and f"{N(8):x}" == "8" and f"{N(255):x}" == "ff"
assert f"{N(8):,}" == "8" and f"{N(1234):,}" == "1,234"
assert isinstance(N(8) + 1, int) and N(8) == 8, "_N is an int, so it can be summed like one"
assert intent._N(3) + intent._N(4) == 7
print(f"_N spells itself six ways (w W C o O) from {len(intent._WORDS)} words; {N(16):w} is the last "
      f"and {N(17):w} is '17'; every other format spec passes through, so it stays an int")

# ------------------------------------------------------------------ 11. facts_from, and fill's swallow
def state(hp_nybble=3, frac=0x00, containers=1, **kw):
    return State(hp=((containers - 1) << 4) | (hp_nybble & 0x0F), hpfrac=frac, **kw)


f = intent.facts_from(state(3, 0x40, 4, triforce=0b1010_0101, bombs=7, keys=2, rupees=48))
assert set(f) == {"tri", "tri1", "containers", "containers1", "hearts", "bombs", "keys", "rupees"}, sorted(f)
assert f"{f['tri']}" == "4" and f"{f['tri1']}" == "5", (f["tri"], f["tri1"])
assert f"{f['containers']}" == "4" and f"{f['containers1']}" == "5"
assert f"{f['bombs']:w}" == "seven" and f"{f['rupees']}" == "48" and f"{f['keys']:o}" == "second"
# the caption template from intent.py:250 - write {tri1:w} OF 8, {containers:w}, {bombs} bombs
filled = intent.fill("TRIFORCE {tri1} OF 8, {containers:C} containers ({containers1} counting this "
                     "one), {hearts} hearts, {bombs} bombs and {keys} keys", f)
assert filled == ("TRIFORCE 5 OF 8, Four containers (5 counting this one), 3.5 hearts, 7 bombs "
                  "and 2 keys"), filled
# the Triforce byte is masked to 8 bits, so a ninth piece cannot be counted
assert f"{intent.facts_from(state(triforce=0x1FF))['tri']}" == "8", "0x1FF & 0xFF is eight"
assert f"{intent.facts_from(state(triforce=0x100))['tri']}" == "0", "bit 8 is outside the field"
# a partial state - anything without triforce - must not raise, because getattr has a default
bare = intent.facts_from(State(hp=0x34))
assert f"{bare['tri']}" == "0" and f"{bare['containers']}" == "4" and f"{bare['hearts']}" == "4"
# `hearts` is an int when it is whole and a float when it is not, so a caption reads "4" not "4.0"
assert type(intent.facts_from(state(3, 0x00, 1))["hearts"]) is int
assert type(intent.facts_from(state(3, 0x40, 1))["hearts"]) is float
# an unknown key is left ALONE rather than raising - that is the whole point of _Keep
assert intent.fill("{nope} {tri}", f) == "{nope} 4", "unknown keys keep their braces"
assert intent.fill("no braces here", f) == "no braces here"
assert intent.fill("{tri}", None) == "{tri}", "no facts means no substitution"
# ...and the swallow. intent.py:288-289 returns the text unchanged when the format blows up, so a
# stray brace reaches the viewer instead of raising. Named here rather than tested around: a test
# that called this a success would be endorsing it.
assert intent.fill("{unclosed", f) == "{unclosed", "the swallow, stated"
assert intent.fill("{0}", f) == "{0}", "index form is not a key either"
assert intent.fill("{tri", f) == "{tri"
print(f"facts_from gives 8 keys and counts the Triforce byte's low 8 bits (0xA5 = 4 pieces, "
      f"bit 8 ignored); _Keep leaves unknown braces alone; and fill's `except (ValueError, "
      f"IndexError, KeyError)` returns the text unchanged - '{{unclosed' in, '{{unclosed' out")

print("all checks passed")