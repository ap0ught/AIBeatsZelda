"""The overworld decode, per cartridge, as a gate that can fail.

    python3 testing/test_owmap_conformance.py

`zelda/owmap.py:check()` is the only end-to-end validator of the geometry decode. It
walks `knowledge/rooms.json` - every overworld screen the bot has actually stood on -
re-decodes each one from the cartridge on disk, and diffs the two grids cell by cell.
It is the function that catches exactly the class of problem the next phase is about,
and **it is not a gate**: run as a module it prints one line and exits 0 either way.

    $ python3 -m zelda.owmap
    98 walked overworld screens, 98 decode exactly

    $ ZELDA_ROM=.../Zelda1_Redux_prg1.nes python3 -m zelda.owmap
    98 walked overworld screens, 53 decode exactly      <- 45 screens wrong, exit 0

Nothing asserts on that line. This file is the assertion. Four parts, in order:

  A. the layers `check()` aggregates, pinned on concrete screens - `squares()`,
     `_square_tiles()`, `cells()`, `info()`. These are the smallest units, so a
     failure names the layer instead of "98 screens wrong".
  B. `check()` on STOCK, asserted: every walked screen decodes, and the knowledge
     base has not lost one.
  C. `check()` on REDUX, in a subprocess, asserted against the CURRENT 53/98.
  D. the guard that keeps C honest when the Redux ROM is absent, and the work list
     that C prints.

## THE FRAMING OF PART C, and why it is not a dressed-up pass

Redux decodes 53 of 98. `assert exact == 98` for Redux would be a permanently red
test, and a permanently red test gets skipped - which is the failure mode this project
keeps hitting. So C does NOT assert 98. It asserts the number that was measured:

    n == 98, exact == 53, and the failing set is exactly the 45 room ids below, with
    the same per-room cell counts.

That is a **pinned known-issue list**, the same device `testing/test_ips_patch.py`
already uses for its MISMATCH/DEFECT checks: each of those asserts the *wrong* current
behaviour on purpose, prints `DEFECT`, and **fails the moment the code is corrected** -
which is the intended signal there and the opposite of the usual "test broke" meaning.
So a Redux geometry fix does not silently improve anything: it fails this file, prints
which rooms changed, and the constants here get edited deliberately. A regression fails
it too. Both directions are caught; neither is dressed up.

**A green run of this file does NOT mean Redux works.** It means: stock is perfect, and
Redux is exactly as broken as it was on 2026-10-02 in a way that has not changed since.
The printed banner says so on every run, and the docstring you are reading says so.

## WHAT IT DOES NOT CLAIM

1. **It proves the decode matches the screens the bot WALKED on stock.** That is a
   98-screen sample of the overworld, not all 256 screen ids, and it is a sample
   collected by one route through one cartridge. It says nothing about the screens no
   bot ever stood on, and nothing about the 35 dungeon screens in the same file, which
   `check()` skips on the `key.startswith("L")` arm.

2. **The 53 is a measurement, not a specification.** Nobody has decided Redux's
   geometry should decode 53/98. It decodes that because the engine has one geometry
   row and Redux is not in it. The number records a starting position; it is not a
   target and it is not a bound on how far the fix goes.

3. **Nothing here runs an emulator.** So nothing here says a Redux ROM *boots*, plays,
   or behaves. It says its bytes decode differently. A decode that matched 98/98 would
   still not prove the hack runs.

4. **The Redux half is skipped when the ROM is absent, and that skip is the sharpest
   edge in this file.** See D, and the paragraph under "the missing cartridge" there
   for the reasoning and for `ZELDA_REQUIRE_REDUX=1`.

5. **The Redux ROM is a read-only input.** It lives outside this repository, in another
   project's build output. This file opens it for reading, hashes it, and asserts the
   hash - and it does that precisely so that a *different* ROM at that path is caught
   here rather than being decoded as if it were Redux.

Run:  python3 testing/test_owmap_conformance.py
"""

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from zelda import owmap                                    # noqa: E402
from zelda import profile                                   # noqa: E402
from zelda.emulator import ROM, VERIFIED_ROM_MD5, rom_md5   # noqa: E402

STOCK = Path(ROM)

# The other cartridge, built in a different repository from a ROM hack ported to the
# stock's PRG1 revision. It is an INPUT: read-only, outside this tree, never copied in.
# Override the path with ZELDA_REDUX_ROM if it lives somewhere else.
REDUX = Path(os.environ.get("ZELDA_REDUX_ROM")
             or "/home/cmayfield/code/games/zelda1-redux/out/Zelda1_Redux_prg1.nes")
REDUX_MD5 = "1334799bc86881f14d2d19f178af2600"   # Zelda 1 Redux on PRG1

