"""Sixty-eight constants, one of which was a measured correction to the source they came from.

`zelda/ram.py` is 91 lines with no function in it, and it is the only place in the project that says
where anything lives. Its docstring opens with the sentence that matters more than the addresses:
*"The encoding notes matter more than the addresses."* Half the byte is not a count, three of them
are a bit per level, and one is a cursor rather than an acquisition. Every other module reads these
names rather than the numbers, so a name that points at the wrong byte is a wrong *decision* three
files away, and the failure mode is silence: a bomb count that reads 0 forever, a map check that
never becomes true, a heart total that is always one too low.

`journal/48-the-map-in-the-chest.md` is an entire session spent on one of these bytes - `$0668`,
read three different wrong ways - and its central fact is that **no instruction in the cartridge
names `$0668` as an operand**, because the one routine that writes it reaches it through an indexed
store shared with four other variables. A table like this one is what that session was arguing
with. Nothing prevents the next one from being read wrong a fourth way, so the addresses are pinned
here, and pinned *against each other*, which is where the copy-paste bug lives.

Seven checks, each printing the count or the fact it established:

  1. the 51 RAM addresses have their documented values   5. $0667/$0668 are two bytes, one bit each
  2. all 51 are distinct - no two names, one address     6. the indexed store: Items + Y = the
  3. the item slots are 17 CONSECUTIVE bytes, no gaps          compass/map addresses, from $0657
  4. $0656 is a slot and $0659/$065B/$0662 are statuses    7. the four namespaces are separate
                                                              tables and only MODE_* is corrected
  (and, between 5 and 7, the $066B gap and MODE_REGISTER's disagreement with Data Crystal)

WHAT IT DOES NOT CLAIM.

* **The addresses are not verified against the cartridge here, and cannot be.** There is no ROM in
  this file and no BizHawk. What these tests establish is that the file says what its docstring
  says, that the table is internally consistent, and that the *relationships* between the addresses
  - which are the part a transcription error breaks - hold. A whole-table shift, or a wrong address
  for a byte nothing else in the table is near, would pass. `zelda/profile.py`'s geometry test and
  `testing/compare_roms.py` are where ROM-level checking lives; this is not that.

* **`MODE_REGISTER = 0x0E` is a disagreement with the cited source, not a fact about the ROM.** The
  comment says so (`ram.py:85`): "observed: register-your-name screen (Data Crystal lists these two
  swapped)". Check 7 pins the corrected value and pins `MODE_ELIMINATION` at the other one, because
  a correction nobody re-checks becomes a second source of truth with no citation.

* **The *encoding* claims are documented, not measured, and the tests only assert the mapping from
  claim to address.** "$0659 is a status, not a count" is a claim about the game's HUD; what is
  checkable here is that `ARROWS` is `$0659` and that `$0659` is not also named by something with a
  different encoding. Nothing here observes a RAM byte.

* **Cross-namespace collisions are reported, not treated as bugs.** `LEVEL` and `MODE_STAIRS_IN`
  are both `$10`, `MODE_SELECT` and `DIR_RIGHT` are both `1`, and so on - the same number meaning a
  game mode in one table and a direction bit in another. Check 7 enumerates them and prints the
  count, because "all 68 constants are distinct" would be a false claim and a distinctness check
  that flagged them would be a nuisance people learn to ignore.

* **`START_ROOM` is a screen id, not an address**, and is checked for being `$77` and for not
  colliding with anything else in the address group - which is a different claim from `$0077` being
  meaningful RAM.

Run:  python3 testing/test_ram_addresses.py
"""

import os
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from zelda import ram

# ------------------------------------------------------------------ the three namespaces
#
# The file holds four kinds of number and only one of them is a RAM address. Splitting them by NAME
# is deliberate: `MODE_*` is a game mode (a value of $0012), `DIR_*` is a direction bitmask, and
# everything else is either an address or `START_ROOM`. Asserting "all 68 are distinct" would be
# false - see check 7 - so distinctness is asserted within each namespace instead.
UPPER = {k: v for k, v in vars(ram).items() if k.isupper() and isinstance(v, int)}
assert {k for k in vars(ram) if not k.startswith("_")} == set(UPPER), \
    "every public name in ram.py is an int in caps - a str or a lowercase one would be missed here"
