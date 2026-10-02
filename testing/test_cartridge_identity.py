"""What does this process believe about the cartridge, and what does it cache under that belief?

    python3 testing/test_cartridge_identity.py

`zelda/profile.py` is the answer to "which cartridge is this process asserting?", and the
next job in this repo needs it: replaying the verified 60,589-frame run against a ROM with
IPS patches applied. So the interesting behaviour is what happens to a cartridge the
profile has *never seen*.

Three things, in increasing order of how much they matter:

  * An unknown md5 does NOT refuse. It falls back to the stock geometry with
    `matched=False` and keeps decoding. That is deliberate (Stage 0a's gate was "no
    behaviour change") and it is the behaviour a patched ROM depends on, so it is
    pinned here rather than wished away.
  * `describe()` says the md5 and the word UNRECOGNISED, on the theory that a run which
    cannot say which cartridge it asserted is not a run whose numbers mean anything.
  * `keyed_cache` puts `(active().md5, args)` in the key. This is audit finding #3, and
    it is the one that bites: because an unrecognised cartridge decodes with the *stock*
    geometry, a decode computed for a patched ROM is stock geometry wearing the patched
    cartridge's md5. If the cache key were the room alone - or a maxsize=1 lru_cache -
    that wrong answer would be served to every later call for that screen and would look
    like a deliberate reading of the patched file.

The keying is checked from the INSIDE: the store is read out of the wrapper's own
`cache_clear` (`cache_clear = store.clear`, so `cache_clear.__self__` IS the store the
wrapper reads and writes) and its md5 keys are compared. Asserting on the key is the
claim; asserting only on the decode cannot tell a keyed cache from a lucky one.

The two cartridges are the stock ROM and a copy with one byte flipped in the overworld
column directory, which every screen's decode reads. The offset comes from the geometry
rather than being typed in, so a geometry change moves the test with it.

WHAT IT DOES NOT CLAIM.

  * Nothing here says a decode of a patched cartridge is CORRECT. It is stock geometry
    applied to different bytes, which is what the fallback is for: observable wrongness
    rather than a refusal. That a patch is *cosmetic* is `testing/compare_roms.py`'s
    claim, not this file's.
  * The store is read through `cache_clear.__self__`, which is a bound method of the
    store dict rather than a documented accessor. It is the same dict the wrapper
    consults - that is what makes it evidence - but it is a private detail, and if
    `keyed_cache` stops publishing `cache_clear` this file stops rather than silently
    passing on a different object.
  * The fallback-order check replaces `profile._ROM_CANDIDATES` for the duration of one
    call and restores it. It does not test `emulator.ROM`, which is captured at import
    and is a separate (known) limitation.
  * The real cartridge in `roms/` is required for the decode checks. This file ASSERTS
    it is there instead of skipping: a test that goes quietly green without the one file
    its central claim depends on is exactly how a guard ends up believed and not
    exercised.

WHAT IT NEEDS: Python and the cartridge. No display, no socket, no BizHawk.

Run:  python3 testing/test_cartridge_identity.py
"""

import contextlib
import os
import sys
from hashlib import md5 as _md5
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from zelda import owmap, profile
from zelda.emulator import ROM, ROM_NAME, VERIFIED_ROM_MD5, rom_md5

TMP = Path("/tmp/opencode/cartridge_identity")
TMP.mkdir(parents=True, exist_ok=True)

STOCK = Path(ROM)
assert STOCK.exists(), (
    f"no cartridge at {STOCK} (expected the No-Intro dump, {ROM_NAME}). Put it back with "
    f"setup_linux.sh; this file decodes two cartridges and cannot do it without one.")
assert rom_md5(STOCK) == VERIFIED_ROM_MD5, (
    f"the cartridge at {STOCK} is not the verified one. This is the journal-47 state - a "
    f"patched file left under the stock filename - and it is worth finding here rather "
    f"than in a 60,589-frame replay.")

# One byte flipped in the column directory every screen's lookup goes through. Named from
# the geometry rather than typed in, so a geometry change moves the test with it.
COL_DIR = profile.GEOMETRY[VERIFIED_ROM_MD5].ow_col_dir
PATCHED = TMP / "patched.nes"
_data = bytearray(STOCK.read_bytes())
_data[profile.HEADER + COL_DIR] ^= 0xFF
PATCHED.write_bytes(bytes(_data))
PATCHED_MD5 = _md5(bytes(_data)).hexdigest()
assert PATCHED_MD5 != VERIFIED_ROM_MD5, "the patched fixture is byte-identical to stock"


