"""Targeted checks for fight-planner drop scoring helpers."""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)
del _os, _sys, _pathlib

import unittest

from zelda.emulator import State
from zelda.lookahead import add_predicted_drops, drop_want, predicted_monster_drop


class _Emu:
    def __init__(self, max_bombs=8):
        self.max_bombs = max_bombs

    def byte(self, addr):
        assert addr == 0x67C
        return self.max_bombs


class DropScoringTests(unittest.TestCase):
    def setUp(self):
        self.emu = _Emu()
        self.full = State(hp=0x78, hpfrac=0, bombs=0, keys=0, rupees=10)

    def test_keys_beat_bombs_when_empty(self):
        self.assertGreater(drop_want(0x19, self.full, self.emu), drop_want(0x00, self.full, self.emu))

    def test_key_value_falls_with_spares(self):
        many = State(hp=0x78, hpfrac=0, keys=3)
        self.assertLess(drop_want(0x19, many, self.emu), drop_want(0x19, self.full, self.emu))

    def test_rupees_get_more_weight_when_short(self):
        self.assertGreater(drop_want(0x18, self.full, self.emu, rupee_target=20),
                           drop_want(0x18, self.full, self.emu, rupee_target=10))
        self.assertGreater(drop_want(0x0F, self.full, self.emu, rupee_target=20),
                           drop_want(0x0F, self.full, self.emu, rupee_target=10))

    def test_predicted_monster_drop_uses_cycle_and_forced_rules(self):
        self.assertEqual(predicted_monster_drop(0x24, 0, 0, 0), 0x00)
        self.assertEqual(predicted_monster_drop(0x24, 5, 0, 0), 0x00)
        self.assertEqual(predicted_monster_drop(0x24, 7, 0, 0), 0x00)
        self.assertEqual(predicted_monster_drop(0x24, 0, 0, 15), 0x23)
        self.assertEqual(predicted_monster_drop(0x24, 0, 9, 0, False), 0x0F)
        self.assertEqual(predicted_monster_drop(0x24, 0, 9, 0, True), 0x00)

    def test_predicted_drop_path_adds_future_monster_drop(self):
        drops = []
        dead = add_predicted_drops(drops, [(3, 0x24, 88, 120, 1)], [], cycle=0)
        self.assertEqual(len(dead), 1)
        self.assertEqual(drops, [(0x00, 88, 120)])

    def test_predicted_drop_path_preserves_carried_item(self):
        drops = []
        dead = add_predicted_drops(drops, [(1, 0x2A, 96, 120, 1)], [], item0=(0x19, 96, 120), item_carriers={1})
        self.assertEqual(len(dead), 1)
        self.assertEqual(drops, [(0x19, 96, 120)])

    def test_predicted_drop_path_adds_room_clear_item(self):
        drops = []
        dead = add_predicted_drops(drops, [(4, 0x30, 104, 136, 1)], [], clear_item=0x19, clear_ready=True, cycle=3)
        self.assertEqual(len(dead), 1)
        self.assertIn((0x19, 104, 136), drops)
        self.assertEqual(len(drops), 1)

    def test_predicted_drop_path_skips_multi_kill_guessing(self):
        drops = []
        dead = add_predicted_drops(drops, [(3, 0x24, 88, 120, 1), (4, 0x24, 104, 120, 1)], [], cycle=0)
        self.assertEqual(len(dead), 2)
        self.assertEqual(drops, [])


if __name__ == "__main__":
    unittest.main()
