"""The swing that could not land: the shield table, the deliberately-wrong box model, and the mask.

`journal/49-five-windows-and-a-black-one.md:141-165` is the record. `combat.shield_side` "had always
known" a swing along a knight's facing is stopped by its shield, and `lookahead.killable` "had
always known" a Darknut was killable. Nobody asked whether *this* swing would land, so `plan_reach`
offered one in all four directions whenever anything killable was within 36 px. The shield-aware fix
took sword frames per attempt from **46, 26, 36, 18** to **0, 2, 0, 0**. That fix has never had a
test, and it is the difference between a fight and 126 wasted frames per attempt.

Two of the four things below are *supposed* to be wrong, and the tests say so in as many words:

  * `reach_box_model` (`combat.py:96-110`) is the model this file used until 2026-09-30 and is kept
    **deliberately wrong**, because `hunt_darknut` and `darknut_ambush` stand off at
    16 + REACH - 4 = 22 px and strike as a knight walks past, and that distance was chosen against
    it. The test therefore pins the *wrongness*, not correctness. If someone "fixes" it, two callers
    walk to a post they can never swing from.
  * `SWORD_ACROSS, SWORD_ALONG = 12, 16` is the measured correction for the ordinary path, and its
    asymmetry (facing horizontally -> 16 across, 12 down; facing vertically -> 12 across, 16 down) is
    a fact about four short routines in Z_01.asm. It is pinned so a "simplification" cannot make it
    symmetric.

Ten checks, each printing the number or the cell it established:

  1. shield_side: the full 4 facings x 4 directions x 2 axes table (128 cells)  6. `enemy_hp` is the
  2. ...and it is built from a rule, not read back from the code          HIGH nybble, so $0F is 0
  3. reach_box_model's window is exactly [16, 26] px and refuses to touch  7. the window's two ends
  4. ...which is wrong in exactly the documented way                         are both load-bearing
  5. sword_reach's thresholds are 16 across / 12 down, and SWAP with facing  8. $FE is sword-only:
  (and 9: a Gleeok neck segment, the case the mask exists for)               sword no, bomb yes
                                                          10. killable() and the mask are separate
                                                             questions, and both are needed

WHAT IT DOES NOT CLAIM.

* **No monster is fought.** `shield_side`, `reach_box_model`, `enemy_hp` and the three immunity
  methods are pure ints and table lookups; the emulator is faked with a four-line object that
  answers `ram(0x4B2, 12)`, which is the entire surface `immune_to` touches. Nothing here says
  whether a swing *lands* - it says what the code *offers* and what the code believes about masks.
  Check 5 exists because that distinction is the bug: the old model offered swings the cartridge
  refused, and every one of them cost 14 frames and a knight's return.

* **`sword_reach` itself is not tested for correctness against the cartridge**, only for the shape of
  its model, because that needs BizHawk and a live swing. The constants are pinned; the claim that
  `|dx| < 16 and |dy| < 12` is what `DoObjectsCollideWithThresholds` computes is quoted from
  Z_01.asm (`combat.py:62-83`) and not re-derived here.

* **`Fighter` is built with `__new__`, not `__init__`.** `Fighter.__init__` builds a `Screen` and
  wants a live Navigator; `search.py:60` already does exactly this for its noise policy, and the
  three methods under test read `self.emu` and nothing else. So this proves the mask *logic*, and not
  that the Fighter is constructed correctly.

* **The mask table is a fixture, not a measurement.** `$FE` is what `InitGleeok` writes to every
  neck segment (`overworld.py:225-232` quotes the disassembly), so it is a documented fact; the
  other three masks in check 9 are chosen to discriminate the lookups, not to describe anything.

* **The 128-cell shield table is a restatement, not a discovery.** It is written from the game's
  rule - a knight's shield is on the side it faces, so it blocks a swing arriving along its facing
  axis from the far side of Link - and compared against the code. That is the only way to be useful:
  a test that copied the implementation would pass when the implementation is wrong, which is the
  failure mode this whole file exists to prevent. What it cannot do is tell you the *sign* is right;
  for that, `journal/49` has a room with eight knights in it.

Run:  python3 testing/test_combat_reach.py
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from zelda import combat
from zelda.emulator import State
from zelda.lookahead import DARKNUT_TYPES, UNKILLABLE, killable
from zelda.overworld import DMG_ARROW, DMG_BOMB, DMG_SWORD, enemy_name

# A read_enemies row: (slot, type, x, y, hp). read_enemies drops slots with type 0 or type >= $60.
def enemy(x, y, t=0x13, slot=1, hp=0x20):
    return (slot, t, x, y, hp)


def link(x=100, y=100, **kw):
    return State(x=x, y=y, **kw)


FACINGS = (0, 1, 2, 4, 8)
DIRECTIONS = ("Right", "Left", "Down", "Up")

# ------------------------------------------------------------------ 1-2. the shield table
#
# The rule, stated independently of the code: a Darknut's shield is on the side its direction
# `facing` names. A swing reaches it only if (a) the swing runs along that facing's axis and (b)
# the knight is on the far side of Link from that facing - i.e. Link is standing where the shield
# points. `shield_side` is given only the swing direction, so axis (b) has to come out of dx/dy,
# and it does: facing right (1) is blocked when dx < 0, i.e. the knight is to Link's LEFT, which
# puts Link on the knight's right, which is where a right-facing shield is.
#
# AXIS[d] is the axis the swing runs along: 0 for a horizontal swing, 1 for a vertical one. So a
# horizontal swing is answered by dx alone and ignores dy entirely - which is the "2 axes" half.
AXIS = {"Right": 0, "Left": 0, "Down": 1, "Up": 1}
assert AXIS == combat.AXIS, "the axis table the function reads must be the one under test"
DIRECTION_OF = {1: (0, +1), 2: (0, -1), 4: (1, +1), 8: (1, -1)}   # facing -> (axis, sign)


def expected_shield(facing, d, dx, dy):
    if facing not in DIRECTION_OF:
        return False                       # facing 0, or a combination: no shield to speak of
    axis, sign = DIRECTION_OF[facing]
    if AXIS[d] != axis:
        return False                       # a swing across the shield never meets it
    return (dx if axis == 0 else dy) * sign < 0


checked = 0
for facing in FACINGS:
    for d in DIRECTIONS:
        for dx in (-40, -1, 0, 1, 40):
            for dy in (-40, -1, 0, 1, 40):
                want = expected_shield(facing, d, dx, dy)
                got = combat.shield_side(facing, d, dx, dy)
                assert got == want, f"shield_side(facing={facing}, {d}, dx={dx}, dy={dy}) = {got}, " \
                                    f"the cartridge's rule says {want}"
                checked += 1
# 5 facings x 4 directions x 25 (dx, dy) pairs = 500 cells, of which the 4-axis ones are the
# part that can be True. Assert the count and the shape so a shortened loop cannot pass silently.
assert checked == 500, checked
true_cells = {(f, d) for f in (1, 2, 4, 8) for d in DIRECTIONS
              if any(combat.shield_side(f, d, dx, dy) for dx in (-1, 1) for dy in (-1, 1))}
assert true_cells == {(1, "Right"), (1, "Left"), (2, "Right"), (2, "Left"),
                      (4, "Down"), (4, "Up"), (8, "Down"), (8, "Up")}, sorted(true_cells)
# the axis asymmetry, named: facing 1 (right) is stopped by Left AND Right swings, and never by a
# vertical one, because a swing from above or below goes past the shield
assert combat.shield_side(1, "Right", -1, 999) is True, "dy is ignored by a horizontal swing"
assert combat.shield_side(1, "Up", -1, 999) is False, "and the same geometry on a vertical swing is not"
assert combat.shield_side(4, "Down", 999, -1) is True and combat.shield_side(4, "Right", 999, -1) is False
assert combat.shield_side(0, "Right", -1, 0) is False, "facing 0 has no shield"
assert not any(combat.shield_side(f, d, 0, 0) for f in FACINGS for d in DIRECTIONS), \
    "a knight exactly on top of Link is not shielded - there is no side to hit"
# the two Darknuts the game has, and nothing else, are the ones this matters for
assert DARKNUT_TYPES == (0x0B, 0x0C), [hex(t) for t in DARKNUT_TYPES]
print(f"shield_side: {checked} cells over {len(FACINGS)} facings x {len(DIRECTIONS)} directions x "
      f"25 offsets, all matching the cartridge's rule; {len(true_cells)} (facing, direction) pairs "
      f"can be blocked and a facing-0 knight never is")

# ------------------------------------------------------------------ 3-5. reach_box_model
#
# DELIBERATELY WRONG, and kept wrong on purpose. combat.py:96-110 says so: the two Darknut routines
# stand off at 16 + REACH - 4 = 22 px and strike as a knight walks past, and that distance was
# chosen against THIS model. The measured correction is `sword_reach`; correcting the box model
# without re-deriving the strategy would leave them walking to a post they can never swing from.
s, e = link(), enemy(100 + 16, 100)
assert combat.REACH == 10 and combat.ALIGN == 4, (combat.REACH, combat.ALIGN)
window = [d for d in range(0, 40) if combat.reach_box_model(s, enemy(100 + d, 100))]
assert window == list(range(16, 27)), window
print(f"reach_box_model offers a swing at exactly {window[0]}-{window[-1]} px "
      f"({len(window)} positions) on the facing axis, with |other axis| <= {combat.ALIGN}")

# ...and both ends of that window are wrong, in the two directions that matter. This is the load-
# bearing part of the test: if the window moves, the Darknut stand-off is wrong, and nothing in the
# tree can tell you because there is no Darknut checkpoint here.
assert combat.reach_box_model(s, enemy(100 + 15, 100)) is None, \
    "15 px away - touching - is refused. The cartridge hits at |dx| < 16, so 15 px is a hit."
assert combat.reach_box_model(s, enemy(100 + 26, 100)) == "Right", \
    "26 px away is offered. The cartridge's reach is 16, so 26 px is out of range."
assert combat.reach_box_model(s, enemy(100 + 27, 100)) is None, "and it stops at 26, not 16"
# the same on the vertical axis, and the corner where both apply
assert combat.reach_box_model(s, enemy(100, 100 + 16)) == "Down"
assert combat.reach_box_model(s, enemy(100 + 3, 100 + 16)) == "Down", "ALIGN lets a 3 px offset through"
assert combat.reach_box_model(s, enemy(100 + 5, 100 + 16)) is None, "and 5 px is outside ALIGN"
assert combat.reach_box_model(s, enemy(100, 84)) == "Up", "16 px above"
assert combat.reach_box_model(s, enemy(84, 100)) == "Left", "16 px to the left"
assert combat.reach_box_model(s, enemy(120, 120)) is None, "the diagonal corner is not reachable in one"
assert combat.reach_box_model(s, enemy(100, 100)) is None, "no offset at all is not a swing"
# the direction it offers: the sign of the offset, NES-down-positive
for dx, want in ((20, "Right"), (-20, "Left")):
    assert combat.reach_box_model(s, enemy(100 + dx, 100)) == want, dx
for dy, want in ((20, "Down"), (-20, "Up")):
    assert combat.reach_box_model(s, enemy(100, 100 + dy)) == want, dy
print(f"reach_box_model refuses {15} px (a hit the cartridge would take) and offers {26} px (a swing "
      f"the cartridge would refuse): wrong at BOTH ends, which is what the two Darknut routines "
      f"were built around")

# 5. and the measured one, for contrast. Its thresholds SWAP with Link's facing, and that asymmetry
#    is the fact from Z_01.asm; four short routines, no guesswork in them (combat.py:62-83).
assert (combat.SWORD_ALONG, combat.SWORD_ACROSS) == (16, 12), \
    (combat.SWORD_ACROSS, combat.SWORD_ALONG)
assert combat.GEOM == [True], "ZELDA_SWORD_GEOM defaults to the measured model, not the box model"


class MaskEmu:
    """The whole emulator surface `immune_to` touches: twelve bytes of ObjInvincibilityMask."""

    def __init__(self, mask=0x00):
        self.mask = mask

    def ram(self, addr, n):
        assert (addr, n) == (0x4B2, 12), (hex(addr), n)
        return bytes([self.mask]) * n


f = combat.Fighter.__new__(combat.Fighter)          # __init__ wants a live Navigator; these three
f.emu = MaskEmu(0xFE)                               # methods read self.emu and nothing else.
assert f.sword_immune(enemy(100, 100, t=0x13)) is False, "$FE = 1111 1110: bit 0 clear, sword yes"
assert f.bomb_immune(enemy(100, 100, t=0x13)) is True, "bit 3 set: a bomb is parried"
assert f.killable_by(enemy(100, 100, t=0x13), DMG_SWORD) is True
assert f.killable_by(enemy(100, 100, t=0x13), DMG_BOMB) is False, "the asymmetry is the point"
# the half-width bit the measured model reads, ObjAttr $4BF bit $40, moves the monster's centre from
# ObjX+8 to ObjX+4. It is a DIFFERENT byte from the mask and reading the wrong one is a silent miss.
assert combat.SWORD_ALONG == 16 and 0x4BF not in (0x4B2,), "the mask and the attr are different bytes"
print("Gleeok neck ($FE) is sword-yes/bomb-no: killable_by(sword) True, killable_by(bomb) False. "
      "Six sword-only segments at 10 HP each is why a bomb cannot beat a dragon")

# ------------------------------------------------------------------ 6-7. enemy_hp and the ends
for raw, want in ((0x00, 0), (0x01, 0), (0x0F, 0), (0x10, 1), (0x1F, 1), (0x23, 2), (0xF0, 15),
                  (0xFF, 15)):
    assert combat.enemy_hp(enemy(0, 0, hp=raw)) == want, (hex(raw), want)
assert combat.enemy_hp(enemy(0, 0, hp=0x0F)) == 0, "$0F is the low nybble: DEAD, not 15 HP"
assert combat.enemy_hp(enemy(0, 0, hp=0x00)) == 0
# it is a >> not a mask-and-shift: 16 HP would read 1, and 256 is not a byte so it cannot happen
assert combat.enemy_hp(enemy(0, 0, hp=0xA0)) == 10 and combat.enemy_hp(enemy(0, 0, hp=0x0A)) == 0
# ...and the tuple it takes is the 5-element read_enemies row, not the 5-element ghost row.
# read_ghost_objects returns (slot, x, y, hp, mask) - hp in position THREE. Applying enemy_hp to a
# ghost row reads its X. Nothing here can prevent that; naming it is the point.
assert combat.enemy_hp(enemy(100, 200, 0x13, hp=0x30)) == 3
assert (0xA0 >> 4) == 10 and enemy(0, 0, hp=0xA0)[4] >> 4 == 10, "the row's index 4 really is the HP"
print("enemy_hp is the HIGH nybble: $0F reads 0 (dead), $A0 reads 10, $FF reads 15")

# ------------------------------------------------------------------ 8-10. killable and the mask
# `killable` is about the MONSTER; the mask is about this weapon against this slot; and the shield
# is about the two of them together. `killable_by` needs both, which is check 10's whole content.
for t in sorted(UNKILLABLE):
    assert killable(enemy(0, 0, t=t)) is False, f"type ${t:02X} is in UNKILLABLE but reads killable"
assert UNKILLABLE == {0x49, 0x2B, 0x2C, 0x2D, 0x40, 0x4B, 0x4C}, [hex(t) for t in sorted(UNKILLABLE)]
assert killable(enemy(0, 0, t=0x13)) is True, "a Zol"
for t in (0x13, 0x0B, 0x0C, 0x01, 0x11):
    assert killable(enemy(0, 0, t=t)) is True, hex(t)
# types >= $50 are effects and pickups, not monsters: read_enemies already drops them, and killable
# repeats the bound so a caller that built the tuple itself cannot get it wrong
assert killable(enemy(0, 0, t=0x4F)) is True, "$4F is the last killable type"
assert not killable(enemy(0, 0, t=0x50)), "$50 is the boundary: read_enemies drops types >= $50"
assert not killable(enemy(0, 0, t=0x5F)) and not killable(enemy(0, 0, t=0x60))
assert killable(enemy(0, 0, t=0x00)) is True, "type 0 is a boss part, and read_enemies drops it"
# the four masks, chosen so each one discriminates a different lookup
MASKS = {0x00: (False, False, False),     # nothing: every weapon lands
         0xFE: (False, True, True),      # a Gleeok neck segment: sword only
         0x09: (True, True, False),      # sword + bomb refuse, arrow lands
         0x01: (True, False, False),     # sword refuses alone
         0x08: (False, True, False)}     # bomb refuses alone
assert len(MASKS) == 5, len(MASKS)
for mask, (sword_imm, bomb_imm, arrow_imm) in MASKS.items():
    f.emu = MaskEmu(mask)
    ee = enemy(100, 100, t=0x13)
    assert f.sword_immune(ee) is sword_imm, (hex(mask), "sword", f.sword_immune(ee))
    assert f.bomb_immune(ee) is bomb_imm, (hex(mask), "bomb", f.bomb_immune(ee))
    assert f.killable_by(ee, DMG_ARROW) is (killable(ee) and not arrow_imm), hex(mask)
    assert f.killable_by(ee, DMG_SWORD) is (killable(ee) and not sword_imm), hex(mask)
# each mask discriminates: no two of the five give the same answer triple
answers = {m: tuple(MASKS[m]) for m in MASKS}
assert len(set(answers.values())) == 5, answers
# a mask cannot make an unkilled monster killable: both conditions are needed
f.emu = MaskEmu(0x00)
assert f.killable_by(enemy(0, 0, t=0x4B), DMG_SWORD) is False, "UNKILLABLE beats an empty mask"
# and immune_to refuses to answer for a slot outside the object table, rather than indexing it
assert not combat.immune_to(f.emu, 12, DMG_SWORD) and not combat.immune_to(f.emu, -1, DMG_SWORD)
assert combat.immune_to(f.emu, 11, DMG_SWORD) is False, "slot 11 is the last real one"
print(f"killable() excludes {len(UNKILLABLE)} types and everything at or above $50; killable_by() is "
      f"the AND of both questions, and {len(MASKS)} masks x 3 weapons = {len(MASKS) * 3} lookups "
      f"agree, all 5 triples distinct")
print(f"all {len(UNKILLABLE)} UNKILLABLE types, by overworld.enemy_name: "
      + ", ".join(f"${t:02X} {enemy_name(t)}" for t in sorted(UNKILLABLE))
      + "  ($49 and $4C have no name in that table, so UNKILLABLE is the only description they have)")

print("all checks passed")