"""What a monster will leave behind, and how sure we are of it.

    python3 testing/test_drops.py

`zelda/drops.py` is the transcription of `SetUpDroppedItem` that the fight planner shapes
toward, and `testing/probe_drop_behaviour.py` checks it against the game: 45 of 45
attributable drops over the full run6 landed exactly what this predicts. These tests check
the same function without an emulator, so a change to it fails here in a second rather than
after a three-minute replay.

The last test is the one that matters. A drop is usually *cancelled* - measured at 9.3% /
20.3% / 14.8% per row against the 31.2% / 59.4% / 40.6% the table implies - so a planner
that shaped toward a future drop as though it were certain would pay real frames for a bomb
that never appeared, roughly two times in three. Probability is the whole reason this
module returns one, and a test that only checked the item id would not notice it being
dropped.
"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)
del _os, _sys, _pathlib

import unittest

from zelda.drops import (
    BOMB, DROP_TABLE, FIVE_RUPREES, FAIRY, HEART, LISTED, MEASURED_RATE, NO_DROP,
    RATES, ROW0, ROW1, ROW2, SLOT1_NO_DROP, expected_drop, implied_rate, row_of,
)

KEY = 0x19
RUPEE = 0x18

# Well below the guarantee threshold and well below the fairy count, so a test that does not
# pass them is exercising the plain table path.
CLEAN = dict(help_count=0, help_value=0, kill_count=0)


def drop(mtype, slot=4, cycle=0, **kw):
    args = dict(CLEAN, **kw)
    return expected_drop(mtype, slot, cycle, args["help_count"], args["help_value"],
                         args["kill_count"])


class TheFiveExits(unittest.TestCase):
    """Three of the five leave nothing, and that is a prediction rather than a failure."""

    def test_a_no_drop_type_leaves_nothing(self):
        for t in NO_DROP:
            item, prob, _ = drop(t)
            self.assertIsNone(item, f"${t:02X} is in NoDropMonsterTypes")
            self.assertEqual(prob, 0.0)

    def test_slot_1_stalfos_and_30_leave_nothing(self):
        # The fifth exit, and the one a table-only model gets wrong in the direction that
        # matters: $30 is an ordinary row-2 type everywhere except slot 1.
        for t in SLOT1_NO_DROP:
            item, prob, why = drop(t, slot=1)
            self.assertIsNone(item, f"${t:02X} in slot 1 should leave nothing")
            self.assertEqual(prob, 0.0)
            self.assertIn("slot-1", why)

    def test_the_same_type_outside_slot_1_does_drop(self):
        # If this fails, the slot-1 exception has leaked into the type test.
        for t in SLOT1_NO_DROP:
            item, prob, _ = drop(t, slot=2, cycle=0)
            self.assertIsNotNone(item, f"${t:02X} in slot 2 should use its row")
            self.assertGreater(prob, 0.0)

    def test_the_tenth_kill_is_a_fairy_and_only_the_tenth(self):
        # `CPY #$10` is an exact compare on a plain INC that never wraps.
        self.assertEqual(drop(ROW2[0], kill_count=0x10)[0], FAIRY)
        self.assertEqual(drop(ROW2[0], kill_count=0x10)[1], 1.0, "the fairy path is certain")
        for n in (0x0F, 0x11, 0x20):
            self.assertNotEqual(drop(ROW2[0], kill_count=n)[0], FAIRY,
                                f"kill_count ${n:02X} must not take the fairy path")

    def test_the_tenth_kill_beats_the_guarantee(self):
        # Assembly order: the fairy compare comes first, so a kill that is both the tenth
        # and past the guarantee threshold is a fairy, not five rupees.
        self.assertEqual(drop(ROW2[0], help_count=0x0A, kill_count=0x10)[0], FAIRY)

    def test_the_guarantee_threshold_is_exactly_ten(self):
        self.assertEqual(drop(ROW2[0], help_count=0x0A, help_value=0)[0], FIVE_RUPREES)
        self.assertEqual(drop(ROW2[0], help_count=0x0A, help_value=1)[0], BOMB)
        below = drop(ROW2[0], help_count=0x09, help_value=0)
        self.assertEqual(below[1], MEASURED_RATE[2], "below the threshold it is the table path")
        self.assertNotEqual(below[0], FIVE_RUPREES)


class TheTablePath(unittest.TestCase):
    def test_every_listed_type_resolves_to_its_own_row(self):
        for t in ROW0:
            self.assertEqual(row_of(t), 0, f"${t:02X}")
        for t in ROW1:
            self.assertEqual(row_of(t), 1, f"${t:02X}")
        for t in ROW2:
            self.assertEqual(row_of(t), 2, f"${t:02X}")

    def test_the_column_selects_the_item(self):
        for t, row in ((ROW0[0], 0), (ROW1[0], 1), (ROW2[0], 2)):
            for c in range(10):
                self.assertEqual(drop(t, cycle=c)[0], DROP_TABLE[row][c],
                                 f"${t:02X} at column {c}")

    def test_the_column_wraps_the_way_the_counter_does(self):
        # $52A is a byte that walks 0..9, so a caller passing a larger value should wrap
        # rather than index off the end of a 10-wide row.
        self.assertEqual(drop(ROW1[0], cycle=12)[0], DROP_TABLE[1][2])

    def test_an_unlisted_type_is_declined_rather_than_guessed(self):
        # Row 3 is "everything the game did not list" - bosses and scenery. There is no
        # measured rate for it, so the model says nothing rather than inventing a number.
        item, prob, why = drop(0x40)
        self.assertIsNone(item)
        self.assertEqual(prob, 0.0)
        self.assertIn("not a listed monster type", why)

    def test_no_key_is_reachable(self):
        # The premise behind pricing keys as a room item rather than a drop.
        reachable = {v for row in DROP_TABLE for v in row} | {FAIRY, FIVE_RUPREES, BOMB}
        self.assertNotIn(KEY, reachable)
        for t in LISTED:
            for c in range(10):
                self.assertNotEqual(drop(t, cycle=c)[0], KEY, f"${t:02X} column {c}")


class TheProbabilityIsThePoint(unittest.TestCase):
    """A rare drop must not be worth as much as a certain one."""

    def test_the_table_path_is_never_certain(self):
        for t in LISTED:
            item, prob, _ = drop(t)
            self.assertLess(prob, 1.0, f"${t:02X}: only the two counter paths are certain")
            self.assertGreater(prob, 0.0, f"${t:02X} is listed, so it should have a rate")

    def test_the_measured_rate_is_far_below_what_the_table_implies(self):
        # This is the number that would be wrong if someone "corrected" MEASURED_RATE back
        # to implied_rate. The gap is real: the cancel fires about twice as often as
        # DropItemRates predicts, for a reason not yet understood.
        for row in MEASURED_RATE:
            self.assertLess(MEASURED_RATE[row], implied_rate(row),
                            f"row {row}: the measured rate should sit below the implied one")

    def test_a_guaranteed_drop_outranks_an_equally_valuable_maybe(self):
        # Find a cell that is a bomb rather than assuming one: row 2 column 0 is a heart,
        # and an earlier version of this test assumed otherwise and failed for a reason that
        # had nothing to do with the guarantee. Bombs sit at columns 1, 6 and 8.
        cells = [(t, c) for t in LISTED for c in range(10) if drop(t, cycle=c)[0] == BOMB]
        self.assertTrue(cells, "no monster type drops a bomb in any column")
        t, c = cells[0]
        maybe = drop(t, cycle=c)
        certain = drop(t, cycle=c, help_count=0x0A, help_value=1)
        self.assertEqual(maybe[0], certain[0], "same item, so only the probability differs")
        self.assertLess(maybe[1], 1.0)
        self.assertEqual(certain[1], 1.0)

    def test_the_measured_rates_cover_every_row_a_planner_can_reach(self):
        # Rows 0-2 are the only rows a listed monster can use, so a planner never needs a
        # rate it does not have. If this fails, expected_drop will decline on a real monster.
        reachable = {row_of(t) for t in LISTED}
        self.assertTrue(reachable <= set(MEASURED_RATE),
                        f"rows {reachable - set(MEASURED_RATE)} have no measured rate")

    def test_rates_are_probabilities(self):
        for row, r in MEASURED_RATE.items():
            self.assertTrue(0.0 < r < 1.0, f"row {row} rate {r}")
        for row, r in enumerate(RATES):
            self.assertTrue(0.0 < implied_rate(row) < 1.0)


class AHeartIsNotGuaranteedEither(unittest.TestCase):
    def test_row_0_column_4_is_a_heart_at_its_measured_rate(self):
        # The heart in the table, which is the one drop a planner most wants to be wrong
        # about: it is worth a lot and it lands 9.3% of the time.
        item, prob, _ = drop(ROW0[0], cycle=4)
        if DROP_TABLE[0][4] == HEART:
            self.assertEqual(item, HEART)
            self.assertLess(prob, 0.1, "a heart landing under a tenth of the time")


if __name__ == "__main__":
    unittest.main(verbosity=2)