@contextlib.contextmanager
def with_env(**kw):
    """Set env vars around one block and put them back. `ZELDA_ROM` selects the active
    cartridge for every decoder in the process, so leaking it would silently retarget
    every later check here."""
    saved = {k: os.environ.get(k) for k in kw}
    try:
        for k, v in kw.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        yield
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

# =====================================================================================
# 1. An unknown cartridge falls back to the stock geometry and says so, rather than
#    refusing. `matched is False` and the geometry IS the stock one - the same object,
#    not an equal copy, so there is exactly one stock geometry in the process.
# =====================================================================================
prof = profile.resolve(PATCHED)
assert prof.md5 == PATCHED_MD5, (prof.md5, PATCHED_MD5)
assert prof.matched is False, "a patched cartridge has geometry of its own, which it does not"
assert prof.geometry is profile.GEOMETRY[VERIFIED_ROM_MD5], (
    "the fallback is not the stock geometry object")
assert profile.resolve(STOCK).matched is True, "the stock cartridge should be recognised"
print(f"unrecognised md5 {PATCHED_MD5[:12]}... -> matched=False, geometry is the stock one "
      f"(ow_col_dir ${COL_DIR:04X})")

# =====================================================================================
# 2. describe() carries the md5 and the word UNRECOGNISED, both of them, every time. A
#    gate that prints "matched" for a cartridge it has never seen is worse than no gate.
# =====================================================================================
d_unrec = prof.describe()
assert prof.md5 in d_unrec and "UNRECOGNISED" in d_unrec, d_unrec
assert "stock geometry" in d_unrec, d_unrec
assert "matched" not in d_unrec.replace("UNRECOGNISED", ""), d_unrec
stock_prof = profile.resolve(STOCK)
d_rec = stock_prof.describe()
assert stock_prof.md5 in d_rec and "matched" in d_rec, d_rec
assert "UNRECOGNISED" not in d_rec, d_rec
print(f"describe() unrecognised: {d_unrec!r}")

# =====================================================================================
# 3. unverified_reason() is the same identity question asked the other way, and it agrees
#    with describe(): None for stock, prose for the patched file.
# =====================================================================================
assert stock_prof.unverified_reason() is None, stock_prof.unverified_reason()
why = prof.unverified_reason()
assert isinstance(why, str) and PATCHED_MD5 in why and VERIFIED_ROM_MD5 in why, why
print(f"unverified_reason(): names both md5s for the patched file, None for stock")

# =====================================================================================
# 4. selected_path() reads ZELDA_ROM NOW, not at import. The defect this replaced was
#    `ROM_PATH = ROM` captured once, which ignored a ZELDA_ROM set later in the process -
#    and every decoder here reads through this function, so an early capture retargets
#    the whole project silently.
# =====================================================================================
with with_env(ZELDA_ROM=str(PATCHED)):
    assert profile.selected_path() == PATCHED, profile.selected_path()
    assert profile.active().md5 == PATCHED_MD5, profile.active().md5
with with_env(ZELDA_ROM=str(STOCK)):
    assert profile.selected_path() == STOCK, profile.selected_path()
# and with nothing set, the fallback order: the first candidate that exists, else the
# first candidate at all (which is the one whose absence produces the sensible error).
with with_env(ZELDA_ROM=None):
    got = profile.selected_path()
    cands = profile.candidate_paths()
    expect = next((p for p in cands if p.exists()), cands[0])
    assert got == expect, (got, expect, cands)
print(f"selected_path(): ZELDA_ROM wins when set; unset -> {got.name!r} from "
      f"{len(cands)} candidates in order")

# =====================================================================================
# 5. THE CACHE KEY. Read the store out of the wrapper and look at the md5s in it: two
#    cartridges, same screen, two entries. This is the assertion that fails if
#    `keyed_cache` stops putting the md5 in the key - a break no assertion on decoded
#    output can reliably catch, because a missing key does nothing with one cartridge.
# =====================================================================================
# `keyed_cache` attaches `cache_clear = store.clear`, so the bound method's __self__ is
# the very dict the wrapper consults. Read it through getattr rather than as an attribute
# so that losing it is a readable failure here and not an AttributeError four lines up.
clear = cast(Any, getattr(owmap.cells, "cache_clear", None))
store = cast(Any, getattr(clear, "__self__", None))
assert isinstance(store, dict), (
    "owmap.cells.cache_clear is not a bound method of a dict, so the wrapper's store is "
    f"no longer reachable: {type(clear)}. This file reads the store on "
    "purpose - see WHAT IT DOES NOT CLAIM - and it must stop rather than pass.")
