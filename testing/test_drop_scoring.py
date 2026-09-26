"""Targeted checks for fight-planner drop scoring helpers."""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)
del _os, _sys, _pathlib

from zelda.emulator import State
from zelda.lookahead import add_predicted_drops, drop_want, predicted_monster_drop


class _Emu:
    def __init__(self, max_bombs=8):
        self.max_bombs = max_bombs

    def byte(self, addr):
        assert addr == 0x67C
        return self.max_bombs


emu = _Emu()
full = State(hp=0x78, hpfrac=0, bombs=0, keys=0, rupees=10)
assert drop_want(0x19, full, emu) > drop_want(0x00, full, emu)
assert drop_want(0x19, State(hp=0x78, hpfrac=0, keys=3), emu) < drop_want(0x19, full, emu)
assert drop_want(0x18, full, emu, rupee_target=20) > drop_want(0x18, full, emu, rupee_target=10)
assert drop_want(0x0F, full, emu, rupee_target=20) > drop_want(0x0F, full, emu, rupee_target=10)

assert predicted_monster_drop(0x24, 0, 0, 0) == 0x00
assert predicted_monster_drop(0x24, 5, 0, 0) == 0x00
assert predicted_monster_drop(0x24, 7, 0, 0) == 0x00
assert predicted_monster_drop(0x24, 0, 0, 15) == 0x23
assert predicted_monster_drop(0x24, 0, 9, 0, False) == 0x0F
assert predicted_monster_drop(0x24, 0, 9, 0, True) == 0x00

drops = []
dead = add_predicted_drops(drops, [(3, 0x24, 88, 120, 1)], [], cycle=0)
assert dead and drops == [(0x00, 88, 120)]

drops = []
dead = add_predicted_drops(drops, [(1, 0x2A, 96, 120, 1)], [], item0=(0x19, 96, 120), item_carriers={1})
assert dead and drops == [(0x19, 96, 120)]

drops = []
dead = add_predicted_drops(drops, [(4, 0x30, 104, 136, 1)], [], clear_item=0x19, clear_ready=True, cycle=3)
assert dead and (0x19, 104, 136) in drops

drops = []
dead = add_predicted_drops(drops, [(3, 0x24, 88, 120, 1), (4, 0x24, 104, 120, 1)], [], cycle=0)
assert len(dead) == 2 and not drops

print("drop scoring helpers: ok")