# The 98 overworld screens in knowledge/rooms.json, as of this writing. `check()`
# picks them out by `not key.startswith("L") and len(cells) == 1408`; 35 dungeon
# screens share the file and are skipped. This is the FLOOR, not the expectation:
# the list grows as the bot walks new screens, and part B asserts both that all 98 are
# still there and that none of the 35 dungeon keys leaked into the overworld count.
WALKED = {
    "06", "07", "0a", "0b", "0c", "14", "15", "16", "17", "18", "19", "1a", "1b",
    "1c", "1d", "21", "24", "25", "27", "28", "29", "2a", "2b", "2c", "2d", "2e",
    "31", "32", "34", "35", "37", "38", "39", "3a", "3b", "3c", "3d", "3e", "40",
    "41", "42", "43", "44", "45", "46", "47", "48", "49", "4a", "4b", "4c", "4d",
    "4e", "50", "51", "52", "53", "54", "55", "56", "57", "58", "59", "5a", "5b",
    "5c", "5d", "5e", "60", "61", "62", "63", "64", "65", "66", "67", "68", "69",
    "6a", "6b", "6c", "6d", "6e", "6f", "72", "73", "74", "75", "76", "77", "78",
    "79", "7a", "7b", "7c", "7d", "7e", "7f",
}

# Redux's 45 failing screens and the number of cells that differ on each. This is the
# WORK LIST: when the Redux geometry row lands, every one of these numbers changes and
# this assert fires, printing which ones. Measured 2026-10-02 against REDUX_MD5.
REDUX_FAILING = {
    "0a": 10, "0c": 2, "16": 12, "17": 32, "18": 8, "1a": 20, "1d": 4, "21": 96,
    "25": 2, "27": 18, "2a": 8, "2b": 8, "2c": 12, "2d": 8, "2e": 4, "31": 64,
    "32": 8, "34": 16, "35": 20, "37": 90, "39": 8, "3a": 12, "3b": 8, "40": 4,
    "41": 100, "42": 8, "43": 8, "44": 10, "45": 60, "4a": 10, "50": 8, "54": 4,
    "55": 28, "56": 4, "5e": 2, "64": 2, "65": 44, "66": 2, "67": 4, "6f": 2,
    "75": 46, "76": 8, "77": 6, "7b": 8, "7e": 4,
}
REDUX_EXACT = 53
REDUX_DIFF_CELLS = 842          # sum(REDUX_FAILING.values())
STOCK_N, STOCK_EXACT = 98, 98

# =============================================================================================
# the fixtures, before anything is asserted about them
# =============================================================================================
assert STOCK.exists(), (
    f"no cartridge at {STOCK}. Put the verified dump back with setup_linux.sh - parts B "
    f"and the control in C are about it and cannot run without it.")
assert STOCK.name == "Legend of Zelda, The (USA) (Rev 1).nes", STOCK
stock_md5 = rom_md5(STOCK)
assert stock_md5 == VERIFIED_ROM_MD5 == stock_md5, (
    f"roms/ holds {stock_md5}, not the verified cartridge. That is the journal-47 state - "
    f"a patched file left under the stock filename - and it belongs here, not in a "
    f"60,589-frame replay.")
print(f"stock: {STOCK}  {len(STOCK.read_bytes())} bytes  md5 {stock_md5}")

# =============================================================================================
# A. THE LAYERS `check()` AGGREGATES.  A failure here names the layer; a failure in B
#    says "45 screens wrong" and nothing else.
# =============================================================================================

# A1. `_tables()` is six 128-byte screens off `ow_effects`, 0x80 apart. Not decoded
#     anywhere else in the file, and `squares()` reaches into table 3 for the layout id,
#     so a wrong base here silently re-indexes every screen.
geom = profile.GEOMETRY[VERIFIED_ROM_MD5]
tables = owmap._tables()
assert len(tables) == 6, f"the screen-effect table is not six blocks: {len(tables)}"
assert all(len(t) == 128 for t in tables), [len(t) for t in tables]
prg = profile.prg()
assert bytes(tables[0]) == prg[geom.ow_effects: geom.ow_effects + 0x80], (
    "table 0 is not the first 0x80 bytes at ow_effects")
assert bytes(tables[5]) == prg[geom.ow_effects + 5 * 0x80: geom.ow_effects + 6 * 0x80], (
    "the stride between screen-effect tables is not 0x80")
assert [list(tables[i][:4]) for i in (0, 1, 3, 5)] == \
    [[163, 147, 99, 115], [39, 95, 107, 95], [0, 1, 2, 3], [131, 0, 131, 3]], \
    [list(tables[i][:4]) for i in (0, 1, 3, 5)]
print(f"A1. 6 screen-effect tables of 128 bytes at ${geom.ow_effects:05X}, stride 0x80; "
      f"first four bytes {[list(tables[i][:4]) for i in (0, 1, 3, 5)]}")