MODES = {k: v for k, v in UPPER.items() if k.startswith("MODE_")}
DIRS = {k: v for k, v in UPPER.items() if k.startswith("DIR_")}
ADDRS = {k: v for k, v in UPPER.items() if k not in MODES and k not in DIRS}
assert len(MODES) == 13 and len(DIRS) == 4 and len(ADDRS) == 51, (len(MODES), len(DIRS), len(ADDRS))
assert set(ADDRS) | set(MODES) | set(DIRS) == set(UPPER), "the split missed a constant"
print(f"{len(ADDRS)} RAM addresses, {len(MODES)} game modes, {len(DIRS)} direction bits, "
      f"{len(UPPER)} constants in all")

# ------------------------------------------------------------------ 1. the documented values
#
# Transcribed from Data Crystal and ROM Detectives (ram.py:18-20). Written out longhand rather than
# read back from the module, because a check that compares the module against itself proves nothing.
DOCUMENTED = {
    "LEVEL": 0x10, "GAME_MODE": 0x12, "SUBMODE": 0x13, "FRAME_COUNTER": 0x15,
    "KILL_TALLY": 0x50, "RETURN_ROOM": 0x526,
    "LINK_X": 0x70, "ENEMY_X": 0x71, "LINK_Y": 0x84, "ENEMY_Y": 0x85, "LINK_DIR": 0x98,
    "LINK_ANIM": 0xAC, "SWORD_STATE": 0xB9, "PAUSED": 0xE0, "SCROLL_DIR": 0xE8,
    "ROOM": 0xEB, "ROOM_DEST": 0xEC,
    "ENEMY_TYPES": 0x350, "ENEMY_HP": 0x485,
}
wrong = {k: (hex(v), hex(ADDRS[k])) for k, v in DOCUMENTED.items() if ADDRS[k] != v}
assert not wrong, wrong
assert ADDRS["KILL_TALLY"] == 0x50, "the kill streak and the kill tally are the same byte"
# the object table, as read_enemies uses it: ObjType=$34F, ObjX=$70, ObjY=$84, ObjHP=$485,
# indexed by slot, slot 0 = Link. The three bases are 12 bytes apart and the enemy ranges start at
# slot 1, which is why ENEMY_TYPES ($350) is the *second* byte of its table and not the first.
assert ADDRS["ENEMY_TYPES"] == 0x350 == 0x34F + 1, hex(ADDRS["ENEMY_TYPES"])
assert ADDRS["ENEMY_HP"] == 0x485 and ADDRS["ENEMY_X"] - ADDRS["LINK_X"] == 1, "slot 1 is the first enemy"
assert ADDRS["ENEMY_Y"] - ADDRS["LINK_Y"] == 1, "Y is indexed the same way as X"
assert ADDRS["ROOM_DEST"] == ADDRS["ROOM"] + 1, "ROOM and ROOM_DEST are adjacent"
print("documented values: %d checked, all matching; ObjType base $34F with ENEMY_TYPES at $350 "
      "(slot 1), ObjHP $485, ROOM $EB / ROOM_DEST $EC" % len(DOCUMENTED))

# ------------------------------------------------------------------ 2. distinctness
#
# The bug class: a copy-paste that gives two names the same address. `drops.STREAK` and
# `ram.KILL_TALLY` are already two names for $50 on purpose, and that is the exception that proves
# the rule - it is why the check below is about the RAM addresses specifically.
dupes = {a: sorted(k for k, v in ADDRS.items() if v == a)
         for a, n in Counter(ADDRS.values()).items() if n > 1}