_clear_cells = cast(Any, owmap.cells).cache_clear
_clear_squares = cast(Any, owmap.squares).cache_clear
_clear_cells()
_clear_squares()
try:
    # The active md5 is read INSIDE the block: ZELDA_ROM is what selects the cartridge,
    # and with_env puts it back on the way out, so a check outside the block is reading
    # the default cartridge every time.
    with with_env(ZELDA_ROM=str(STOCK)):
        stock_cells = owmap.cells(0x0A)
        assert profile.active().md5 == VERIFIED_ROM_MD5, profile.active().md5
    with with_env(ZELDA_ROM=str(PATCHED)):
        patched_cells = owmap.cells(0x0A)
        assert profile.active().md5 == PATCHED_MD5, profile.active().md5
except Exception:
    _clear_cells()
    _clear_squares()
    raise
# NOT cleared afterwards: the store is the evidence. A decode failure clears it and
# re-raises, so a broken run does not leave entries behind for the next one to read.

keys_md5 = {k[0] for k in store}
assert keys_md5 == {VERIFIED_ROM_MD5, PATCHED_MD5}, (
    f"the store is keyed on {keys_md5}, not on one entry per cartridge. Either the md5 is "
    f"not in the key, or a key is not (md5, args) - {sorted(map(repr, store))}")
# room 0x0A from each cartridge, and nothing else: two entries, not 256.
assert {k[1] for k in store} == {(0x0A,)}, sorted(map(repr, store))
assert len(store) == 2, f"two cartridges, one screen, but {len(store)} entries: {sorted(map(repr, store))}"
assert stock_cells != patched_cells, (
    f"flipping PRG ${COL_DIR:04X} changed nothing about screen 0x0A, so this file is not "
    "actually exercising the cache: either the offset missed the tables or the decode "
    "does not read them. Fix the offset before trusting a pass.")
print(f"keyed_cache: screen 0x0A from two cartridges -> {len(store)} entries keyed "
      f"{sorted(m[:12] + '...' for m in keys_md5)}")

# =====================================================================================
# 6. The finding, stated as a fact: the patched cartridge's entry holds a decode made
#    with the STOCK geometry, and it is filed under the PATCHED md5. That is the shape of
#    audit finding #3 - a wrong answer wearing the right cartridge's name - and the only
#    reason it is not a bug in the cache is that the key carries the md5, so the patched
#    answer can never be served to the stock cartridge or vice versa.
# =====================================================================================
patched_entry = store[(PATCHED_MD5, (0x0A,))]
assert patched_entry == patched_cells, "the stored value is not the value that was returned"
assert patched_entry != stock_cells, "the two cartridges returned the same decode"
# Re-read both with a cold cache, keyed correctly, and confirm each gets its own answer
# again: the entry under each md5 is stable, not an artefact of call order.
_clear_cells()
with with_env(ZELDA_ROM=str(PATCHED)):
    again_patched = owmap.cells(0x0A)
with with_env(ZELDA_ROM=str(STOCK)):
    again_stock = owmap.cells(0x0A)
assert again_patched == patched_cells == store[(PATCHED_MD5, (0x0A,))], "patched decode drifted"
assert again_stock == stock_cells == store[(VERIFIED_ROM_MD5, (0x0A,))], "stock decode drifted"
print(f"stock-geometry decode for the patched cartridge is memoised under the PATCHED md5 "
      f"({PATCHED_MD5[:12]}...), {len(patched_entry)}x{len(patched_entry[0])} cells, "
      f"and differs from stock's")

# =====================================================================================
# 7. The wrapper also answers to the decorated function's name and doc, and hands back
#    the undecorated one. `__wrapped__` is what the broken line in testing/test_profile.py
#    was reaching for and not finding.
# =====================================================================================
_cells = cast(Any, owmap.cells)
assert _cells.__name__ == "cells", _cells.__name__
assert _cells.__wrapped__ is not None and callable(_cells.__wrapped__)
assert "tile ids" in (_cells.__doc__ or ""), _cells.__doc__
print(f"wrapper keeps __name__={_cells.__name__!r}, the docstring, and __wrapped__")

print("all checks passed")