# A2. `_square_tiles` splits on `s >= 0x10`: below that the four tile ids come out of the
#     64-byte SECONDARY table verbatim, at or above it out of the 56-byte PRIMARY table as
#     p, p+1, p+2, p+3. The primary table is 0x38 bytes, so codes 0x38..0x7F raise - which
#     is the real boundary of this function and is asserted here rather than implied.
at = geom.ow_squares + geom.ow_squares_skip
prim = prg[at: at + 0x38]
sec = prg[at + 0x38: at + 0x38 + 64]
assert len(prim) == 0x38 == 56 and len(sec) == 64, (len(prim), len(sec))
assert owmap._square_tiles(0x10) == [prim[0x10], prim[0x10] + 1, prim[0x10] + 2, prim[0x10] + 3] \
    == [3, 4, 5, 6], owmap._square_tiles(0x10)
# The last secondary entry, whose four bytes are NOT ascending (0x89,0x88,0x8B,0x88): a
# decode that returned them in the wrong order - BR,TR,BL,TL instead of TL,BL,TR,BR -
# would still pass on every other secondary code and fail only here.
assert owmap._square_tiles(0x0F) == [137, 136, 139, 136] == list(sec[0x3C: 0x40]), \
    owmap._square_tiles(0x0F)
assert sec[0x3C: 0x40] == bytes([0x89, 0x88, 0x8B, 0x88]), sec[0x3C: 0x40].hex()
# the two codes that straddle the branch
assert owmap._square_tiles(0x0F) != owmap._square_tiles(0x10), "the branch at 0x10 is dead"
# and the table's real end: a code one past the primary table is an IndexError, not a wrap
for bad_code in (0x38, 0x40, 0x7F):
    try:
        owmap._square_tiles(bad_code)
    except IndexError:
        pass
    else:
        raise AssertionError(f"_square_tiles({bad_code:#04x}) is past the 0x38-byte primary "
                             f"table and did not raise")
assert owmap._square_tiles(0x37) == [prim[0x37], prim[0x37] + 1, prim[0x37] + 2, prim[0x37] + 3], \
    "the last in-range primary code is not decodable"
print(f"A2. _square_tiles: 0x0F (secondary, {list(sec[0x3C:0x40])}) and 0x10 (primary, "
      f"p..p+3 from {prim[0x10]:#04x}); 0x37 decodes, 0x38/0x40/0x7F raise IndexError")

# A3. `squares(room)` = 16 columns of 11 square codes, and each column is
#     `_column(desc)` for the layout byte at that column. Screen 0x07 is chosen because it
#     is walked, it has a secret, and its layout bytes are 0x50 / 0x01 / 0x81 - three
#     different column directories, so an off-by-one in the column directory or in the
#     layout stride moves this and nothing subtler.
uid07 = tables[3][0x07] & 0x7F
assert uid07 == 7, f"screen 0x07's layout id moved: {uid07}"
layout07 = list(prg[geom.ow_layouts + uid07 * 16: geom.ow_layouts + uid07 * 16 + 16])
assert layout07 == [1, 1, 1, 1, 80, 1, 167, 241, 240, 166, 129, 1, 167, 166, 1, 1], layout07
sq07 = owmap.squares(0x07)
assert len(sq07) == 16, len(sq07)
assert all(len(c) == 11 for c in sq07), [len(c) for c in sq07]
assert list(sq07[4]) == owmap._column(layout07[4]) == [27, 27, 27, 27, 27, 14, 10, 10, 10, 10, 10], \
    list(sq07[4])
assert list(sq07[5]) == owmap._column(layout07[5]) == [27, 27, 27, 27, 27, 14, 26, 27, 27, 27, 27], \
    list(sq07[5])
assert list(sq07[10]) == owmap._column(layout07[10]) == [27, 27, 27, 27, 39, 14, 26, 27, 27, 27, 27], \
    list(sq07[10])
# Every column really is its own layout byte, checked one at a time so a loop that never
# ran cannot hide: 16 columns, 16 assertions, counted.
rebuilt = [owmap._column(layout07[cx]) for cx in range(16)]
assert len(rebuilt) == 16 and all(len(c) == 11 for c in rebuilt), "a column decoded short"
assert all(tuple(rebuilt[cx]) == sq07[cx] for cx in range(16)), \
    "squares() is not 16 independent _column() decodes of the 16 layout bytes"
print(f"A3. squares(0x07): 16 x 11, rebuilt as 16 independent _column() decodes of the 16 "
      f"layout bytes at ${geom.ow_layouts + uid07 * 16:05X} {layout07}")