assert not dupes, f"two names for one address: {dupes}"
# ...and every address is inside the NES's 2 KiB of work RAM ($0000-$07FF), which is what the bridge's
# `ram` command can read at all. Nothing here is a ROM offset or a save-state index.
assert all(0x0000 <= v <= 0x07FF for v in ADDRS.values()), \
    sorted(f"{k}=${v:04X}" for k, v in ADDRS.items() if not 0 <= v <= 0x07FF)
assert max(ADDRS.values()) == ADDRS["MAX_BOMBS"] == 0x67C, hex(max(ADDRS.values()))
# The table has three bands, and the middle one is the least obvious: $0350, $0485 and $0526 are
# the twelve object slots' type / HP / return-room, not variables of Link's. Stated because a byte
# that moved across a band boundary would still be "in work RAM" and still pass every check above.
LOWER = sorted(k for k, v in ADDRS.items() if v < 0x0300)        # Link and the game mode
OBJECT_TABLE = sorted(k for k, v in ADDRS.items() if 0x0300 <= v < 0x0600)
INVENTORY = sorted(k for k, v in ADDRS.items() if v >= 0x0600)   # items, rupees, keys, hearts
assert sorted(OBJECT_TABLE) == sorted(["ENEMY_TYPES", "ENEMY_HP", "RETURN_ROOM"]), OBJECT_TABLE
assert min(ADDRS[n] for n in INVENTORY) == ADDRS["B_ITEM"] == 0x656, "the inventory band starts at $656"
print(f"all {len(ADDRS)} distinct and all inside work RAM ($0000-$07FF, highest "
      f"${max(ADDRS.values()):04X}); bands: {len(LOWER)} below $0300, {len(OBJECT_TABLE)} object-table "
      f"({', '.join(OBJECT_TABLE)}), {len(INVENTORY)} inventory from ${ADDRS['B_ITEM']:04X}")

# ------------------------------------------------------------------ 3. the item slots are contiguous
#
# $0656..$0666 is seventeen consecutive bytes, one per B-item. That they are consecutive is not a
# detail: it is why "the item slot block" can be indexed, and a gap or a duplicated address inside
# it would move one item's byte while leaving the other sixteen looking fine.
SLOTS = ["B_ITEM", "SWORD", "BOMBS", "ARROWS", "BOW", "CANDLE", "WHISTLE", "BAIT", "POTION", "ROD",
         "RAFT", "BOOK", "RING", "LADDER", "MAGIC_KEY", "BRACELET", "LETTER"]
assert len(SLOTS) == 17
assert [ADDRS[n] for n in SLOTS] == list(range(0x656, 0x656 + 17)), \
    [f"{n}=${ADDRS[n]:04X}" for n in SLOTS]
assert ADDRS["B_ITEM"] == 0x656 and ADDRS["LETTER"] == 0x666, (hex(ADDRS["B_ITEM"]), hex(ADDRS["LETTER"]))
# and the next four bytes after the block are the compass, the map, and their level-9 twins
assert [ADDRS[n] for n in ("COMPASS", "MAP", "COMPASS_L9", "MAP_L9")] == [0x667, 0x668, 0x669, 0x66A]
# $066B is unnamed: it sits between the level-9 twins and the clock, and calling it a gap is a
# statement about the file, which is worth more than leaving it implicit.
assert 0x66B not in ADDRS.values(), "$066B is a hole in this table, not a missing constant"
assert ADDRS["CLOCK"] == 0x66C and ADDRS["CLOCK"] - ADDRS["MAP_L9"] == 2, "the hole is exactly one byte"
print(f"item slots: {len(SLOTS)} consecutive bytes ${ADDRS['B_ITEM']:04X}-${ADDRS['LETTER']:04X}, "
      f"then compass/map/l9 twins ${ADDRS['COMPASS']:04X}-${ADDRS['MAP_L9']:04X}, "
      f"one unnamed byte $066B, clock ${ADDRS['CLOCK']:04X}")

