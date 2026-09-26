"""What each floor item is worth per pixel, and that a key beats a bomb when it is scarce.

    python3 testing/test_drop_want.py

Issue #6 found that `plan_fight` valued a key at 1.2 per pixel - less than a third of a
bomb - while the same file carried `sc -= 6000` for spending the wrong key. The cause was
not a judgement about keys. `want` was a heart-deficit rate, and everything that was not a
bomb or a heart fell through it unchanged.

These tests check the rates against **each other**, which is the only comparison that
survives someone retuning a constant. Asserting "a key is 6.0" would fail the next time
anyone has a reason to change it and teach nothing; asserting "a key you need outranks a
bomb you probably do not" is the property the issue actually asked for, and it holds for
any pair of constants that express it.

That framing is deliberate. A previous test in this repo asserted a delta equalled a
constant, which certified an omission as correct behaviour (see test_fairy_stops.py). A
test that pins a number pins a decision; a test that pins a relationship pins a reason.
"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)
del _os, _sys, _pathlib

import unittest
from types import SimpleNamespace

from zelda.lookahead import KEY_WANT_HELD, KEY_WANT_SCARCE, drop_want

# The item ids `drop_want` switches on, named here rather than in the scorer: these are
# the same ids as combat.py's DROPS table, and a test that reads them from the code it
# tests cannot catch the code renumbering itself.
BOMB, CLOCK, HEART, FAIRY, KEY, RUPEE, FIVE_RUPREES = 0x00, 0x21, 0x22, 0x23, 0x19, 0x18, 0x0F


def link(hearts=6, containers=6, bombs=8, keys=0, rupees=0):
    """Anything with the five fields `drop_want` reads. A State works; so does this."""
    return SimpleNamespace(hearts=hearts, containers=containers, bombs=bombs,
                           keys=keys, rupees=rupees)


def w(kind, s, max_bombs=8) -> float:
    """`drop_want`, asserted to be a rate. Most comparisons here are between two things
    that must be worth something; making that explicit beats casting at every call site."""
    v = drop_want(kind, s, max_bombs)
    assert v is not None, f"${kind:02X} was skipped for {s}, so it cannot outrank anything"
    return v



def _worth_on(cls, kind, s) -> bool:
    """`Fighter._worth` called unbound, with the smallest `self` it will accept.

    It only ever reads `self.emu.byte($67C)`, so a one-method stub is the whole dependency -
    and an unbound call keeps the test from needing a real Fighter or a running NES.
    """
    stub = SimpleNamespace(emu=SimpleNamespace(byte=lambda addr: 8))
    return bool(cls._worth(stub, kind, s))    # type: ignore[arg-type]


class AKeyIsWorthADoor(unittest.TestCase):
    """The acceptance criterion from #6: a key drop is valued above a bomb at keys == 0."""

    def test_a_needed_key_outranks_a_bomb(self):
        # bombs=4 is the honest comparison: a bomb below 4 gets a further +2.5 premium, and
        # bombs=8 would be skipped entirely at max_bombs, so neither would be a candidate.
        s = link(keys=0, bombs=4)
        self.assertGreater(w(KEY, s), w(BOMB, s))

    def test_a_needed_key_outranks_a_bomb_even_when_link_is_hurt(self):
        # At low health the heart-deficit term lifts every consumable, so this is the case
        # where a key used to lose. It should not: a key does not care how hurt Link is.
        s = link(keys=0, bombs=4, hearts=1, containers=6)
        self.assertGreater(w(KEY, s), w(BOMB, s))

    def test_a_bomb_still_wins_when_link_is_hurt_and_out_of_bombs(self):
        # The one case where a key loses, and it is deliberate rather than accidental.
        # Below 4 bombs a bomb carries a further +2.5, so a hurt Link with no bombs reaches
        # ~6.5 against a key's 6.0. A bomb prevents the damage that is already happening; a
        # key opens a door. If this ever inverts, the fix is to raise KEY_WANT_SCARCE and not
        # to delete this test - the boundary is a decision, not an accident.
        s = link(keys=0, bombs=0, hearts=1, containers=6)
        self.assertGreater(w(BOMB, s), w(KEY, s))

    def test_a_spare_key_is_worth_less_than_a_rupee_the_route_needs(self):
        # Holding keys, a key on the floor is a door that is already open.
        scarce, plenty = link(keys=0), link(keys=3)
        self.assertLess(w(KEY, plenty), w(RUPEE, scarce))
        self.assertLess(w(KEY, plenty), w(KEY, scarce))

    def test_key_worth_does_not_depend_on_health(self):
        # The property that makes a key a key. A heart-deficit rate cannot satisfy this.
        for h in (0, 1, 3, 6):
            self.assertEqual(w(KEY, link(keys=0, hearts=h)),
                             w(KEY, link(keys=0, hearts=0)),
                             f"a key's value moved with health at hearts={h}")


class RupeesArePricedAgainstWhatIsStillOwed(unittest.TestCase):
    def test_a_rupee_is_worth_more_when_the_route_is_short(self):
        broke, funded = link(rupees=0), link(rupees=255)
        self.assertGreater(w(RUPEE, broke), w(RUPEE, funded))

    def test_five_rupees_outrank_one(self):
        s = link(rupees=0)
        self.assertGreater(w(FIVE_RUPREES, s), w(RUPEE, s))

    def test_a_funded_rupee_is_worth_less_than_a_heart_container_worth_while_hurt(self):
        # The comparison that matters when Link is hurt and cannot afford to walk past
        # money: a heart beats a rupee he does not need.
        hurt_have_money = link(hearts=2, rupees=255)
        hurt_no_money = link(hearts=2, rupees=0)
        self.assertGreater(w(HEART, hurt_no_money), w(RUPEE, hurt_have_money))


