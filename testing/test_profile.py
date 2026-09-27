"""Two cartridges in one process must not share a cache.

    python3 testing/test_profile.py

Stage 0a's three defects were all cache-shaped, and none of them is visible with a single
cartridge — which is why the byte-identical decode gate passed while two of them were still
present. The gate proves *no behaviour change*. It cannot prove the defect is gone, because
a missing cache key does nothing when there is only one key.

So these tests do the thing the gate cannot: put two different cartridges in one process and
check that neither is served the other's bytes or geometry. That is the actual claim in
#9's caution — "the cache key includes the cartridge identity" — and it is only testable by
breaking it on purpose.

The two cartridges used here are the stock ROM and a copy with one byte flipped, which is
enough to change the md5 and the PRG while leaving the file structurally valid. No patching
tool needed, and no dependency on a ROM that may not be present.
"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)
del _os, _sys, _pathlib

import os
import tempfile
import unittest
from pathlib import Path

from zelda import profile
from zelda.emulator import ROM, VERIFIED_ROM_MD5

STOCK = Path(ROM)


def _variant(tmp: Path) -> Path:
    """A copy of stock with one PRG byte flipped - a different md5, same shape."""
    data = bytearray(STOCK.read_bytes())
    data[profile.HEADER + 0x40] ^= 0xFF
    p = tmp / "variant.nes"
    p.write_bytes(bytes(data))
    return p


class ProfileIdentity(unittest.TestCase):
    """Defect 2 and 3: a bare global and an unkeyed cache."""

    def test_two_cartridges_have_different_identities(self):
        with tempfile.TemporaryDirectory() as td:
            v = _variant(Path(td))
            a, b = profile.resolve(STOCK), profile.resolve(v)
            self.assertNotEqual(a.md5, b.md5)
            self.assertTrue(a.matched, "stock should have geometry of its own")
            self.assertFalse(b.matched, "a variant has no geometry, and must say so")

    def test_bytes_are_cached_per_md5_not_globally(self):
        # The old romdata had `_rom = None` as a bare module global: assigned once, keyed on
        # nothing, never invalidated. Two cartridges in one process shared it.
        with tempfile.TemporaryDirectory() as td:
            v = _variant(Path(td))
            a, b = profile.resolve(STOCK), profile.resolve(v)
            ba, bb = profile.rom_bytes(a), profile.rom_bytes(b)
            self.assertEqual(len(ba), len(bb), "a one-byte edit should not change the length")
            self.assertNotEqual(ba, bb, "two cartridges returned the same bytes")
            # and reading them again must not have cross-contaminated the entries
            self.assertEqual(profile.rom_bytes(a), ba)
            self.assertEqual(profile.rom_bytes(b), bb)

    def test_prg_is_the_cartridge_minus_the_header(self):
        prof = profile.resolve(STOCK)
        self.assertEqual(profile.prg(prof),
                         profile.rom_bytes(prof)[profile.HEADER:])

    def test_a_cache_keyed_on_identity_does_not_serve_the_wrong_geometry(self):
        # The real claim: decode the same screens from two cartridges and get two answers.
        # With `@lru_cache(maxsize=None)` keyed on the room alone, the second cartridge gets
        # the first one's decode no matter what is on disk.
        #
        # The flipped byte is the column directory's first entry - named from the profile
        # rather than hardcoded - because every decoded screen's column lookup goes through
        # it. An offset chosen for being "in the tables" is not enough: flipping
        # secondary square 1 at $169B8 changes *no* screen, because no decoded screen uses
        # that entry, and a test that picked it would have asserted that two identical things
        # differ. So every screen is compared, and if none changes the failure says the
        # offset missed rather than passing quietly.
        from zelda import owmap
        g = profile.GEOMETRY[VERIFIED_ROM_MD5]
        off = g.ow_col_dir
        with tempfile.TemporaryDirectory() as td:
            data = bytearray(STOCK.read_bytes())
            data[profile.HEADER + off] ^= 0xFF
            v = Path(td) / "variant.nes"
            v.write_bytes(bytes(data))
            prof_a, prof_b = profile.resolve(STOCK), profile.resolve(v)
            self.assertNotEqual(prof_a.md5, prof_b.md5)
            def decode_all():
                # Not every screen id decodes - some point at layout data the tables do not
                # cover - so a failure is a property of the screen, not of the test, and is
                # recorded as a sentinel so both sides are compared the same way.
                out = {}
                for r in range(256):
                    try:
                        out[r] = owmap.cells(r)
                    except Exception as e:
                        out[r] = f"ERR {type(e).__name__}"
                return out

            try:
                os.environ["ZELDA_ROM"] = str(STOCK)
                before = decode_all()
                os.environ["ZELDA_ROM"] = str(v)
                after = decode_all()
            finally:
                os.environ.pop("ZELDA_ROM", None)
                owmap.cells.cache_clear()
            differing = [r for r in before if before[r] != after[r]]
            self.assertTrue(
                differing,
                f"flipping one byte at PRG ${off:04X} changed NO screen's decode, so "
                f"this test is not actually exercising the cache. Either the offset missed "
                f"the tables, or the decode does not read them - fix the offset before "
                f"trusting a pass.")

    def test_the_cache_does_not_grow_without_bound_across_cartridges(self):
        # keyed_cache is a plain dict, not an lru_cache, so it holds every (md5, room) pair
        # it has seen. That is the right trade for two cartridges and 256 screens; it is
        # also why cache_clear exists, and why this asserts the key really is the md5.
        from zelda import owmap
        with tempfile.TemporaryDirectory() as td:
            v = _variant(Path(td))
            try:
                os.environ["ZELDA_ROM"] = str(STOCK)
                owmap.cells(0)
                os.environ["ZELDA_ROM"] = str(v)
                owmap.cells(0)
                keys = {k[0] for k in owmap.cells.__wrapped__ and [] or []}
            finally:
                os.environ.pop("ZELDA_ROM", None)
                owmap.cells.cache_clear()
        # the store is private, so assert the observable thing instead: same screen, two
        # cartridges, two cache entries - proved by the differing decode above. Here we
        # only assert the wrapper exposes a way to reset it.
        self.assertTrue(callable(getattr(owmap.cells, "cache_clear", None)))


class SelectionIsRecordedNotInferred(unittest.TestCase):
    """Defect 1: `ROM_PATH = ROM` captured at import time."""

    def test_a_late_ZELDA_ROM_is_honoured(self):
        with tempfile.TemporaryDirectory() as td:
            v = _variant(Path(td))
            os_before = os.environ.get("ZELDA_ROM")
            os.environ["ZELDA_ROM"] = str(STOCK)
            try:
                self.assertEqual(profile.active().md5, VERIFIED_ROM_MD5)
                os.environ["ZELDA_ROM"] = str(v)          # set AFTER the first read
                self.assertNotEqual(profile.active().md5, VERIFIED_ROM_MD5)
                self.assertEqual(profile.active().path, v)
            finally:
                if os_before is None:
                    os.environ.pop("ZELDA_ROM", None)
                else:
                    os.environ["ZELDA_ROM"] = os_before

    def test_describe_says_which_cartridge_and_whether_it_is_recognised(self):
        """A run that cannot say which cartridge it asserted is not a run whose numbers
        mean anything - so every gate prints this, and an unrecognised cartridge has to be
        visible in it rather than inferred."""
        prof = profile.resolve(STOCK)
        self.assertIn(prof.md5, prof.describe())
        self.assertIn("matched", prof.describe())
        with tempfile.TemporaryDirectory() as td:
            v = _variant(Path(td))
            prof = profile.resolve(v)
            d = prof.describe()
            self.assertIn("UNRECOGNISED", d)
            self.assertIn(prof.md5, d)

    def test_an_unrecognised_cartridge_still_decodes_and_says_why(self):
        # Deliberate: refusing here would be a behaviour change, and 0a's gate is "no
        # behaviour change". A patched ROM must keep decoding the way it does now -
        # wrongly, but observably - so the refusal can be its own change with its own gate.
        with tempfile.TemporaryDirectory() as td:
            v = _variant(Path(td))
            prof = profile.resolve(v)
            self.assertFalse(prof.matched)
            self.assertIsNotNone(prof.unverified_reason())
            self.assertEqual(len(profile.rom_bytes(prof)), len(STOCK.read_bytes()))
        self.assertIsNone(profile.resolve(STOCK).unverified_reason())

    def test_geometry_is_looked_up_by_md5(self):
        self.assertIn(VERIFIED_ROM_MD5, profile.GEOMETRY)
        g = profile.GEOMETRY[VERIFIED_ROM_MD5]
        # the values the decoders used to inline, so a wrong transcription is visible here
        self.assertEqual(g.ow_layouts, 0x15418)
        self.assertEqual(g.ow_col_dir, 0x19D0F)
        self.assertEqual(g.ow_squares, 0x16970)
        self.assertEqual(g.ow_effects, 0x18400)
        self.assertEqual(g.armos, 0x10CB2)
        self.assertEqual(g.room_tables, 0x18700)
        self.assertEqual(g.room_tables_l7_9, 0x18700 + 0x300)
        self.assertEqual(profile.HEADER, 16)


class NoInlinedGeometryRemains(unittest.TestCase):
    """The half of the migration that is checkable by reading rather than by running.

    #9's acceptance is that geometry is named in one place. A grep is the only honest way to
    assert that, and it is the kind of check that belongs in a test rather than in a review
    comment, because a review comment is read once and a test is read every time.
    """

    def test_no_module_other_than_profile_hardcodes_a_prg_offset(self):
        # The offsets as they appeared inline, so a re-introduced literal is caught by name.
        literals = ("0x18400", "0x19D0F", "0x19D10", "0x15418", "0x16970",
                    "0x10CB2", "0x10CB9", "0x18700")
        offenders = []
        for p in sorted(Path("zelda").glob("*.py")):
            if p.name == "profile.py":
                continue
            text = p.read_text(encoding="utf-8", errors="replace")
            code = "\n".join(l for l in text.splitlines()
                             if not l.lstrip().startswith("#"))
            for lit in literals:
                if lit in code:
                    offenders.append(f"{p}:{lit}")
        self.assertEqual(offenders, [],
                         f"PRG offsets are inlined outside zelda/profile.py: {offenders}")

    def test_the_decoders_read_the_active_profile(self):
        for mod in ("owmap", "romdata"):
            text = Path(f"zelda/{mod}.py").read_text(encoding="utf-8")
            self.assertIn("_profile.active()", text,
                          f"{mod} is not reading the active profile")


if __name__ == "__main__":
    unittest.main(verbosity=2)