# ------------------------------------------------------------------ 4. slot vs status vs count
#
# The docstring's encoding notes, each attached to the address it is about (ram.py:5-16). The point
# of the list is that a name cannot be read as a number: BOMBS is a count, ARROWS is not, B_ITEM is
# neither. What is checkable here is that each claim is attached to a distinct byte, because that
# is what stops "one byte, two encodings" - the actual bug in journal/48.
CLAIMS = [
    ("$0656", "B_ITEM", "slot", "a cursor, not an acquisition"),
    ("$0657", "SWORD", "count", "0/1/2/3"),
    ("$0658", "BOMBS", "count", "a real count"),
    ("$0659", "ARROWS", "status", "0 none / 1 arrow / 2 silver arrow"),
    ("$065B", "CANDLE", "status", "0 none / 1 blue / 2 red"),
    ("$065D", "BAIT", "count", "Food in Inventory"),
    ("$0662", "RING", "status", "0 none / 1 blue / 2 red"),
    ("$0667", "COMPASS", "bitfield", "one bit PER LEVEL"),
    ("$0668", "MAP", "bitfield", "one bit PER LEVEL"),
    ("$066F", "HEARTS", "nybbles", "low = hearts filled, high = containers - 1"),
    ("$0670", "HEART_FRAC", "byte", "$00 / $01-$7F / $80-$FF"),
    ("$0671", "TRIFORCE", "bitfield", "one bit per piece"),
]
assert len(CLAIMS) == 12, len(CLAIMS)
for text, name, kind, _why in CLAIMS:
    assert ADDRS[name] == int(text.lstrip("$"), 16), \
        f"{name} is ${ADDRS[name]:04X}, the docstring says {text}"
kinds = Counter(k for _, _, k, _ in CLAIMS)
assert kinds["status"] == 3 and kinds["bitfield"] == 3 and kinds["count"] == 3, dict(kinds)
# the two nybbles of $066F are the only place hearts are stored, and the encoding note is what
# `emulator.State.hearts` implements: low nybble +1.0/$80 fraction, high nybble containers - 1.
assert ADDRS["HEART_FRAC"] == ADDRS["HEARTS"] + 1, "the partial-heart byte follows the hearts byte"
assert ADDRS["HEARTS"] == 0x66F, hex(ADDRS["HEARTS"])
# the three STATUS bytes are all in the B-item block, and all three read 0/1/2 like the sword's:
# they are the three acquisitions that are encoded as a level, not as a quantity.
for n in ("ARROWS", "CANDLE", "RING"):
    assert 0x656 <= ADDRS[n] <= 0x666, f"{n} left the B-item block"
assert {ADDRS[n] for n in ("ARROWS", "CANDLE", "RING")} == {0x659, 0x65B, 0x662}
print("encodings: 3 statuses ($659/$65B/$662), 3 bit-per-level fields ($667/$668/$671), "
      "3 counts ($657/$658/$65D), $66F is the only nybble-packed byte, $670 is its fraction")
# ...and BOMBS really is the one a count is taken from. `drops.ROWS[2]` bombs and the run's own
# bomb-bought arithmetic both go through this name, so a status/count swap here is a silent wrong
# number rather than a crash.
assert ADDRS["BOMBS"] == 0x658 and not (ADDRS["BOMBS"] in {ADDRS[n] for n in ("ARROWS", "CANDLE", "RING")})
assert ADDRS["B_ITEM"] + 2 == ADDRS["BOMBS"], "bombs is the third item slot, not the second"

# ------------------------------------------------------------------ 5. one bit per level
#
# Not a 0/1 flag. A 0/1 reading of $0668 is the third wrong way journal/48 counted, and the way that
# cost the acquisition tracker two counts. What is checkable without the cartridge: the two fields
# are two DIFFERENT bytes (so neither can be the other's bit), and each has a separate level-9 byte,
# which is only necessary if the byte is indexed by level.
assert ADDRS["MAP"] == ADDRS["COMPASS"] + 1, "compass and map are adjacent, not one byte"
assert ADDRS["COMPASS_L9"] == ADDRS["COMPASS"] + 2 and ADDRS["MAP_L9"] == ADDRS["MAP"] + 2, \
    "the level-9 twins are two bytes past their level 1-8 byte"