class SkipsStillHold(unittest.TestCase):
    """The refactor moved these out of the scorer. Moving code is where skips get lost."""

    def test_a_heart_at_full_health_is_worthless(self):
        self.assertIsNone(drop_want(HEART, link(hearts=6, containers=6)))

    def test_a_heart_while_hurt_is_worth_walking_for(self):
        self.assertIsNotNone(drop_want(HEART, link(hearts=3, containers=6)))

    def test_a_fairy_at_full_health_is_worthless(self):
        self.assertIsNone(drop_want(0x23, link(hearts=6, containers=6)))

    def test_a_clock_is_never_worth_a_detour(self):
        self.assertIsNone(drop_want(CLOCK, link()))

    def test_a_bomb_at_max_bombs_cannot_be_taken(self):
        self.assertIsNone(drop_want(BOMB, link(bombs=8), 8))

    def test_a_bomb_below_max_bombs_is_worth_taking(self):
        self.assertIsNotNone(drop_want(BOMB, link(bombs=2), 8))

    def test_a_bomb_is_worth_more_when_link_is_short(self):
        # Level 9 stranded this run with zero bombs (the owner's rule).
        self.assertGreater(w(BOMB, link(bombs=0)), w(BOMB, link(bombs=7)))


class AKeyCannotComeFromAMonster(unittest.TestCase):
    """A guard on the premise, not on the code.

    KEY_WANT_SCARCE is calibrated as a single special case for a room item, which is only
    sound because a monster cannot drop one. If the drop table ever grows a $19, that
    calibration is wrong and this fails rather than the planner quietly mispricing every
    key in the game.
    """

    def test_the_confirmed_drop_table_contains_no_key(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "p", str(_ROOT / "testing" / "probe_drop_behaviour.py"))
        assert spec is not None and spec.loader is not None
        p = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(p)
        from_table = {v for row in p.DROP_TABLE for v in row}
        forced = {0x23, 0x0F, 0x00}          # fairy, five rupees, bomb
        self.assertNotIn(KEY, from_table | forced,
                         "a key is now droppable - KEY_WANT_SCARCE needs recalibrating")


class TheCollectorAndThePlannerAgree(unittest.TestCase):
    """Issue #6's other acceptance criterion, closed rather than asserted away.

    `_worth` decides whether to walk to something already on the floor; `drop_want` decides
    how much the fight should have been shaped toward it. They used to disagree: `_worth`
    returned True for a key unconditionally, so the collector would spend up to 120 pixels
    and 240 frames on a key the planner had valued below a bomb. The fix could have gone
    either way - raise the planner's key, or stop the collector chasing spare ones - and
    both were defensible in isolation.

    What is not defensible is leaving them disagreeing, because then whichever one is wrong
    the other will fight it at runtime and the symptom will look like a random detour. So
    this asserts the *relationship*: for every state, the collector takes a key exactly when
    the planner thinks one is worth taking. If someone retunes KEY_WANT_SCARCE, this is the
    test that notices the two have drifted apart again.
    """

    def _worth_key(self, s):
        from zelda.combat import Fighter
        return _worth_on(Fighter, KEY, s)

    def test_they_agree_about_a_key_in_every_state(self):
        # The relationship is not "the planner wants it" - a held key still rates 0.8, so
        # that is true in every state and would assert nothing. The relationship is that
        # both sides flip at the *same* threshold: the collector takes a key exactly when
        # the planner is giving it the scarce rate rather than the held rate. A spare key
        # is priced, and therefore travelled toward, just not chased.
        for keys in (0, 1, 2, 3, 8):
            for hearts, containers in ((6, 6), (1, 6), (0, 6)):
                for rupees in (0, 119, 120, 255):
                    s = link(hearts=hearts, containers=containers, bombs=4,
                             keys=keys, rupees=rupees)
                    planner_prices_it_as_scarce = w(KEY, s) == KEY_WANT_SCARCE
                    collector_takes_it = self._worth_key(s)
                    self.assertEqual(
                        planner_prices_it_as_scarce, collector_takes_it,
                        f"keys={keys} hearts={hearts}/{containers} rupees={rupees}: "
                        f"planner rates the key scarce={planner_prices_it_as_scarce} but "
                        f"the collector takes it={collector_takes_it}")

    def test_a_held_key_is_still_priced_just_not_chased(self):
        # The distinction the previous version of this test collapsed. KEY_WANT_HELD is 0.8,
        # not None: a spare key is worth a walk if Link is going that way anyway, and the
        # fight planner should still prefer ending near it. It is only the collector's
        # 120-pixel detour that is not worth spending.
        s = link(keys=3)
        self.assertEqual(w(KEY, s), KEY_WANT_HELD)
        self.assertGreater(w(KEY, s), 0)
        self.assertFalse(self._worth_key(s))

    def test_the_collector_still_takes_rupees_unconditionally(self):
        # Money is never refused. Only a key is scarce enough to be worth refusing, and
        # the planner agrees - a rupee is worth something at every rupee count.
        from zelda.combat import Fighter
        for rupees in (0, 120, 255):
            self.assertTrue(_worth_on(Fighter, RUPEE, link(keys=0, rupees=rupees)))
            self.assertTrue(_worth_on(Fighter, FIVE_RUPREES, link(keys=0, rupees=rupees)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
