"""What killing things gets you, and how to ask for it.

One place for the drop table, because it was in three. The bomb steering in `lookahead.py` knew
`(0, 5, 7)` and a hand-copied `ROW2`; the clock steering in `combat.py` knew a second copy of the
same arithmetic; and the two were only ever checked against each other by a probe.

THE MECHANISM. `$52A` (WorldKillCycle) steps 0..9 on every kill, BEFORE the drop is chosen, and
the POST-kill value is the column. Measured on this cartridge, not read off a comment: one Blue
Darknut killed in L3 room 0x69 moved `$52A 05 -> 06` and dropped bombs, and row 2 column 6 is
bombs. `$50` is the kill streak, and a hit on Link resets it.

The direction of that rule is confirmed by code that already depended on it: `plan_fight` waits for
`$52A` in (0, 5, 7) so the next row-2 kill lands on column 1, 6 or 8 - which is exactly where row
2's bombs are. Pre-kill in, post-kill column.

Rows by monster type; row 3 is everything not listed. A drop is the table entry for
(row, column), and only happens when a random byte is under the row's rate: row 0 `0x50`/256,
row 1 `0x98`/256, rows 2-3 `0x68`/256. At `$50 == 9` the tenth kill is guaranteed instead - bombs if
it was killed by a bomb, else 5 rupees.
"""
from __future__ import annotations

KILL_CYCLE = 0x52A
STREAK = 0x50
HELP_COUNT = 10

ROWS = {
    0: {0x07, 0x08, 0x0E, 0x04, 0x0F, 0x23},
    1: {0x21, 0x22, 0x0D, 0x10, 0x13, 0x28, 0x2A, 0x27, 0x16},
    2: {0x09, 0x0A, 0x03, 0x01, 0x12, 0x06, 0x0B, 0x24, 0x30},
}
ROW3 = None                     # everything else; assigned below

BOMBS, CLOCK, HEART, FAIRY, RUPEE, FIVE_RUPEES, KEY = 0x00, 0x21, 0x22, 0x23, 0x18, 0x0F, 0x19

TABLE = {
    0: [HEART, RUPEE, HEART, RUPEE, FAIRY, RUPEE, HEART, HEART, RUPEE, RUPEE],
    1: [FIVE_RUPEES, RUPEE, HEART, RUPEE, FIVE_RUPEES, HEART, CLOCK, RUPEE, RUPEE, RUPEE],
    2: [HEART, BOMBS, RUPEE, CLOCK, RUPEE, HEART, BOMBS, RUPEE, BOMBS, HEART],
    3: [HEART, HEART, FAIRY, RUPEE, HEART, FAIRY, HEART, HEART, HEART, RUPEE],
}
RATES = {0: 0x50, 1: 0x98, 2: 0x68, 3: 0x68}

_TYPE_ROW = {t: r for r, ts in ROWS.items() for t in ts}
_eligible = set(_TYPE_ROW)
ROW3 = frozenset(range(0x100)) - _eligible

# Derived, not transcribed: ITEM_COLUMNS[item][row] = the SET of columns of that row yielding the
# item. Hand-copying "clock is row 1 column 6" into two files is how they drift.
#
# It has to be a set per row, not a single column. Bombs occur three times in row 2 (columns 1, 6
# and 8), and the first version of this collapsed them to whichever came last, so the bomb desire
# came out as "pre-kill 7" where the working code had always used (0, 5, 7). Nothing crashed; the
# planner just stopped steering for bombs on two of the three columns it used to.
ITEM_COLUMNS: dict[int, dict[int, set[int]]] = {}
for _row, _cols in TABLE.items():
    for _col, _item in enumerate(_cols):
        ITEM_COLUMNS.setdefault(_item, {}).setdefault(_row, set()).add(_col)


def row_of(monster_type: int) -> int:
    return _TYPE_ROW.get(monster_type, 3)


def rows_yielding(item: int) -> dict[int, set[int]]:
    """{row: columns} for `item`. Empty if no row can drop it."""
    return ITEM_COLUMNS.get(item, {})


def pre_kills_for(item: int) -> set[int]:
    """The `$52A` values which, if a monster of the right row dies next, produce `item`."""
    return {(col - 1) % 10 for cols in rows_yielding(item).values() for col in cols}


def chance(item: int) -> float:
    """Rough odds on one eligible kill, best row first."""
    best = min((RATES[r] for r in rows_yielding(item)), default=0)
    return best / 256


def prefer_target(emu, targets, item: int):
    """Order `targets` so the next kill is the one most likely to yield `item`.

    `targets` are `read_enemies` rows. Returns a new list, or None when there is nothing to steer
    towards - which is a real case, not a failure:

      * no row drops `item` at all;
      * no live enemy is in such a row;
      * every live enemy IS in such a row, so there is nothing left to advance the cycle with. That
        last gate is the `not all(ROW2 ...)` the bomb code already had, and it is load-bearing: you
        cannot spend four cycles burning monsters you do not have.

    When the next column is not the wanted one, an enemy OUTSIDE the wanted rows goes first, so the
    cycle advances on a monster whose own drop we do not need, and the eligible one is still alive
    when its column comes round.
    """
    # Set of monster TYPES, not row numbers. rows_yielding() is keyed by row, and comparing a
    # monster type against a row number is the kind of thing that type-checks perfectly and does
    # nothing: rows {1,2} matched Blue Lynel and Red Lynel and nothing else, so every room came back
    # with no eligible target and the few that "steered" steered on a Lynel.
    types = {t for r in rows_yielding(item) for t in ROWS[r]}
    if not types or not targets:
        return None
    elig = [t for t in targets if t[1] in types]
    other = [t for t in targets if t[1] not in types]
    if not elig or not other:
        return None
    # The check is on the PRE-kill $52A, because that is what pre_kills_for returns. Comparing
    # (c + 1) % 10 against it - the post-kill column - is off by one and disagreed with the bomb
    # code's own `(0, 5, 7)` in 16,530 of 40,890 cases.
    if emu.byte(KILL_CYCLE) in pre_kills_for(item):
        return elig + other            # the very next kill lands on it
    return other + elig                # burn a cycle on a monster we do not need