# nine levels need nine bits; one byte holds eight. So $0667/$0668 cannot be a per-level bitfield
# covering level 9 alone - which is exactly why the level-9 twins exist.
assert ADDRS["COMPASS_L9"] - ADDRS["COMPASS"] == 2, "if level 9 were bit 9, there would be no twin"
# 8 Triforce pieces is a whole byte's worth of bits, so - unlike the compass and the map - it needs
# no ninth byte. $0672 being unnamed is that fact showing up in the table.
assert ADDRS["TRIFORCE"] == 0x671 and 0x672 not in ADDRS.values(), \
    "8 pieces fit in $0671; a level-9 twin would mean a ninth piece, and there is not one"
print("compass $0667 and map $0668 are two bytes with level-9 twins at $0669/$066A; one byte holds "
      "8 bits and there are 9 levels, which is why the twins exist. Triforce needs all 8 in $0671")

# ------------------------------------------------------------------ 6. Items + Y
#
# The fact journal/48 is built on: `Items = $0657`, `Y` is an item slot from ItemIdToSlot, and one
# `STA Items, Y` sets FOUR variables. id $16 -> slot $10 -> $0667 compass, id $17 -> slot $11 ->
# $0668 map, and the same three lines set $0669, $066A and $0671. A byte-pattern search for
# `68 06` returns zero hits, and that is the correct answer rather than a failed search.
ITEM_SLOT_BASE = ADDRS["SWORD"]
assert ITEM_SLOT_BASE == 0x657, "the indexed store's base is Items, which is $0657 - the sword slot"
assert ITEM_SLOT_BASE + 0x10 == ADDRS["COMPASS"] == 0x667, "slot $10 is the compass"
assert ITEM_SLOT_BASE + 0x11 == ADDRS["MAP"] == 0x668, "slot $11 is the map"
assert ITEM_SLOT_BASE + 0x12 == ADDRS["COMPASS_L9"] == 0x669, "slot $12 is the level-9 compass"
assert ITEM_SLOT_BASE + 0x13 == ADDRS["MAP_L9"] == 0x66A, "slot $13 is the level-9 map"
assert ADDRS["TRIFORCE"] == 0x671, "slot $1A is the Triforce, from the same three lines"
# all five addresses in one run, so they are contiguous apart from the hole at $066B
written = [ADDRS[n] for n in ("COMPASS", "MAP", "COMPASS_L9", "MAP_L9", "TRIFORCE")]
assert written == [0x667, 0x668, 0x669, 0x66A, 0x671], [hex(a) for a in written]
span = written[-1] - written[0] + 1
assert span == 11 and len(written) == 5, (span, len(written))
# The span $0667-$0671 is 11 bytes and this one routine writes five of them, none of them adjacent
# to all the others. That is the shape that makes a byte-pattern search for `68 06` across PRG-ROM
# return zero hits: the address is not an operand anywhere, and no amount of grepping finds it.
between = sorted(v for v in ADDRS.values() if 0x667 <= v <= 0x671)
assert between == [0x667, 0x668, 0x669, 0x66A, 0x66C, 0x66D, 0x66E, 0x66F, 0x670, 0x671], \
    [hex(v) for v in between]
assert 0x66B not in ADDRS.values(), "$066B is the one byte of the span nothing in this file names"
print(f"Items=$0657 + Y: slots $10-$13 give compass/map/l9-twins at "
      f"${ADDRS['COMPASS']:04X}-${ADDRS['MAP_L9']:04X}, and the same store reaches Triforce "
      f"${ADDRS['TRIFORCE']:04X} - 5 bytes over 11, with $066B the hole")

