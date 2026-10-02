"""The drop table, its two derivations, and the steering that depends on them - with no kill in it.

`zelda/drops.py` exists because the drop table was in three files at once: `lookahead.py` hardcoded
`(0, 5, 7)` for bombs, `combat.py` kept a second copy of the same pre-kill arithmetic for the clock,
and the only thing that ever checked the two agreed was a probe. That is the module's whole reason
for being, and its whole risk: a table that is *derived* cannot drift, and a table that is *derived
from the wrong thing* drifts silently, which is what the first version of `ITEM_COLUMNS` did.

Nine checks, each printing the number or the set it established:

  1. bombs want pre-kill $52A in {0, 5, 7}            6. `prefer_target` never returns the whole room
  2. bombs come from row 2 columns 1, 6 and 8         7. the eligible-type set is TYPES, not rows
  3. ITEM_COLUMNS round-trips against TABLE            8. the wait-list is PRE-kill, off by one
  4. `row_of` covers all 256 types, rows {1,2} exact   9. the whole pre-kill/post-kill arithmetic
  5. `chance` is the BEST row's rate, not the average       shifts by -1 mod 10 and nothing else

Checks 1-3 exist because of a bug that already happened once, and the module's own docstring is
the record of it (drops.py:50-54). `ITEM_COLUMNS` has to be a set per row rather than a single
column because bombs occur three times in row 2. The first version collapsed them to whichever came
last, so the bomb desire came out as `pre-kill 7` where the working code had always used
`(0, 5, 7)`. Nothing crashed. The planner just stopped steering for bombs on two of the three
columns it used to. This file is the thing that would have caught that.

WHAT IT DOES NOT CLAIM.

* **The direction of the rule is a measurement, not a derivation, and cannot be checked here.**
  `$52A` steps 0..9 on every kill *before* the drop is chosen and the *post*-kill value is the
  column (drops.py:7-14). That is established by one Blue Darknut killed in L3 room 0x69 moving
  `$52A 05 -> 06` and dropping bombs - row 2, column 6 - which is the same fact the working code's
  `(0, 5, 7)` was built on. Nothing without the cartridge can re-measure it. What check 9 pins is
  the arithmetic *given* that direction, and check 1 pins the resulting set against the literal
  `(0, 5, 7)` that `lookahead.py` had always used. A sign error in `(col - 1)` would pass check 9
  and fail check 1, so check 1 is the one that matters; check 9 only proves the table is
  self-consistent.

* **The table's contents are transcribed, not decoded.** `TABLE`, `ROWS` and `RATES` are hand-typed
  from the cartridge. These tests check that everything *derived* agrees with them and that the
  documented per-row monster types are the ones in the file - not that row 2 really is the bomb row.

* **Nothing here observes a drop.** No kill, no `$52A`, no probability sample. `chance` is the
  rate table divided by 256, not a measured frequency, and these tests do not claim the rates are
  right - only that `chance` reads them the way its docstring says ("best row first", which means
  the minimum, which check 5 pins because picking the maximum is an equally plausible mistake).

* **`prefer_target` is tested with a two-line fake for the emulator**, because that is all it asks
  of one (`emu.byte(KILL_CYCLE)`). It does not claim that the resulting order is *good* steering -
  only that it is the order drops.py:81-113 says it is, including the two ways it is easy to get
  wrong.

* **The `lookahead` cross-checks at the end are import-level facts, not behaviour.** `ROW2` and
  `KILL_CYCLE`/`STREAK` are checked because a second copy of a constant is the exact bug this
  module was written to end; that they are the same object today is not evidence about tomorrow.

Run:  python3 testing/test_drops_table.py
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from zelda import drops, lookahead, ram

BOMBS, CLOCK, HEART, FAIRY, RUPEE, FIVE_RUPEES, KEY = (drops.BOMBS, drops.CLOCK, drops.HEART,
                                                       drops.FAIRY, drops.RUPEE,
                                                       drops.FIVE_RUPEES, drops.KEY)

# ------------------------------------------------------------------ 1. the bomb wait-list
#
# (0, 5, 7), not (7,). This is the literal the working code had always used, and the literal the
# collapsed three-column version lost. One assert, guarding a bug that has already happened once.
pre = drops.pre_kills_for(BOMBS)
assert pre == {0, 5, 7}, f"bomb pre-kill wait-list is {sorted(pre)}, not the working code's (0, 5, 7)"
assert len(pre) == 3, pre
print(f"bombs: pre-kill $52A in {sorted(pre)}  (3 values, from {len(drops.rows_yielding(BOMBS)[2])} columns)")

# and it is a set of small ints in 0..9, which is what "$52A steps 0..9" means
for item in (BOMBS, CLOCK, HEART, FAIRY, RUPEE, FIVE_RUPEES, KEY):
    p = drops.pre_kills_for(item)
    assert p <= set(range(10)), (item, p)
    assert all(isinstance(v, int) for v in p), (item, p)

# ------------------------------------------------------------------ 2. the same fact one layer down
cols = drops.rows_yielding(BOMBS)
assert cols == {2: {1, 6, 8}}, cols
assert set(cols) == {2}, f"bombs are a row-2 drop; rows {sorted(cols)} is a transcription error"
print(f"bombs: row 2 only, columns {sorted(cols[2])}")

# print the whole table, once per item, so the reader sees all of it
by_item = {i: drops.rows_yielding(i) for i in (BOMBS, CLOCK, HEART, FAIRY, RUPEE, FIVE_RUPEES, KEY)}
for i, r in by_item.items():
    print(f"  {i:#04x}: rows " + " ".join(f"{row}:{{{','.join(str(c) for c in sorted(cs))}}}"
                                          for row, cs in sorted(r.items()))
          + f"   pre-kill {sorted(drops.pre_kills_for(i))}   chance {drops.chance(i):.5f}")

# every item the table can produce is reachable by rows_yielding, and vice versa
produced = {it for row in drops.TABLE.values() for it in row}
assert produced == set(drops.ITEM_COLUMNS), (sorted(produced), sorted(drops.ITEM_COLUMNS))
assert len(produced) == 6, sorted(produced)
# KEY appears in no row at all, so it can never be steered for
assert KEY not in produced and drops.pre_kills_for(KEY) == set(), "a key is not a kill drop"
print(f"{len(produced)} distinct items are droppable (the key is not one of them), so "
      f"pre_kills_for(KEY) is empty and prefer_target(KEY) has nothing to aim at")

# ------------------------------------------------------------------ 3. the derivation round-trips
#
# ITEM_COLUMNS is built from TABLE by a comprehension, so this check is nearly tautological - and
# that is the point. The bug drops.py:50-54 records was in *that comprehension* (it collapsed a set
# to one column). A round-trip check is what fails when the comprehension is changed to something
# else, and it also fails if anyone hand-adds an entry to ITEM_COLUMNS that TABLE does not support.
for row, columns in drops.TABLE.items():
    assert len(columns) == 10, (row, columns)              # ten kill-cycle columns, always
    for col, item in enumerate(columns):
        assert col in drops.ITEM_COLUMNS.get(item, {}).get(row, set()), (row, col, item)
for item, byrow in drops.ITEM_COLUMNS.items():
    for row, cs in byrow.items():
        assert cs, f"{item:#04x} row {row} has an empty column set"
        for col in cs:
            assert drops.TABLE[row][col] == item, f"ITEM_COLUMNS says {item:#04x} at {row}/{col}, " \
                                                  f"TABLE says {drops.TABLE[row][col]:#04x}"
# the multiplicity that was collapsed. bombs occur THREE times in row 2, and a single-column-per-row
# version of ITEM_COLUMNS would turn that into one value - which is the bug drops.py:50-54 records.
# The numbers below are the shape of the whole table, so the reader can see 3 is not the maximum
# fan-out: hearts appear in every row and six times in row 3.
fanout = {i: [len(cs) for cs in byrow.values()] for i, byrow in drops.ITEM_COLUMNS.items()}
assert fanout[BOMBS] == [3], fanout
assert len(drops.pre_kills_for(BOMBS)) == 3, \
    "a single-column-per-row ITEM_COLUMNS collapses bombs' three columns to one wait value"
assert sum(fanout[HEART]) == 15 and len(drops.pre_kills_for(HEART)) == 9, (fanout[HEART],)
print("ITEM_COLUMNS agrees with TABLE in both directions. Columns per item per row: "
      + ", ".join(f"{i:#04x}:{f}" for i, f in sorted(fanout.items()))
      + "  (bombs 3 in row 2; hearts 15 across four rows, 9 distinct wait values)")

# ------------------------------------------------------------------ 4. row_of
# ROWS holds only the three listed rows; row 3 is the separate `ROW3` frozenset that row_of's
# fallback of 3 names, so the two have to be checked against each other rather than assumed.
assert set(drops.ROWS) == {0, 1, 2}, sorted(drops.ROWS)
assert all(drops.ROWS[r] for r in (0, 1, 2)), "no listed row may be empty"
assert len(drops.TABLE) == 4 and set(drops.TABLE) == set(drops.RATES), sorted(drops.TABLE)
for r, types in drops.ROWS.items():
    for t in types:
        assert drops.row_of(t) == r, (hex(t), drops.row_of(t), r)
        assert drops.ROW3.isdisjoint(drops.ROWS[r]), f"type {t:#04x} is in two rows"
assert len(drops.ROW3) == 0x100 - sum(len(v) for v in drops.ROWS.values()), len(drops.ROW3)
assert drops.ROW3 == frozenset(range(0x100)) - set(drops._TYPE_ROW), "ROW3 is everything not listed"
# rows 1 and 2 happen to be the same size (9 each) and row 0 is 6, so a row mix-up in a place that
# compares sizes would be silent. Pin the sizes so that changes are visible.
assert [len(drops.ROWS[r]) for r in (0, 1, 2)] == [6, 9, 9], [len(drops.ROWS[r]) for r in (0, 1, 2)]
# rows {1, 2} - the ROW NUMBERS - name Blue and Red Lynel and nothing else. This is the bug:
# comparing a monster TYPE against a row number type-checks perfectly and does nothing, and it is
# what the comment at drops.py:99-100 is warning about. Asserting it here makes the coincidence
# visible rather than leaving it to be rediscovered.
assert drops.row_of(0x01) == 2 and drops.row_of(0x02) == 3, \
    "the row numbers 1 and 2 are the types Blue Lynel (01) and Red Lynel (02); if that ever stops " \
    "being true the comment at drops.py:99-100 is describing a different coincidence"
assert drops.row_of(0x11) == 3, "the Zora is in no listed row"
print(f"row_of: {len(drops.ROWS[0])}+{len(drops.ROWS[1])}+{len(drops.ROWS[2])} listed types, "
      f"{len(drops.ROW3)} in row 3, all 256 accounted for; row_of(01)={drops.row_of(0x01)} "
      f"row_of(02)={drops.row_of(0x02)} row_of(11)={drops.row_of(0x11)}")

# ------------------------------------------------------------------ 5. chance
assert drops.RATES == {0: 0x50, 1: 0x98, 2: 0x68, 3: 0x68}, drops.RATES
assert drops.chance(BOMBS) == 0x68 / 256 == 0.40625, drops.chance(BOMBS)
assert drops.chance(HEART) == 0x50 / 256 == 0.3125, drops.chance(HEART)
assert drops.chance(FIVE_RUPEES) == 0x98 / 256 == 0.59375, drops.chance(FIVE_RUPEES)
assert drops.chance(KEY) == 0.0, "min() of nothing is 0, not a crash"
# "best row first" means the MINIMUM rate, and two items discriminate it from the maximum:
#   CLOCK  drops from rows 1 (0x98) and 2 (0x68) -> min 0.68, max 0.98
#   FAIRY  drops from rows 0 (0x50) and 3 (0x68) -> min 0.50, max 0.68
# The clock is the interesting one: row 1 is where the clock lives (Ghini, Zol, Stalfos - the
# families that fill rooms, combat.py:30-35) but row 2's rate is the better one, so "best row" is
# not "the row the item is associated with".
assert sorted(drops.rows_yielding(CLOCK)) == [1, 2] and drops.chance(CLOCK) == 0x68 / 256, \
    "the clock's best row is row 2 at 0x68, not row 1 at 0x98"
assert sorted(drops.rows_yielding(FAIRY)) == [0, 3] and drops.chance(FAIRY) == 0x50 / 256, \
    "fairies: row 0's 0x50 beats row 3's 0x68"
# every row a drop can come from must be a key of RATES, or chance() raises on the min()
for item in by_item:
    assert set(drops.rows_yielding(item)) <= set(drops.RATES), item
assert set(drops.TABLE) == set(drops.RATES), "TABLE and RATES must agree on which rows exist"
print(f"chance pins RATES={ {k: hex(v) for k, v in drops.RATES.items()} } and takes the MIN: "
      f"bombs {drops.chance(BOMBS):.5f}, clock {drops.chance(CLOCK):.5f} (row 2's 0x68 beats "
      f"row 1's 0x98), heart {drops.chance(HEART):.5f}, key {drops.chance(KEY):.5f}")

# ------------------------------------------------------------------ 6-8. prefer_target
class Cycle:
    """The whole emulator surface drops.prefer_target touches: one byte, at $52A."""
    def __init__(self, v):
        self.v = v

    def byte(self, addr):
        assert addr == drops.KILL_CYCLE, f"prefer_target read {addr:#06x}, not the kill cycle"
        return self.v


# read_enemies rows: (slot, type, x, y, hp). One of every kind of interesting case:
# a row-2 type (the bomb row), a row-1 type, a row-0 type, and Red Lynel 02 - which is NOT in any
# drop row, so it must be an "other".
BLUE_LYNEL, ZOL, RED_LYNEL, RED_MOBLIN = 0x01, 0x13, 0x02, 0x04
TARGETS = [(1, BLUE_LYNEL, 0, 0, 0x20), (2, ZOL, 0, 0, 0x20),
           (3, RED_LYNEL, 0, 0, 0x20), (4, RED_MOBLIN, 0, 0, 0x20)]
ELIGIBLE_TYPES = set(drops.ROWS[2])                 # what rows {2} really means
INELIGIBLE = {ZOL, RED_LYNEL, RED_MOBLIN}
assert {t[1] for t in TARGETS} - ELIGIBLE_TYPES == INELIGIBLE, \
    "this fixture stopped discriminating between 'type set' and 'row numbers {1,2}'"

# 7. the eligible set is monster TYPES. If it were the row numbers {1,2} then Red Lynel (02) would
#    be treated as an eligible bomb-row monster and Zol (13) would not be.
assert ELIGIBLE_TYPES != {1, 2}, "the two candidate readings have converged; this fixture is dead"
assert BLUE_LYNEL in ELIGIBLE_TYPES and RED_LYNEL not in ELIGIBLE_TYPES, sorted(ELIGIBLE_TYPES)

# 8. the check is on the PRE-kill cycle. `pre_kills_for` says {0,5,7}; the post-kill columns are
#    {1,6,8}. The two sets are DISJOINT, so using one where the other belongs is wrong on 6 of the
#    10 cycle values - not a subtle disagreement. (drops.py:109-110 measures the same off-by-one
#    disagreeing with the bomb code's own (0, 5, 7) in 16,530 of 40,890 cases, 40%.)
POST = {1, 6, 8}
assert pre == {(c - 1) % 10 for c in POST}, (sorted(pre), sorted(POST))
assert pre & POST == set(), "pre-kill and post-kill must not overlap, or the off-by-one is invisible"
assert len(pre | POST) == 6 and set(range(10)) - (pre | POST) == {2, 3, 4, 9}, sorted(pre | POST)
order_pre_first, order_other_first = [], []
for cycle in range(10):
    out = drops.prefer_target(Cycle(cycle), TARGETS, BOMBS)
    assert out is not None and len(out) == len(TARGETS), (cycle, out)   # a permutation, never None
    (order_pre_first if cycle in pre else order_other_first).append((cycle, tuple(t[1] for t in out)))
assert len(order_pre_first) == 3 and len(order_other_first) == 7, (len(order_pre_first),)
for cycle, types in order_pre_first:
    assert types[0] == BLUE_LYNEL and set(types[1:]) == INELIGIBLE, (cycle, types)
for cycle, types in order_other_first:
    assert types[-1] == BLUE_LYNEL and set(types[:-1]) == INELIGIBLE, (cycle, types)
print(f"bomb steering: $52A in {sorted(pre)} -> kill the row-2 monster first; "
      f"the other {len(order_other_first)} values -> burn a cycle on Zol/Red Lynel/Red Moblin first")

# 6. it declines in all three of the ways its docstring lists, and returns None each time
assert drops.prefer_target(Cycle(0), [], BOMBS) is None, "no live enemies"
assert drops.prefer_target(Cycle(0), TARGETS, KEY) is None, "no row drops a key"
assert drops.prefer_target(Cycle(0), [t for t in TARGETS if t[1] in ELIGIBLE_TYPES], BOMBS) is None, \
    "every live enemy is in the wanted row: there is nothing left to advance the cycle with"
assert drops.prefer_target(Cycle(0), [t for t in TARGETS if t[1] not in ELIGIBLE_TYPES], BOMBS) is None, \
    "no live enemy is in a wanted row"
# ...and it does not mutate the list it was handed
before = list(TARGETS)
drops.prefer_target(Cycle(0), TARGETS, BOMBS)
assert TARGETS == before, "prefer_target reordered the caller's list"
print("prefer_target returns None for: no targets, an undroppable item, all-eligible, none-eligible "
      "(4 cases) and leaves the caller's list alone")

# ------------------------------------------------------------------ 9. the arithmetic, whole table
for item, byrow in by_item.items():
    post = {c for cs in byrow.values() for c in cs}
    shifted = {(c - 1) % 10 for c in post}
    assert drops.pre_kills_for(item) == shifted, (hex(item), sorted(post), sorted(drops.pre_kills_for(item)))
    assert not (drops.pre_kills_for(item) & set(range(10)) - shifted), item
assert drops.HELP_COUNT == 10 and drops.STREAK == 0x50 and drops.KILL_CYCLE == 0x52A, \
    "the at-$50 streak and the $52A cycle the ten columns are named for"
# $52A is a bus address outside work RAM; $50 is work RAM and is the same byte ram.KILL_TALLY names.
assert drops.STREAK == ram.KILL_TALLY == 0x50, "two names for $50 must agree or one of them is a typo"
print("pre-kill == post-kill shifted by -1 mod 10 for all "
      f"{len(produced)} droppable items; KILL_CYCLE=${drops.KILL_CYCLE:04X} "
      f"STREAK=${drops.STREAK:02X} == ram.KILL_TALLY")

# ------------------------------------------------------------------ one table, not three
assert lookahead.ROW2 is drops.ROWS[2], "lookahead.py must alias drops.ROWS[2], not copy it"
assert lookahead.BOMB_TARGET == [6], lookahead.BOMB_TARGET
assert set(drops.ROWS[2]) == {1, 3, 6, 9, 10, 11, 18, 36, 48}, sorted(drops.ROWS[2])
print("lookahead.ROW2 IS drops.ROWS[2] (same object), 9 monster types: "
      + ", ".join(f"{t:#04x}" for t in sorted(drops.ROWS[2])))

print("all checks passed")