# A4. `cells(room)` expands each square code into 2x2 in TL,BL,TR,BR order, laid down as
#     g[2*sy][2*sx]=TL, g[2*sy+1][2*sx]=BL, g[2*sx][2*sx+1]=TR, g[2*sy+1][2*sx+1]=BR. Three
#     squares of screen 0x07, so the ordering, the stride and the CLOSED arm are all read
#     off cells() and not merely asserted about the smaller functions.
c07 = owmap.cells(0x07)
assert len(c07) == 22, len(c07)
assert all(len(r) == 32 for r in c07), sorted({len(r) for r in c07})
# (cx 0, ry 0): code 0x1B -> four DISTINCT tiles, so a TR/BR or BL/TL swap is visible.
assert sq07[0][0] == 0x1B and owmap._square_tiles(0x1B) == [216, 217, 218, 219], \
    (sq07[0][0], owmap._square_tiles(0x1B))
c00_r0, c00_r1 = list(c07[0][0:2]), list(c07[1][0:2])
assert (c00_r0, c00_r1) == ([216, 218], [217, 219]), \
    f"TL,BL / TR,BR order: got {c00_r0} and {c00_r1}"
# (cx 5, ry 5): code 14, which is NOT in CLOSED, so the plain path runs and all four
# cells are 0x26.
assert sq07[5][5] == 14 and 14 not in owmap.CLOSED, sq07[5][5]
assert owmap._square_tiles(14) == [38, 38, 38, 38], owmap._square_tiles(14)
c55_r10, c55_r11 = list(c07[10][10:12]), list(c07[11][10:12])
assert (c55_r10, c55_r11) == ([38, 38], [38, 38]), (c55_r10, c55_r11)
# (cx 10, ry 4): code 0x27, the bomb wall, which IS in CLOSED - see A5.
assert sq07[10][4] == 0x27, sq07[10][4]
wall_r8, wall_r9 = list(c07[8][20:22]), list(c07[9][20:22])
assert (wall_r8, wall_r9) == ([216, 218], [217, 219]), (wall_r8, wall_r9)
print(f"A4. cells(0x07): 22 x 32; code 0x1B at (cx0,ry0) -> rows 0/1 cols 0/1 "
      f"{[c00_r0, c00_r1]}; code 14 at (cx5,ry5) -> {[c55_r10, c55_r11]}; "
      f"code 0x27 at (cx10,ry4) -> {[wall_r8, wall_r9]}")

# A5. THE CLOSED ARM, and the only thing in the file that makes `cells()` differ from a
#     plain 2x2 expansion: a shut secret draws as the scenery AROUND it, not as itself.
#     `_square_tiles(0x27)` is (230,231,232,233) and `cells()` puts (216,217,218,219) -
#     and A4 has already pinned the cell values, so if the `s in CLOSED` branch is
#     removed these two disagree and this fails.
for code, drawn in owmap.CLOSED.items():
    assert code in owmap.SPECIAL, f"CLOSED has code {code:#04x} that SPECIAL does not"
    assert drawn != owmap._square_tiles(code), (
        f"CLOSED[{code:#04x}] == _square_tiles({code:#04x}) == {drawn}, so this code cannot "
        f"tell the two paths apart and is not testing anything")
assert len(owmap.CLOSED) == 4 and set(owmap.CLOSED) == set(owmap.SPECIAL), \
    (sorted(owmap.CLOSED), sorted(owmap.SPECIAL))
assert owmap.CLOSED == {0x26: (200, 201, 202, 203), 0x27: (216, 217, 218, 219),
                        0x28: (196, 197, 198, 199), 0x29: (188, 189, 190, 191)}, \
    owmap.CLOSED
assert owmap._square_tiles(0x27) == [230, 231, 232, 233], owmap._square_tiles(0x27)
# A coincidence worth naming, because it makes the bomb wall on screen 0x07 look like the
# plain tree at its top-left corner: code 0x1B draws the same four tiles that CLOSED draws
# for 0x27. Both assertions above are still load-bearing - what differs is the CODE, and
# the code is what `cells()` branches on - but a reader comparing the two A4 lines will
# otherwise think one of them is a copy-paste error.
assert owmap._square_tiles(0x1B) == list(owmap.CLOSED[0x27]), \
    (owmap._square_tiles(0x1B), owmap.CLOSED[0x27])
assert (c07[8][20], c07[9][20], c07[8][21], c07[9][21]) == owmap.CLOSED[0x27], (
    f"the bomb wall on screen 0x07 is not drawn CLOSED: TL,BL,TR,BR came back as "
    f"{(c07[8][20], c07[9][20], c07[8][21], c07[9][21])}, CLOSED says {owmap.CLOSED[0x27]}")
print(f"A5. all {len(owmap.CLOSED)} CLOSED codes are SPECIAL codes, each differs from its "
      f"own _square_tiles (0x27: {owmap.CLOSED[0x27]} vs {owmap._square_tiles(0x27)}), and "
      f"the bomb wall on 0x07 draws CLOSED")
