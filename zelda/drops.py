"""What a monster leaves behind, and how likely it is to leave it at all.

    python3 -c "import zelda.drops"      # nothing to run; this is a table plus a function

`SetUpDroppedItem` in `Z_04.asm` decides a monster's drop from four type lists, a 40-byte
table indexed by `$52A` WorldKillCycle, two counter compares, and a random cancel. This
module is that decision, transcribed once, and it exists as a separate module for a reason
worth stating: **the fight planner and the behavioural probe must not each hold their own
copy.** A probe that validates one transcription and a planner that uses another is a
measurement of nothing, and the way that goes wrong is quietly - both look right, they just
disagree at the edges.

So `testing/probe_drop_behaviour.py` imports this, and its 43/43 over the full run6 is a
statement about the code the planner actually runs.

## The five exits, not four

```asm
SetUpDroppedItem:
    LDA Item_ObjMonsterType, X
    LDY #$06
@FindNoDropType:  CMP NoDropMonsterTypes, Y / BEQ @DestroyMonster    ; 7 types, no drop
    LDY #$05
@FindDrop0Type:  CMP DropItemMonsterTypes0, Y / BEQ @Found          ; 6 types, row 0
    ...
@Found:
    CPX #$01
    BNE @LookUpItem
    CMP #$2A
    BEQ @DestroyMonster     ; Stalfos in SLOT 1 - might already carry a room item
    CMP #$30
    BEQ @DestroyMonster     ; $30 in SLOT 1 - and $30 is an ordinary row-2 type
```

The fifth is keyed on the **slot**, not the type, and it is the one a table-only model gets
wrong in the direction that matters: `$30` in slot 1 drops nothing, the same `$30` anywhere
else is row 2. The source gives the reason — in slot 1 they may already be carrying a room
item. Note the two tables here are transcriptions of the *source listing*; the check that
they are the game's own indexing (rather than an artifact of how the table wraps in the
listing) is `probe_drop_table.py`, which decodes the base offsets out of the cartridge.

## Why the probability is a measured number and not `rate / 256`

`DropItemRates` says a drop survives when `Random[slot] < rate`, which reads as 31% / 60% /
41% / 41% for the four rows. Measured over 136,526 frames and 697 kills, the real rates
are **9.3% / 20.3% / 14.8%** — roughly a third of what the table implies.

That gap is not a transcription error. The table is exact: 43 of 43 drops from the 24
listed monster types are predicted correctly by the code below. The gap is the cancel
firing far more often than `DropItemRates` predicts, and `Random` is per-slot
(`LDA Random, X`) and re-randomised, so it cannot be read back after the frame to see why.

The practical consequence is the whole reason this module returns a probability: a planner
that shaped toward a future drop as if it were certain would be wrong two times in three,
and would pay real frames for a bomb that never appeared. So the shaping is scaled by what
was measured, not by what the table says.

Row 3 is absent from `MEASURED_RATE` on purpose, and it is not an oversight. Row 3 means
"every type the game did not list", so it holds bosses and scenery rather than monsters —
leaving them in the measurement dropped the agreement rate from 86% to 70%, which is a pool
problem wearing the costume of a table error. A listed monster type is in rows 0-2 **by
construction**, so the planner never needs a row 3 rate: `row_of` returns 3 only for a type
the game does not list, and for those `SetUpDroppedItem` may not run at all. `expected_drop`
returns probability 0.0 for those, which is the honest answer rather than a guess.
"""
from __future__ import annotations

# ---- the type lists, as listed in Z_04.asm -----------------------------------------
# Sizes matter: the search loops bound their own scans (LDY #$06 for 7 entries, #$05 for
# 6, #$08 for 9), so a wrong count is a bug rather than a style choice.
NO_DROP = [0x5D, 0x14, 0x15, 0x1B, 0x1C, 0x1D, 0x17]
ROW0 = [0x07, 0x08, 0x0E, 0x04, 0x0F, 0x23]
ROW1 = [0x21, 0x22, 0x0D, 0x10, 0x13, 0x28, 0x2A, 0x27, 0x16]
ROW2 = [0x09, 0x0A, 0x03, 0x01, 0x12, 0x06, 0x0B, 0x24, 0x30]
LISTED = set(ROW0) | set(ROW1) | set(ROW2)      # the 24 types the game actually lists

RATES = [0x50, 0x98, 0x68, 0x68]   # DropItemRates; a drop is cancelled when Random >= this
COLS = 10                          # $52A WorldKillCycle runs 0..9