# ------------------------------------------------------------------ 7. four namespaces
assert MODES == {"MODE_TITLE": 0x00, "MODE_SELECT": 0x01, "MODE_TRANSITION": 0x02, "MODE_WIPE": 0x03,
                 "MODE_STAIRS_OUT": 0x04, "MODE_NORMAL": 0x05, "MODE_PRE_SCROLL": 0x06,
                 "MODE_SCROLLING": 0x07, "MODE_GROTTO_EXIT": 0x0A, "MODE_GROTTO": 0x0B,
                 "MODE_REGISTER": 0x0E, "MODE_ELIMINATION": 0x0F, "MODE_STAIRS_IN": 0x10}, \
    {k: hex(v) for k, v in MODES.items()}
# MODE_REGISTER is a MEASURED correction to the table these came from. ram.py:85 says Data Crystal
# lists $0E and $0F the other way round; the observation on this cartridge puts the
# register-your-name screen at $0E. Pin BOTH values, because a correction nobody re-checks is a
# second source of truth with no citation, and a swap here is a run that waits on a screen that
# never comes (or walks into one that does).
assert MODES["MODE_REGISTER"] == 0x0E, "register-your-name is $0E, observed on this cartridge"
assert MODES["MODE_ELIMINATION"] == 0x0F, "elimination is $0F, the other half of the swap"
assert MODES["MODE_REGISTER"] != MODES["MODE_ELIMINATION"], "a swap would make these equal"
# the two the fighter and the cave code test on every frame
assert MODES["MODE_NORMAL"] == 0x05 and MODES["MODE_GROTTO"] == 0x0B, "0x05 is overworld play, 0x0B a cave"
assert len(set(MODES.values())) == 13, "the 13 modes collide"
assert set(MODES) == {f"MODE_{n}" for n in
                      ("TITLE", "SELECT", "TRANSITION", "WIPE", "STAIRS_OUT", "NORMAL", "PRE_SCROLL",
                       "SCROLLING", "GROTTO_EXIT", "GROTTO", "REGISTER", "ELIMINATION", "STAIRS_IN")}
# ...and the 13 modes are not the 13 consecutive values 0x00-0x0C: four are missing, which is why
# the gaps below are facts rather than mistakes.
missing = sorted(set(range(0x00, 0x11)) - set(MODES.values()))
assert missing == [0x08, 0x09, 0x0C, 0x0D], [hex(m) for m in missing]
assert DIRS == {"DIR_RIGHT": 1, "DIR_LEFT": 2, "DIR_DOWN": 4, "DIR_UP": 8}
# one bit each, and together they cover every facing value there is
assert all(v and not (v & (v - 1)) for v in DIRS.values()), "a direction is a single bit"
assert sum(DIRS.values()) == 0x0F, "the four facings OR to $0F"
assert ADDRS["LINK_DIR"] == 0x98, "LINK_DIR is where the same four bits are read"
# Cross-namespace collisions are real and are NOT bugs: the same number meaning a game mode in one
# table and a direction bit in another is how the game is built. Enumerated rather than asserted
# away, because "all 68 constants are distinct" would be a false claim and a checker that flagged
# these four would be a nuisance people learn to ignore.
by_value = {}
for group in (ADDRS, MODES, DIRS):
    for k, v in group.items():
        by_value.setdefault(v, []).append(k)
collide = {v: sorted(ks) for v, ks in by_value.items() if len(ks) > 1}
assert collide == {0x01: ["DIR_RIGHT", "MODE_SELECT"], 0x02: ["DIR_LEFT", "MODE_TRANSITION"],
                   0x04: ["DIR_DOWN", "MODE_STAIRS_OUT"], 0x10: ["LEVEL", "MODE_STAIRS_IN"]}, collide
assert len(by_value) == len(UPPER) - len(collide), (len(by_value), len(UPPER))
print(f"13 modes, 4 gaps ($08/$09/$0C/$0D unused); 4 direction bits OR to $0F; "
      f"{len(UPPER)} constants share only {len(by_value)} values, and the {len(collide)} "
      f"collisions are all nameable: "
      + ", ".join(f"{v}=${v:02X}({'/'.join(ks)})" for v, ks in sorted(collide.items())))

print("all checks passed")