print(f"A5.   (code 0x1B happens to draw {owmap._square_tiles(0x1B)} - the same four tiles - "
      f"so the two cells windows in A4 look alike; the branch is on the code, not the tile")

# A6. `info(room, quest)` for five walked screens, whole dicts, from a real run. One of
#     each kind, so a wrong CAVE/ITEM/CAVE-kind table moves one of them and no others.
assert owmap.info(0x77) == {"room": 0x77, "cave": 0x10, "kind": "wood sword", "wares": [],
                            "secret": None, "armos_item_x": None}, owmap.info(0x77)
assert owmap.info(0x0A) == {"room": 0x0A, "cave": 0x12, "kind": "white sword", "wares": [],
                            "secret": None, "armos_item_x": None}, owmap.info(0x0A)
assert owmap.info(0x0C) == {"room": 0x0C, "cave": 0x1E, "kind": "shop",
                            "wares": [("magic shield", 160), ("key", 100),
                                      ("blue candle", 60)],
                            "secret": None, "armos_item_x": None}, owmap.info(0x0C)
assert owmap.info(0x1C) == {"room": 0x1C, "cave": 0x15, "kind": "hint", "wares": [],
                            "secret": None, "armos_item_x": 176}, owmap.info(0x1C)
assert owmap.info(0x07) == {"room": 0x07, "cave": 0x17, "kind": "door repair", "wares": [],
                            "secret": ("bomb wall", 160, 128),
                            "armos_item_x": None}, owmap.info(0x07)