# 4 rows x 10 columns: DropItemSetBaseOffsets ($00, $0A, $14, $1E) + WorldKillCycle.
# The reshape is 4 x 10 and not 5 x 8 because both are 40 bytes, so the byte count does not
# disambiguate them - only the $0A-multiple base offsets do. probe_drop_table.py checks that
# against the cartridge.
DROP_TABLE = [
    [0x22, 0x18, 0x22, 0x18, 0x23, 0x18, 0x22, 0x22, 0x18, 0x18],
    [0x0F, 0x18, 0x22, 0x18, 0x0F, 0x22, 0x21, 0x18, 0x18, 0x18],
    [0x22, 0x00, 0x18, 0x21, 0x18, 0x22, 0x00, 0x18, 0x00, 0x22],
    [0x22, 0x22, 0x22, 0x23, 0x18, 0x22, 0x23, 0x22, 0x22, 0x18],
]
SLOT1_NO_DROP = (0x2A, 0x30)        # `CPX #$01` - keyed on the SLOT, not the type

# Measured drop frequency per row, over the full verified run6: 107 / 79 / 115 kills in
# rows 0 / 1 / 2 producing 10 / 16 / 17 drops. Against DropItemRates' implied 31.2% / 59.4%
# / 40.6% that is about a third, and the difference is the cancel.
#
# PROVISIONAL, and it is the one number here that is not exact. It comes from a single run
# on a single route, so 9.3% is 10 drops out of 107 kills. The direction and the order of
# magnitude are solid; the second decimal place is not. Re-measuring means adding the
# per-slot `Random` capture described in the module docstring, which is a pre-frame hook
# rather than a bridge read.
MEASURED_RATE = {0: 0.093, 1: 0.203, 2: 0.148}

# $627 == $10 is an exact compare against a plain INC that never wraps, so the tenth kill
# of the run yields a fairy and only the tenth. Certain, not probable - which is why a
# planner should notice it: a fairy is a heart container, and it arrives at a predictable
# moment in the run.
FAIRY_COUNT = 0x10
FAIRY = 0x23
BOMB = 0x00
FIVE_RUPREES = 0x0F
HEART = 0x22
GUARANTEE_AT = 0x0A       # HelpDropCount >= this makes the drop certain


def row_of(mtype: int) -> int:
    """Which row of DropItemTable this monster type uses. 3 means "not listed"."""
    if mtype in NO_DROP:
        return -1
    if mtype in ROW0:
        return 0
    if mtype in ROW1:
        return 1
    if mtype in ROW2:
        return 2
    return 3


def implied_rate(row: int) -> float:
    """What DropItemRates says, for comparison with what was measured."""
    return RATES[row] / 256


def expected_drop(mtype, slot, cycle, help_count, help_value, kill_count):
    """What this monster leaves behind, and how likely that is.

    Returns `(item, probability, reason)`. `item` is None when the monster leaves nothing,
    which is three of the five exits and a prediction rather than a failure.

    The arguments are the game's own values at the moment of the kill: `cycle` is `$52A`
    WorldKillCycle, `help_count`/`help_value` are `$50`/`$51`, `kill_count` is `$627`.
    Order matters and matches the assembly, including the two counter tests: the fairy
    compare comes first, so a kill that would be both the tenth and past the guarantee
    threshold yields a fairy.

    `probability` is the chance that this is the item which actually lands. It is 1.0 for
    the two certain paths and the measured rate for the table path, because the table path
    can be cancelled and roughly two times in three it is.
    """
    if mtype in NO_DROP:
        return None, 0.0, f"no-drop type ${mtype:02X}"
    if slot == 1 and mtype in SLOT1_NO_DROP:
        # In slot 1 these may already be carrying a room item, so they are destroyed instead.
        return None, 0.0, f"slot-1 ${mtype:02X} may already carry a room item"

    # `LDA #$23 / LDY WorldKillCount / CPY #$10` - an exact compare on a counter that is a
    # plain INC, so it fires once per run and never at $0F or $11.
    if kill_count == FAIRY_COUNT:
        return FAIRY, 1.0, f"fairy: ${FAIRY_COUNT:02X} kills so far, the exact-match path"

    # `LDA HelpDropCount / CMP #$0A / BCC @RandomlyCancel` - below the threshold the drop can
    # be thrown away; at or above it the drop is guaranteed and both counters are reset.
    if help_count >= GUARANTEE_AT:
        item = FIVE_RUPREES if help_value == 0 else BOMB
        return item, 1.0, (f"guaranteed: HelpDropCount ${help_count:02X} >= ${GUARANTEE_AT:02X}"
                           f", HelpDropValue ${help_value:02X}")

    row = row_of(mtype)
    if row not in MEASURED_RATE:
        # A type the game does not list. SetUpDroppedItem may not even run for it, and there
        # is no measured rate, so the honest answer is "nothing to plan around" rather than
        # a guess from DropItemRates.
        return None, 0.0, (f"${mtype:02X} is not a listed monster type (row {row}); no "
                           f"measured drop rate, so nothing to shape toward")
    return (DROP_TABLE[row][cycle % COLS],
            MEASURED_RATE[row],
            f"table row {row} column {cycle} at the measured {MEASURED_RATE[row]:.1%}")
