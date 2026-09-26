"""Fairy stops: real legs, and no verdict until both numbers are measured.

    python3 testing/test_fairy_stops.py

Issue #1 asked whether a deliberate fairy stop pays for itself, and PR #7 answered
"no, +4,994 frames" - which was an artifact. `evaluate()`'s `hearts` is a gate (the
WS/MS threshold), not a commodity, so a healing errand can only ever ADD cost and the
search rejects it for any value of its cost constant. Charging the walk and ranking
the result produces a number indistinguishable, in the output, from a measurement.

These tests pin the two properties that make that impossible to repeat:

1. **The fairy nodes have real legs.** PR #7 pointed `fairy_42`'s lookup at L7's
   door to avoid rebuilding the leg table. I reviewed that as charging the walk to
   the wrong screen and **was wrong** - `fairy_42` and L7 are the same place, both
   `(0x42, 112, 157)`, so the alias was numerically exact. The test records that
   coincidence, so it is not mistaken for a bug if anyone ever separates the two.

   The alias is gone anyway, for a reason that is not about the number: it held only
   while two entries in `P` stayed coincident, and it concealed a stale cache. So the
   test here is about the general hazard rather than these two nodes - every place in
   `P` must have a row in the cached leg table, or the cache is stale and the cost is
   whatever the table happens to say.

2. **A healing stop raises `Unpriceable` until both halves are measured.** Not
   `Infeasible` - that is swallowed a hundred times a search and would hide a missing
   measurement behind silent rejections - and not a number.

The break-even is worth stating, because it is computable without the model and is
what issue #11 has to beat: 4,994 frames per heart for `fairy_2C` (3.6 hearts at the
1,403 average) and **396 for `fairy_42`, which costs no walk at all** (0.28 hearts).
`fairy_42` is very likely worth taking opportunistically and `fairy_2C` very likely
is not - so "both stops are a net loss" is not a finding, it is one conclusion
mechanically applied to two stops that are not comparable.

Deliberately absent: a test that zeroes the legs and asserts the delta equals a cost
constant. That shape is what PR #7 had, and it certifies the omission as correct
behaviour. What is asserted here is that the omission is no longer possible.
"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # knowledge/ow_legs.json is repo-relative
del _os, _sys, _pathlib

import json
import unittest
from pathlib import Path

import route_planner as rp


def _zero_legs(nodes):
    """All legs 0.0, so a test sees only the errand arithmetic and not the map.

    "start" is added because evaluate() seeds `at` with that literal and it is not one of
    CURRENT's errands - without it every leg lookup misses and the first thing you get is
    Infeasible("cannot reach L3 from start"), which is how the first version of this file
    failed all five of its arithmetic tests for a reason that had nothing to do with them.
    """
    nodes = {"start", *nodes}
    table = {a: {b: 0.0 for b in nodes} for a in nodes}
    return {"base": table, "raft": table, "ladder": table}


def _with_fairy(after: str) -> list[str]:
    seq = list(rp.CURRENT)
    seq.insert(seq.index(after) + 1, "fairy_2C")
    return seq


class FairyNodeGeometry(unittest.TestCase):
    """The legs are real, and the cache cannot be stale.

    A correction, because the first version of this file asserted something false. It
    claimed `fairy_42` must not be priced like L7's door, on the grounds that PR #7's
    WALK_ALIAS sent the walk "to a different screen". It does not: `fairy_42` and `L7`
    are the *same* place - both `(0x42, 112, 157)` - so the alias was numerically exact
    and my review of it was wrong.

    The alias was still worth removing, for a different reason than the one I gave: it
    only stayed correct while two entries in `P` remained coincident, and it hid a stale
    cache from view. So the property actually worth testing is the general one - every
    place in `P` has a row in the cached leg table - which is what the alias was
    papering over, and which catches the mistake for any node rather than just these two.
    """

    def test_fairy_nodes_are_in_the_place_table(self):
        for name in rp.HEAL:
            self.assertIn(name, rp.P, f"{name} is an errand with no place")

    def test_every_place_has_a_row_in_the_cached_leg_table(self):
        # A stale cache is the real hazard: a node added to P without a rebuild gets
        # silently mispriced, or raises "cannot reach" from deep inside evaluate().
        cache = rp.CACHE
        self.assertTrue(cache.exists(), f"no leg cache at {cache}")
        L = json.loads(cache.read_text())
        for variant in ("base", "raft", "ladder"):
            missing = sorted(n for n in rp.P if n not in L[variant])
            self.assertEqual(missing, [],
                             f"{len(missing)} place(s) have no row in the {variant} leg table "
                             f"- rebuild it: python3 route_planner.py --rebuild")
        self.assertNotIn("WALK_ALIAS", vars(rp),
                         "WALK_ALIAS is back; the nodes are real now, so it would be a second "
                         "source of truth for where a walk goes")

    def test_fairy_42_and_L7_are_the_same_place(self):
        # Recorded so the coincidence is not mistaken for a bug if someone separates them.
        self.assertEqual(rp.P["fairy_42"], rp.P["L7"])


class HealingIsUnpriceableUntilMeasured(unittest.TestCase):
    """The fix for #1: no number, and a clear reason, instead of a confident one."""

    def setUp(self):
        self._fs, self._hv = rp.FAIRY_STOP[0], rp.HEART_VALUE[0]
        self.addCleanup(lambda: rp.FAIRY_STOP.__setitem__(0, self._fs))
        self.addCleanup(lambda: rp.HEART_VALUE.__setitem__(0, self._hv))

    def test_refuses_with_both_numbers_unset(self):
        rp.FAIRY_STOP[0] = None
        rp.HEART_VALUE[0] = None
        with self.assertRaises(rp.Unpriceable):
            rp.evaluate(_with_fairy("L3"), _zero_legs({*rp.CURRENT, "fairy_2C"}))

    def test_refuses_with_only_the_cost_measured(self):
        # The exact state PR #7 left itself in, had it credited anything: a cost with no
        # benefit to credit. This is the one that produced +4,994.
        rp.FAIRY_STOP[0] = 396
        rp.HEART_VALUE[0] = None
        with self.assertRaises(rp.Unpriceable) as cm:
            rp.evaluate(_with_fairy("L3"), _zero_legs({*rp.CURRENT, "fairy_2C"}))
        self.assertIn("no exchange rate between a heart and frames", str(cm.exception))

    def test_unpriceable_is_not_infeasible(self):
        # plan() swallows Infeasible deliberately. If Unpriceable were a subclass, a missing
        # measurement would hide behind a hundred silent candidate rejections.
        self.assertFalse(issubclass(rp.Unpriceable, rp.Infeasible))

    def test_prices_the_credit_once_both_numbers_exist(self):
        rp.FAIRY_STOP[0] = 396
        rp.HEART_VALUE[0] = 4000
        legs = _zero_legs({*rp.CURRENT, "fairy_2C"})
        base = rp.evaluate(rp.CURRENT, legs)
        with_heal = rp.evaluate(_with_fairy("L3"), legs)
        # zero legs, so the only movement is cost minus the one credit
        self.assertAlmostEqual(with_heal - base, 396 - 4000, places=6)

    def test_a_cheap_heal_can_come_out_ahead(self):
        # The property PR #7's model could never have: if the refill is worth more than
        # the stop costs, the stop wins. Before, the answer was the same for every value.
        legs = _zero_legs({*rp.CURRENT, "fairy_2C"})
        base = rp.evaluate(rp.CURRENT, legs)
        rp.FAIRY_STOP[0], rp.HEART_VALUE[0] = 396, 9000
        self.assertLess(rp.evaluate(_with_fairy("L3"), legs), base)
        rp.FAIRY_STOP[0], rp.HEART_VALUE[0] = 396, 100
        self.assertGreater(rp.evaluate(_with_fairy("L3"), legs), base)

    def test_explain_names_the_credit(self):
        rp.FAIRY_STOP[0], rp.HEART_VALUE[0] = 396, 4000
        _t, lines = rp.evaluate(_with_fairy("L3"), _zero_legs({*rp.CURRENT, "fairy_2C"}),
                                explain=True)
        self.assertTrue(any("credited for the refill" in ln for ln in lines),
                        f"the credit is not visible in the explanation:\n" + "\n".join(lines))


if __name__ == "__main__":
    unittest.main(verbosity=2)