# the secret position is derived, not stored: column index cx -> cx*16 px, row index ry
# -> ry*16 + 64 px, and on 0x07 that is squares column 10, row 4 - the 0x27 of A4/A5.
assert (0xA0 // 16, (128 - 64) // 16) == (10, 4), "the secret position no longer maps back " \
    f"to squares column 10 row 4"
assert sq07[10][4] == 0x27, sq07[10][4]
assert owmap.SPECIAL[0x27] == "bomb wall", owmap.SPECIAL[0x27]
print(f"A6. info() on 5 screens: cave 0x10 wood sword, 0x12 white sword, 0x1E shop with 3 "
      f"wares, 0x15 hint with armos x=176, 0x17 door repair with a bomb wall at "
      f"(160, 128)")

# A7. THE QUEST GATE. `info()` returns early unless the screen's quest bits say this
#     quest has it: 0 both, 1 first only, 2 second only. 0x21 (t5 = 0x62, q = 1) is
#     first-quest-only and 0x06 (t5 = 0x84, q = 2) is second-quest-only, so each one
#     must decode in one quest and be blank in the other - which no constant-default
#     reading of `info()` could produce.
assert tables[5][0x21] == 0x62 and tables[5][0x21] >> 6 == 1, hex(tables[5][0x21])
assert tables[5][0x06] == 0x84 and tables[5][0x06] >> 6 == 2, hex(tables[5][0x06])
assert owmap.info(0x21, 1) == {"room": 0x21, "cave": 0x13, "kind": "magic sword", "wares": [],
                               "secret": ("push grave", 144, 144),
                               "armos_item_x": None}, owmap.info(0x21, 1)
assert owmap.info(0x21, 2) == {"room": 0x21, "cave": None, "kind": None, "wares": [],
                               "secret": None, "armos_item_x": None}, owmap.info(0x21, 2)
assert owmap.info(0x06, 1) == {"room": 0x06, "cave": None, "kind": None, "wares": [],
                               "secret": None, "armos_item_x": None}, owmap.info(0x06, 1)
assert owmap.info(0x06, 2) == {"room": 0x06, "cave": 0x11, "kind": "heart container",
                               "wares": [], "secret": None,
                               "armos_item_x": None}, owmap.info(0x06, 2)
# The Armos coordinate is read BEFORE the quest gate in `info()`, so it survives a quest
# mismatch - but NO Armos screen is quest-gated on this cartridge: all seven of them have
# quest bits 0. So that ordering is asserted in the source and CANNOT be exercised from
# real data, and this says so rather than pretending a loop proved it. What is checkable
# is the Armos screens themselves, and that all seven are quest-neutral, which is exactly
# what makes the gap unnoticeable. Seven, not six: 0x22 holds one and no bot has walked it.
armos_rooms = [r for r in range(128) if owmap.info(r, 1)["armos_item_x"] is not None]
assert len(armos_rooms) == 7, [hex(r) for r in armos_rooms]
assert armos_rooms == [0x0B, 0x1C, 0x22, 0x24, 0x34, 0x3D, 0x4E], [hex(r) for r in armos_rooms]
assert all(tables[5][r] >> 6 == 0 for r in armos_rooms), \
    [(hex(r), tables[5][r] >> 6) for r in armos_rooms]
assert [owmap.info(r, 1)["armos_item_x"] for r in armos_rooms] == \
    [176, 176, 48, 224, 64, 144, 160], [owmap.info(r, 1)["armos_item_x"] for r in armos_rooms]
assert len(set(armos_rooms) & {int(k, 16) for k in WALKED}) == 6, \
    sorted(hex(r) for r in set(armos_rooms) & {int(k, 16) for k in WALKED})
# and the gate's early return still has all six keys, which is the only observable of the
# ordering on a quest-gated screen.
for gated in (0x21, 0x06):
    for quest in (1, 2):
        keys = set(owmap.info(gated, quest))
        assert keys == {"room", "cave", "kind", "wares", "secret", "armos_item_x"}, keys
print(f"A7. quest gate: 0x21 is first-quest-only (t5={tables[5][0x21]:#04x}) and 0x06 is "
      f"second-quest-only (t5={tables[5][0x06]:#04x}); each decodes in one quest and is "
      f"blank in the other")
print(f"A7.   {len(armos_rooms)} Armos screens ({', '.join(hex(r) for r in armos_rooms)}) all "
      f"carry quest bits 0, so the armos-before-gate order cannot be exercised from data")

# A8. `info()` does not range-check `room`, in the two opposite ways Python allows. Room
#     128 and up raise IndexError because the screen tables are 128 bytes; a NEGATIVE room
#     is not an error at all - it indexes from the end of every table and returns a
#     complete, plausible-looking dict. A screen id is a game byte, so -1 is reachable from
#     a corrupt state, and the answer it gets is not "no cave" but "the last cave row".
for out_of_range in (128, 200, 255):
    try:
        owmap.info(out_of_range)
    except IndexError:
        pass
    else:
        raise AssertionError(f"info({out_of_range}) is past the 128-byte screen tables and "
                             f"did not raise")
neg = owmap.info(-1)
assert neg == {"room": -1, "cave": 0, "kind": None, "wares": [], "secret": None,
               "armos_item_x": None}, neg
assert tables[5][-1] >> 6 == 0, hex(tables[5][-1])      # quest bits say "both quests"...
assert neg["cave"] == 0 and neg["kind"] is None, neg    # ...and cave 0 has no CAVE name
assert owmap.info(-128)["cave"] is None, owmap.info(-128)
assert len(owmap._tables()[5]) == 128, len(owmap._tables()[5])
print(f"A8. info() has no range check: 128/200/255 raise IndexError, and info(-1) returns "
      f"the full dict {neg} by indexing from the end of every table")

# =============================================================================================
# B. `check()` ON STOCK. This is the gate.
# =============================================================================================
n, exact, diffs = owmap.check()
assert n == STOCK_N == 98, f"the knowledge base no longer holds {STOCK_N} overworld screens: {n}"
assert exact == n == STOCK_EXACT, (
    f"{n - exact} of {n} walked screens no longer decode from the cartridge: "
    + ", ".join(f"{k} ({c} cells)" for k, c, _ in diffs[:8]))
assert diffs == [], diffs[:8]
print(f"B.  check() on {stock_md5[:12]}...: {n} walked overworld screens, {exact} decode "
      f"exactly, {len(diffs)} differ")

# ... and the 98 are the same 98, by id. A knowledge base that quietly lost a screen would
# otherwise still report 98/98 if it lost one and gained another; and the count alone does
# not say the overworld filter still excludes the 35 dungeon screens.
rooms = json.loads((owmap.HARNESS / "knowledge" / "rooms.json").read_text(encoding="utf-8"))
overworld = {k for k, v in rooms.items()
             if not k.startswith("L") and len(v.get("cells", "")) == 1408}
dungeon = {k for k, v in rooms.items() if k.startswith("L") and len(v.get("cells", "")) == 1408}
assert len(rooms) == 133, len(rooms)
assert len(overworld) == 98 and len(dungeon) == 35, (len(overworld), len(dungeon))
assert len(overworld | dungeon) == len(rooms), (
    f"{len(rooms) - len(overworld | dungeon)} entries are neither 1408 hex cells nor "
    f"L-prefixed, so check()'s filter is not the whole story")
assert overworld == WALKED, (
    f"the walked-screen set changed: {sorted(overworld ^ WALKED)} appear or are gone. If "
    f"that is new knowledge, add the ids to WALKED in this file and say why.")
assert not (overworld & dungeon), sorted(overworld & dungeon)
print(f"B2. the {len(overworld)} overworld screens are the ids in WALKED, and the {len(dungeon)} "
      f"L-prefixed dungeon screens in the same file are still excluded by check()'s filter")

# =============================================================================================
# C. `check()` ON REDUX, in a subprocess.
# =============================================================================================
# Why a subprocess and not `os.environ["ZELDA_ROM"] = ...` in this process:
# `zelda/profile.py:resolve()` caches a `Profile` per resolved path and `keyed_cache`
# memoises on `(active().md5, args)`. Both are keyed correctly - `testing/test_profile.py`
# and `testing/test_cartridge_identity.py` prove that - but a fresh interpreter is the only
# way to be certain which cartridge was in effect, so the driver REPORTS the md5 it saw
# and the assertion below is on that, not on the path we asked for. The stock half above
# is deliberately in-process, so the two halves also differ in that respect.
DRIVER = """
import json, sys
sys.path.insert(0, %r)
from zelda import profile, owmap
prof = profile.active()
n, exact, diffs = owmap.check()
print("ACTIVE_MD5=" + prof.md5)
print("MATCHED=" + ("yes" if prof.matched else "no"))
print("COL_DIR=0x%%05X" %% prof.geometry.ow_col_dir)
print("CHECK=" + json.dumps({"n": n, "exact": exact, "bad": {k: c for k, c, _ in diffs}}))
""" % str(ROOT)


def decode_in(rom: Path) -> dict:
    """Run the driver with ZELDA_ROM=rom and return its report, with the cartridge it says
    it actually read attached. Asserted rather than returned, because a driver that
    failed to switch would otherwise report a confident stock answer."""
    assert rom.exists(), f"no cartridge at {rom}"
    proc = subprocess.run([sys.executable, "-c", DRIVER], cwd=ROOT, capture_output=True,
                          text=True, env={**os.environ, "ZELDA_ROM": str(rom)})
    assert proc.returncode == 0, (proc.returncode, proc.stdout, proc.stderr)
    out = {"md5": None, "matched": None, "col_dir": None, "n": 0, "exact": 0, "bad": {},
           "raw": proc.stdout}
    for line in proc.stdout.splitlines():
        if line.startswith("ACTIVE_MD5="):
            out["md5"] = line.split("=", 1)[1]
        elif line.startswith("MATCHED="):
            out["matched"] = line.split("=", 1)[1]
        elif line.startswith("COL_DIR="):
            out["col_dir"] = int(line.split("=", 1)[1], 16)
        elif line.startswith("CHECK="):
            out.update(json.loads(line.split("=", 1)[1]))
    assert out["md5"], f"the driver did not report a cartridge:\n{proc.stdout}{proc.stderr}"
    assert out["bad"] is not None
    return out


# The control: the SAME driver, the SAME code path, pointed at stock. If this did not come
# back 98/98 the Redux number below would be meaningless - it would mean the driver, not
# the cartridge, was responsible.
ctl = decode_in(STOCK)
assert ctl["md5"] == stock_md5 == VERIFIED_ROM_MD5, ctl["md5"]
assert ctl["n"] == 98 and ctl["exact"] == 98 and ctl["bad"] == {}, (ctl["n"], ctl["exact"],
                                                                    list(ctl["bad"])[:8])
assert ctl["matched"] == "yes", ctl["matched"]
assert ctl["col_dir"] == geom.ow_col_dir == 0x19D0F, (ctl["col_dir"], geom.ow_col_dir)
print(f"C0. control, same driver on stock: md5 {ctl['md5'][:12]}... matched, "
      f"ow_col_dir ${ctl['col_dir']:05X}, {ctl['n']} screens, {ctl['exact']} exact")

# --- the missing cartridge, decided explicitly ------------------------------------------
# Redux's ROM is built in ANOTHER repository. A fresh clone of this one does not have it,
# and there is nothing it could commit, because the brief for that repository is to treat
# it as a read-only input here. So this half SKIPS rather than fails - but the skip is not
# allowed to be silent, and it is not the end of what the file establishes:
#
#   * the banner below is seven lines and names the path, the md5, and the consequence;
#   * the pinned work list is PRINTED ANYWAY, from the constants in this file, so every
#     green run states the 53/98 whether or not the ROM was there to re-verify it;
#   * `ZELDA_REQUIRE_REDUX=1` makes the absence a hard failure, which is what a machine
#     that has the ROM should use;
#   * the md5 is asserted whenever the file IS there, so a different ROM at that path is
#     caught rather than decoded as if it were Redux.
#
# Why skip and not fail: a test that cannot pass on a fresh clone is a test that gets
# deleted, or added to a skip list, or worked around with --no-verify. This project's
# recurring lesson is that a permanently red gate stops being read. The honest middle is
# a loud skip plus a printed number plus an opt-in hard failure - and the number being
# printed on every run is what stops a skipped Redux half from being mistaken for a
# working one.
REQUIRE_REDUX = os.environ.get("ZELDA_REQUIRE_REDUX") == "1"

if not REDUX.exists():
    print()
    print("!" * 78)
    print(f"!! REDUX HALF NOT RUN.  No cartridge at")
    print(f"!!   {REDUX}")
    print(f"!! expected md5 {REDUX_MD5}")
    print(f"!! Zelda 1 Redux, ported to the stock's PRG1 revision, built in a different")
    print(f"!! repository and treated as a READ-ONLY input here - it is never copied in.")
    print(f"!! Point ZELDA_REDUX_ROM at it to re-verify, or set ZELDA_REQUIRE_REDUX=1 to")
    print(f"!! make this absence a hard failure (what a machine that has it should do).")
    print(f"!! What this run can therefore NOT tell you: that Redux still decodes "
          f"{REDUX_EXACT}/98.")
    print("!" * 78)
    print(f"D.  Redux work list as PINNED in this file, NOT re-verified on this run "
          f"(no cartridge):")
    for key, count in sorted(REDUX_FAILING.items()):
        print(f"D.     screen {key}: {count} cells differ")
    print(f"D.  {len(REDUX_FAILING)} of 98 screens wrong, {REDUX_DIFF_CELLS} cells in total; "
          f"{REDUX_EXACT} decode exactly")
    if REQUIRE_REDUX:
        raise AssertionError(
            f"ZELDA_REQUIRE_REDUX=1 and there is no Redux cartridge at {REDUX}. Build it "
            f"(md5 {REDUX_MD5}) or unset the variable.")
    print("all checks passed (stock only - the Redux half was skipped, see above)")
    raise SystemExit(0)

redux_md5 = rom_md5(REDUX)
assert redux_md5 == REDUX_MD5, (
    f"the file at {REDUX} is md5 {redux_md5}, not {REDUX_MD5}. Decoding it and calling it "
    f"Redux would put a different cartridge's numbers in this file's work list. If the ROM "
    f"was rebuilt, update REDUX_MD5 here and re-measure every number below.")
assert redux_md5 != stock_md5, "the two cartridges are the same file"

rx = decode_in(REDUX)
assert rx["md5"] == redux_md5, f"the driver read {rx['md5']}, not the ROM it was pointed at"
assert rx["md5"] != ctl["md5"], "the two subprocesses decoded the same cartridge"
assert rx["matched"] == "no", (
    f"Redux is not in profile.GEOMETRY, so it must decode with the stock geometry and say "
    f"so: matched={rx['matched']!r}. When the Redux geometry row lands, this assert fires - "
    f"that is the intended signal, and it is also a chance to notice that nothing in "
    f"production reads `matched`.")
assert rx["col_dir"] == ctl["col_dir"] == 0x19D0F, (
    f"Redux is still being decoded with the STOCK column directory ${ctl['col_dir']:05X} "
    f"(read ${rx['col_dir']:05X}). That is the fallback, and it is why the 45 screens below "
    f"are wrong - see testing/test_geometry_fallback.py for the byte-level diff.")
assert rx["n"] == 98, f"Redux compared {rx['n']} screens, not 98 - the knowledge base is the " \
                     f"same file, so this means check()'s filter changed"

# The work-list comparison, printed only when it has drifted. The full NEW list is printed
# before the assert, so the failure output of this file is the next version of the list -
# which is the whole reason the list is pinned rather than merely reported.
drift = sorted(set(rx["bad"]) ^ set(REDUX_FAILING))
if drift:
    for key in drift:
        print(f"C.      screen {key}: {'now fails' if key in rx['bad'] else 'now decodes'} "
              f"- it was not in the recorded list")
    for key, count in sorted(rx["bad"].items()):
        print(f"C.      screen {key}: {count} cells differ")
assert rx["exact"] == REDUX_EXACT == 53, (
    f"Redux decodes {rx['exact']}/98, not the {REDUX_EXACT}/98 recorded on 2026-10-02. "
    f"Either the geometry decode changed, or a different cartridge is at {REDUX}. The new "
    f"work list is printed above.")
assert rx["bad"] == REDUX_FAILING, (
    f"{len(drift)} screen(s) changed status: {drift}. If the decode improved, delete the "
    f"failing screens from REDUX_FAILING above and set REDUX_EXACT; if it regressed, "
    f"something in zelda/ changed.")
assert sum(rx["bad"].values()) == REDUX_DIFF_CELLS == 842, sum(rx["bad"].values())
assert len(rx["bad"]) == len(REDUX_FAILING) == 45, len(rx["bad"])
print()
print(f"C.  check() on REDUX {redux_md5[:12]}...: {rx['n']} walked overworld screens, "
      f"{rx['exact']} decode exactly, {len(rx['bad'])} differ "
      f"({sum(rx['bad'].values())} cells)")
print(f"C.  KNOWN SHORTFALL, pinned above and re-verified just now: Redux is NOT supported. "
      f"A green run of this file does not mean Redux works.")
print()
print(f"D.  Redux work list, all {len(REDUX_FAILING)} screens:")
for key, count in sorted(rx["bad"].items()):
    print(f"D.     screen {key}: {count} cells differ")

print("all checks passed")