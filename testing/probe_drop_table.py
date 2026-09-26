"""Decode the monster drop table out of the cartridge, and check the shape.

    python3 testing/probe_drop_table.py

Monster drops are decided in `SetUpDroppedItem` (Z_04.asm). Four tables decide
what a given monster gives:

    NoDropMonsterTypes        7 types that drop nothing
    DropItemMonsterTypes0     6 types -> row 0
    DropItemMonsterTypes1     9 types -> row 1
    DropItemMonsterTypes2     9 types -> row 2
                              everything else -> row 3

and the item comes from a 40-byte table indexed by row base + $52A WorldKillCycle.
`$52A` walks 0..9, so each row is 10 wide, and the row bases are multiples of $0A:

```asm
; Multiples of $A to index the base of each row of items in DropItemTable.
DropItemSetBaseOffsets:
    .BYTE $00, $0A, $14, $1E
```

**The trap, and it is a real one.** The disassembly *lists* the table wrapped
eight bytes to a line, which reads as 5 rows of 8:

```asm
DropItemTable:
    .BYTE $22, $18, $22, $18, $23, $18, $22, $22      <- 5 rows of 8? no
    .BYTE $18, $18, $0F, $18, $22, $18, $0F, $22
    .BYTE $21, $18, $18, $18, $22, $00, $18, $21
    .BYTE $18, $22, $00, $18, $00, $22, $22, $22
    .BYTE $23, $18, $22, $23, $22, $22, $22, $18
```

5 x 8 and 4 x 10 are both 40 bytes, so the byte count does not disambiguate them -
only the base offsets do. Read the wrong way, row 1 comes out as
`18 18 0F 18 22 18 0F 22 21 18` and every item after the eighth is off by two
positions. This is the single easiest thing to get wrong when transcribing the
table, and it is why the reshape is done from the base offsets below rather than
from how the source is wrapped.

## What this does and does not prove

It proves the transcription, and it is the citation `zelda/lookahead.py` should be
carrying for `DROP_TABLE`, `NO_DROP`, `ROW0`, `ROW1` and `ROW2`.

It does **not** prove the table describes what the game does. The remaining check
is behavioural, and it is the one this repo's own rule demands: kill a known
monster at a known `$52A` and see what lands. See issue #6. Reading a table out of
the cartridge tells you what the code says; only a kill tells you what happens.

The forced drops are the other half, and they are three comparisons rather than a
table - see FORCED below and issue #6, which carries each one with its address.
"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/ are repo-relative
del _os, _sys, _pathlib

from pathlib import Path

from zelda.emulator import ROM

PRG = 0x10          # a 16-byte iNES header, so PRG starts here
COLS = 10           # $52A WorldKillCycle runs 0..9
ROWS = 4

# The type tables, as listed in Z_04.asm. Sizes matter: the search loops bound their
# own scans (LDY #$06 for 7 entries, #$05 for 6, #$08 for 9), so a wrong count is a bug
# rather than a style choice.
NO_DROP = [0x5D, 0x14, 0x15, 0x1B, 0x1C, 0x1D, 0x17]
ROW0 = [0x07, 0x08, 0x0E, 0x04, 0x0F, 0x23]
ROW1 = [0x21, 0x22, 0x0D, 0x10, 0x13, 0x28, 0x2A, 0x27, 0x16]
ROW2 = [0x09, 0x0A, 0x03, 0x01, 0x12, 0x06, 0x0B, 0x24, 0x30]
BASE_OFFSETS = [0x00, 0x0A, 0x14, 0x1E]      # multiples of $0A
RATES = [0x50, 0x98, 0x68, 0x68]              # a drop is cancelled at Random >= this

# What the forced rules actually are, read off SetUpDroppedItem (Z_04.asm). The two
# decisions that matter for a planner, both of which were got wrong in PR #12:
#   - the fairy is $627 == $10 EXACTLY, once, because WorldKillCount is a plain INC
#     with no wrap. Not "every 10 after 15".
#   - the tenth kill is $50 >= $0A, and the item is read from $51, which counts bomb
#     kills since the counter maxed - not from whether this kill was a bomb.
FORCED = """
  $627 == $10 exactly            -> $23 fairy          (one compare, CPY #$10; $627 never wraps)
  $50 >= $0A and $51 == 0        -> $0F five rupees    (HelpDropValue picks: 0 = rupees)
  $50 >= $0A and $51 != 0        -> $00 bomb
  otherwise                      -> the table row
  ... and below $0A a drop is CANCELLED when Random >= DropItemRates[row]
      $50 / $98 / $68 / $68, so rows 0 and 2-3 drop about 31% and 41% of the time.
      The guarantee path skips the cancel, which is what the guarantee is for.
"""


def find(hay: bytes, needle: bytes, what: str) -> int:
    """Byte offset of `needle`, or raise. Searching for what we expect to find is not a
    proof on its own - which is why the reshape below is checked against the base
    offsets, and why the behavioural test is still outstanding."""
    i = hay.find(needle)
    if i < 0:
        raise SystemExit(f"could not locate {what} in the cartridge")
    return i


def main() -> int:
    rom = Path(ROM).read_bytes()
    prg = rom[PRG:]

    flat = bytes([0x22, 0x18, 0x22, 0x18, 0x23, 0x18, 0x22, 0x22,
                  0x18, 0x18, 0x0F, 0x18, 0x22, 0x18, 0x0F, 0x22,
                  0x21, 0x18, 0x18, 0x18, 0x22, 0x00, 0x18, 0x21,
                  0x18, 0x22, 0x00, 0x18, 0x00, 0x22, 0x22, 0x22,
                  0x23, 0x18, 0x22, 0x23, 0x22, 0x22, 0x22, 0x18])
    off = find(prg, flat, "DropItemTable")

    # The source declares the base offsets and the rates BEFORE the table, and the
    # assembler emits in source order, so in the cartridge they precede it. The first
    # version of this looked after the table and correctly refused to reshape on a guess.
    before = prg[max(0, off - 96):off]
    found_bases = None
    for k in range(len(before) - len(BASE_OFFSETS), -1, -1):
        if list(before[k:k + len(BASE_OFFSETS)]) == BASE_OFFSETS:
            found_bases = (max(0, off - 96) + k, True)
            break
    print(f"cartridge     : {ROM}")
    print(f"DropItemTable : prg ${off:05X}  ({len(flat)} bytes)")
    if found_bases is None:
        print(f"  could not find {['$%02X' % b for b in BASE_OFFSETS]} in the 96 bytes before "
              f"the table. The reshape below would be a guess, not a decode. Stopping.")
        return 1
    print(f"base offsets  : prg ${found_bases[0]:05X}  "
          + " ".join(f"${b:02X}" for b in BASE_OFFSETS)
          + "   (declared before the table in the source, emitted before it in the ROM)")
    print("  the $0A-multiple bases are present, so 4 rows x 10 columns is the game's "
          "own indexing\n  and not an artefact of how the source happens to wrap.\n")

    rows = [list(flat[r * COLS:(r + 1) * COLS]) for r in range(ROWS)]
    print("DropItemTable, reshaped by the base offsets (column = $52A WorldKillCycle):")
    print("        " + " ".join(f"  c{c}" for c in range(COLS)))
    for r, row in enumerate(rows):
        print(f"  row {r}  " + " ".join(f" {x:02X}" for x in row))

    for r in range(ROWS):
        assert len(rows[r]) == COLS

    # The type tables, located by their own contents.
    print()
    for name, vals in (("NoDropMonsterTypes", NO_DROP), ("DropItemMonsterTypes0", ROW0),
                       ("DropItemMonsterTypes1", ROW1), ("DropItemMonsterTypes2", ROW2)):
        o = find(prg, bytes(vals), name)
        print(f"{name:22s} prg ${o:05X}  n={len(vals)}  "
              + " ".join(f"{v:02X}" for v in vals))
    o = find(prg, bytes(RATES), "DropItemRates")
    # `LDA Random, X / CMP DropItemRates[row] / BCS @DestroyMonster` - so a drop SURVIVES
    # when Random < rate, and Random is a byte. The rate is a fraction of 256, not of 100.
    print(f"{'DropItemRates':22s} prg ${o:05X}  n={len(RATES)}  "
          + " ".join(f"{v:02X}" for v in RATES)
          + "\n" + " " * 24 + "a drop survives when Random < rate, Random is a byte, so: "
          + "  ".join(f"row {r} {v*100//256}%" for r, v in enumerate(RATES)))

    # Cross-check the constant that was already in the harness, before this table existed.
    print()
    from zelda.lookahead import ROW2 as HARNESS_ROW2
    same = sorted(HARNESS_ROW2) == sorted(ROW2)
    print(f"cross-check against zelda/lookahead.py ROW2 (the bomb row, mapped earlier): "
          f"{'identical' if same else 'DIFFERENT'}")
    if not same:
        print(f"  harness {sorted(HARNESS_ROW2)}")
        print(f"  cartridge {sorted(ROW2)}")
        return 1

    # Sanity: the type sets must be disjoint, or a monster would land in two rows.
    sets = {"no-drop": set(NO_DROP), "row0": set(ROW0), "row1": set(ROW1), "row2": set(ROW2)}
    overlaps = [(a, b, sorted(sets[a] & sets[b])) for i, a in enumerate(sets)
                for b in list(sets)[i + 1:] if sets[a] & sets[b]]
    if overlaps:
        print("  OVERLAP between the type sets, which cannot be right:")
        for a, b, v in overlaps:
            print(f"    {a} & {b}: {' '.join(f'{x:02X}' for x in v)}")
        return 1
    print(f"  all four type sets are disjoint ({sum(len(v) for v in sets.values())} types "
          f"accounted for)")

    print("\nForced drops, from SetUpDroppedItem (Z_04.asm):")
    print(FORCED)
    print("Still outstanding: the behavioural half. Nothing here has been checked against a\n"
          "live kill - see issue #6.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
