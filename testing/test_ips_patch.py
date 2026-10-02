"""Does the IPS path do what it claims, before the next phase runs 60,589 frames against it?

The next phase replays an already-verified run against a ROM built by applying "enhanced"
IPS patches. `testing/patch_rom_ips.py` is the first thing that phase runs, and it has never
been run in this tree against anything: there is no `.ips` file anywhere in the repository.
So every line of the patch path is unexercised code that a four-hour replay depends on.

The failure this file is shaped around is not a crash. It is a *misread*: a length decoded one
byte short, a record cursor off by one, a truncate field the parser does not know where to
look. Each of those yields a ROM that is the right SIZE, has a valid iNES header, and boots -
and is not the hack that was intended. It then fails its replay for reasons that look exactly
like emulator nondeterminism, which is the same class of error that cost an hour in
`journal/47-the-cartridge-i-did-not-swap.md` (there: a patched ROM under the stock filename;
here: a patched ROM that was never the patch). Nothing downstream of this file can tell those
apart, so the checks below are byte-exact rather than smoke tests.

Each check prints the number or the literal it established, in the order they run:

  PARSER    1. a plain record lands at the offset its header names
            2. the wire format, pinned as raw hex                  10. the truncate field, after EOF
            3. an RLE count of N writes N copies (65535 too)         10b. MISMATCH: the docstring
            4. the N==1 boundary: one byte, one place                    puts it in the wrong place
            5. the record cursor survives a mixed file               10c. a SHRINKING truncate works
            6. the RLE count of 0 is a zero-length record            10d. DEFECT: a GROWING truncate
            7. "EOF" inside record data is data                             is ignored
            7b. LIMITATION: a hunk at $454F46 is swallowed            10e. DEFECT: truncate to 0
            8. a patch with no "EOF" marker is accepted              11. DEFECT: a short record
            9. bad magic is rejected                                 12. apply_patch zero-extends
                                                                13. ... and a straddling write
                                                                14. ... and an empty record
  PATCHER  15. the base ROM is byte-identical afterwards (3 paths)   19. the zero-pad branch fires
            16. an existing output is never overwritten (3 paths)    20. DEFECT: empty patch dies
            17. "UNCHANGED" is pinned
            18. "*** CHANGED ***" is pinned
  END TO   21. the Automap0.2.IPS case: short by exactly 2           25. the iNES header survives
  END      22. output md5 differs, base copy does not                26. ... and is genuinely read
            23. the diff is EXACTLY the bytes written, nowhere else
            24. the damage table decodes identically on the patch
               24b. ... and one byte of it is caught, one is invisible

WHAT IT DOES NOT CLAIM. Four things, and the fourth is the important one.

1. **No emulator.** BizHawk is never launched. That is a deliberate constraint, not a
   limitation of the harness: the checks here are about whether the right BYTES landed, and a
   replay can only tell you the bytes were wrong after four hours. Check 24 is the strongest
   emulator-free statement about game behaviour available here - it says the navigator's damage
   model is byte-identical on the patched cartridge - and it is still not a boot test. A patch
   that changes a jump target and nothing this file reads would pass every check below. In
   particular nothing here proves a patched ROM REPLAYS: only that it is the bytes it claims.

2. **No real `.ips` file.** `Automap0.2.IPS` is reconstructed from the shape the docstrings
   describe (see check 21), not decoded from the artifact, because the artifact is not in this
   repository. So this file proves the parser agrees with the IPS format as documented at
   fileformats.archiveteam.org/wiki/IPS_(binary_patch_format) - and check 10b is where it
   disagrees with `ips_decode.py`'s OWN docstring, which puts the truncate field in the wrong
   place. That disagreement is reported rather than resolved here: the code is right and the
   documentation is wrong, and the fix belongs to the docstring.

3. **The `*** CHANGED ***` branch cannot be reached honestly.** No legitimate run of the
   patcher changes the base, which is the whole point of it, so the branch that prints
   `*** CHANGED ***` is dead code in normal use. Check 18 substitutes `patch_rom_ips.md5` to
   reach it. That is the one check here that does not measure the real function; it pins a
   human-facing string, and a string is all it can pin. The honest half of the guarantee is
   check 15, which is a real run against real bytes.

4. **Six checks pin something that is wrong, and one pins a format limitation.** 10b (a
   docstring that misplaces the truncate field), 10d (a growing truncate ignored), 10e (a
   truncate to zero ignored), 11 (a short record silently shortened), 20 (an empty patch raises
   `ValueError`) and the second half of 24b (88 of the damage table's 96 bytes unchecked) are
   marked `MISMATCH` or `DEFECT` in the output and spelled out above each one. Check 7b pins a
   limitation the IPS format itself documents and recommends generators avoid. They exist so
   these are visible in the test suite and not only in a commit message, and each one FAILS if
   the code is corrected - which is the intended signal here, and the opposite of the usual
   "test broke" meaning. Do not silence one by editing production code in the same change; fix
   the code or the docstring, then flip the assertion to what it now does and drop the marker.

Run:  python3 testing/test_ips_patch.py
"""

import contextlib
import hashlib
import io
import os as _os
import pathlib as _pathlib
import subprocess
import sys

_ROOT = _pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)
del _os, _pathlib

import os
from pathlib import Path

sys.path.insert(0, str(_ROOT / "testing"))
import ips_decode
import patch_rom_ips as patcher
from ips_decode import apply_patch, decode

SCRATCH = Path("/tmp/opencode/ipstest")
SCRATCH.mkdir(parents=True, exist_ok=True)

# The real cartridge, read-only. Named once so every check in this file reads the same bytes,
# and so the md5 guard at the top and the one at the bottom cannot drift apart.
STOCK = _ROOT / "roms" / "Legend of Zelda, The (USA) (Rev 1).nes"
VERIFIED_MD5 = "614fb3085826e62f3be3a3fe0b931689"      # zelda/emulator.py:VERIFIED_ROM_MD5
PRG_SIZE = 0x20010                                     # 131,088: 16-byte header + 128K PRG
# harm_halfhearts reads this table straight out of the cartridge (zelda/overworld.py:480-499).
# Every offset below is chosen to miss it, so check 24 is the only thing that goes near it.
HARM_OFF, HARM_LEN = 0x72CA, 0x60

# -- the wire format, built here and nowhere else -------------------------------------------
# These two functions are the test's own encoder. They share no code with the decoder, and
# check 2 pins the raw hex of a whole patch file so that a bug in THIS encoder cannot cancel a
# bug in `ips_decode.decode` and make a test pass for the wrong reason.
PATCH_MAGIC, EOF_MAGIC = b"PATCH", b"EOF"


def rec(off, data):
    """A plain record: 3-byte big-endian offset, 2-byte big-endian length, the data."""
    assert len(data) <= 0xFFFF, len(data)
    return bytes([off >> 16 & 0xFF, off >> 8 & 0xFF, off & 0xFF,
                  len(data) >> 8 & 0xFF, len(data) & 0xFF]) + bytes(data)


def rle(off, run, val):
    """An RLE record: length field 0, then a 2-byte big-endian count and the byte to repeat."""
    assert run <= 0xFFFF, run
    return bytes([off >> 16 & 0xFF, off >> 8 & 0xFF, off & 0xFF, 0x00, 0x00,
                  run >> 8 & 0xFF, run & 0xFF, val & 0xFF])


def patch_blob(*records, tail=b""):
    """`tail` is what goes AFTER "EOF", which is where this parser reads a truncate from."""
    return PATCH_MAGIC + b"".join(records) + EOF_MAGIC + tail


def md5_of(path):
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


def run_patcher(base, ips, out):
    """Drive `patch_rom_ips.main()` in-process with a fake argv.

    -> (exit_code, stdout, message). A `raise SystemExit("message")` carries a string, not an
    int, and the interpreter turns that into exit status 1 - so a string code is reported as 1
    here, which is what a caller running it as a command would see, and the string comes back
    as `message` because that is where the text goes when nobody catches it. stdout is
    captured because four of its lines are the human-facing contract being pinned (checks 17,
    18, 19, 25).
    """
    argv = sys.argv
    sys.argv = ["patch_rom_ips.py", str(base), str(ips), str(out)]
    buf, code, msg = io.StringIO(), 0, ""
    try:
        with contextlib.redirect_stdout(buf):
            patcher.main()
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else 1
        msg = "" if e.code is None else str(e.code)
    finally:
        sys.argv = argv
    return code, buf.getvalue(), msg


def fresher(name, data):
    """A path under the scratch directory holding exactly `data`, created or overwritten."""
    p = SCRATCH / name
    if p.exists():
        p.unlink()
    p.write_bytes(data)
    return p


def unused(name):
    """A path under the scratch directory that is guaranteed not to exist.

    Every output goes through this rather than naming a path directly. `patch_rom_ips.py`
    refuses to overwrite, so a leftover from a previous run of this file would turn every
    output check into a refusal check - and a test that passes for the wrong reason on the
    second run is worse than a test that fails. This file is idempotent by construction.
    """
    p = SCRATCH / name
    if p.exists():
        p.unlink()
    assert not p.exists(), p
    return p


# -- the cartridge, before anything else ------------------------------------------------------
# journal/47 is the reason this is here at all: a patched ROM sat in roms/ under the stock
# filename for a day, every guard read the filename, and a replay died at frame 98,204 looking
# exactly like an emulator fault. This file only ever reads roms/; it proves that by hash, at
# the top and again at the bottom, rather than by intention.
assert STOCK.exists(), f"stock cartridge missing: {STOCK}"
stock_bytes = STOCK.read_bytes()
stock_md5 = md5_of(STOCK)
assert stock_md5 == VERIFIED_MD5, f"roms/ holds the wrong cartridge: {stock_md5}"
assert len(stock_bytes) == PRG_SIZE, f"stock is {len(stock_bytes)} bytes, not ${PRG_SIZE:05X}"
print(f"stock cartridge read-only: {len(stock_bytes)} bytes (${len(stock_bytes):05X}), "
      f"md5 {stock_md5}")

# =============================================================================================
# PARSER - `ips_decode.decode`, testing/ips_decode.py:36-62
# =============================================================================================

# 1. A plain record lands its bytes at the offset its header names - FILE offsets, header
#    included, which is what every other IPS patcher does and what a hack author assumes.
blob = patch_blob(rec(0x0010, b"\xDE\xAD\xBE\xEF"))
recs, trunc = decode(blob)
assert trunc is None, trunc
assert len(recs) == 1, recs
assert recs[0] == (0x10, b"\xDE\xAD\xBE\xEF"), recs[0]
base = bytearray(0x100)
out = apply_patch(bytes(base), recs)
assert len(out) == 0x100 and out[0x10:0x14] == b"\xDE\xAD\xBE\xEF", out[0x10:0x14].hex()
assert bytes(out[:0x10]) == bytes(0x10), "the 16 bytes before the write must be untouched"
print(f"1. plain record: 4 bytes at ${0x10:04X}, the {0x10} bytes below it untouched")

# 2. The wire format, pinned as raw hex. Everything below builds patches with this file's own
#    encoder, so this check is what stops an encoder bug and a decoder bug from cancelling.
#    The RLE line is the one worth reading twice: after the offset $0010 comes 00 00 for the
#    LENGTH FIELD, then 00 04 for the run, then AA for the value. A decoder that reads the run
#    and the value before consuming the length field lands on the wrong bytes and takes its
#    "count" from the value.
assert ips_decode.HDR == PATCH_MAGIC and ips_decode.END == EOF_MAGIC, \
    (ips_decode.HDR, ips_decode.END)
assert patch_blob(rec(0x10, b"\xDE\xAD\xBE\xEF")).hex() == \
    "50415443480000100004deadbeef454f46", patch_blob(rec(0x10, b"\xDE\xAD\xBE\xEF")).hex()
assert patch_blob(rle(0x10, 4, 0xAA)).hex() == "504154434800001000000004aa454f46", \
    patch_blob(rle(0x10, 4, 0xAA)).hex()
print("2. wire format pinned: 50 41 54 43 48 | 0000 10 0004 deadbeef | 454f46"
      "  and  0000 10 0000 0004 aa | 454f46")

# 3. An RLE count of N writes N copies. 65535 is the largest a 2-byte count can hold, and it is
#    the case that a decoder which grows the file by appending instead of extending gets wrong.
for count, val in ((1, 0xAA), (2, 0x5A), (7, 0x00), (256, 0xFF), (65535, 0x3C)):
    recs, _ = decode(patch_blob(rle(0x20, count, val)))
    assert len(recs) == 1, recs
    got = recs[0][1]
    assert len(got) == count, f"RLE count {count} produced {len(got)} bytes"
    assert got == bytes([val]) * count, f"RLE count {count} produced the wrong value"
print(f"3. RLE counts 1, 2, 7, 256, 65535 each produced exactly that many copies "
      f"(65535 -> {len(decode(patch_blob(rle(0, 65535, 0x3C)))[0][0][1])} bytes)")

# 4. The N == 1 boundary, on its own, and on where the byte LANDS rather than only on how many
#    there are. Check 3's loop already pins "count 1 gives 1 byte", so this one exists to pin the
#    two things a reimplementation does that the loop cannot see: `val * (run - 1)`, which loses
#    the byte (caught by 3), and a placement rule that only applies to short records, which would
#    leave the count right and the address wrong. Treating a 1-byte record as RLE in the first
#    place is a third mistake, ruled out by check 1 using a 4-byte record and check 6 a 0-length
#    one. So: one byte, at the offset the header named, and nothing at the offset below it.
recs, _ = decode(patch_blob(rle(0x40, 1, 0x7E)))
assert recs == [(0x40, b"\x7E")], recs
laid = apply_patch(bytes(0x80), recs)
assert laid[0x40] == 0x7E, f"the byte landed at {laid.index(0x7E):#06x}, not at $0040"
assert 0x7E not in laid[:0x40], "the byte also landed below the offset the header named"
assert bytes(laid[0x41:]) == bytes(0x80 - 0x41), "an RLE of 1 wrote more than one byte"
print("4. RLE count 1 wrote exactly one byte, at $0040 and not at $003F")

# 5. The record cursor survives a mixed file. Each record type has its own length, and the
#    cursor has to land on the next header; a decoder that adds 5 instead of 8 for RLE, or
#    forgets the +3 for the run, desynchronises here and silently mis-reads every later record.
mixed = patch_blob(rec(0x0020, b"\x01\x02"), rle(0x0030, 3, 0xBB), rec(0x0040, b"\x09"),
                   rle(0x0050, 1, 0xCC), rec(0x0060, b"\x10\x11\x12\x13\x14"))
recs, trunc = decode(mixed)
assert trunc is None, trunc
assert recs == [(0x20, b"\x01\x02"), (0x30, b"\xBB\xBB\xBB"), (0x40, b"\x09"),
                (0x50, b"\xCC"), (0x60, b"\x10\x11\x12\x13\x14")], recs
print(f"5. mixed file: {len(recs)} records survived in order, cursor never lost")

# 6. An RLE count of 0 is a ZERO-length record, not an error and not one copy. This is a real
#    degenerate input (`val * 0`), and it matters because check 14 shows an empty record at an
#    offset past EOF still has an effect in `apply_patch`.
recs, _ = decode(patch_blob(rle(0x10, 0, 0xAA)))
assert recs == [(0x10, b"")], recs
print("6. RLE count 0 produced a 0-byte record, not an error and not 1 byte")

# 7. "EOF" as record DATA must not end the stream. The terminator is only recognised at a
#    record header, so a hack that writes the three bytes 45 4F 46 into the ROM is decodable.
recs, trunc = decode(patch_blob(rec(0x00, b"EOF")))
assert recs == [(0x00, b"EOF")], recs
assert trunc is None, trunc
recs, _ = decode(patch_blob(rec(0x00, b"EOF"), rec(0x10, b"\x77")))
assert len(recs) == 2, recs
print('7. "EOF" inside record data is data: 1 record, and 2 when a second record follows it')

# 7b. A LIMITATION OF THE FORMAT, reproduced here exactly. The format's own documentation warns
#     that "programs generating IPS files should avoid generating hunks with offset 0x454F46, as
#     the byte encoding of this offset may be misinterpreted as the end-of-file marker"
#     (fileformats.archiveteam.org/wiki/IPS_(binary_patch_format)). `ips_decode.decode` falls for
#     it: the offset bytes sit at a record boundary and spell "EOF", so the loop breaks on the
#     first hunk and the patch decodes as ZERO hunks. Silent - exit 0, "0 record(s), 0 bytes
#     written", output identical to the base.
#
#     Harmless for a 131,088-byte cartridge, because $454F46 is 4.5 MB past the start and no
#     legal hunk offset here is. Pinned because this decoder is a general-purpose tool that
#     `ips_decode.py --base` would happily be pointed at something larger, and because the
#     failure mode is "the patch did nothing" rather than "the patch failed". Check 7 is the
#     sibling case and does NOT have this problem: "EOF" as DATA is not at a boundary.
deep = patch_blob(rec(0x454F46, b"\x5A"), rec(0x10, b"\x77"))
recs, trunc = decode(deep)
assert recs == [] and trunc is None, (recs, trunc)
assert decode(patch_blob(rec(0x454F45, b"\x5A\x5B"), rec(0x10, b"\x77")))[0] == \
    [(0x454F45, b"\x5A\x5B"), (0x10, b"\x77")], "the format's own workaround does not work here"
print('7b. LIMITATION: a hunk at offset $454F46 (the bytes "EOF") is swallowed as the '
      "terminator - 0 hunks, no error; the format warns generators to avoid that offset")

# 8. A patch with no "EOF" marker at all decodes without complaint. Not a claim that it should;
#    a claim that the next phase will not get a clean error, which is the thing worth knowing.
recs, trunc = decode(PATCH_MAGIC + rec(0x20, b"\x01\x02"))
assert recs == [(0x20, b"\x01\x02")] and trunc is None, (recs, trunc)
assert decode(PATCH_MAGIC) == ([], None), "a bare PATCH with no records and no EOF"
print("8. no \"EOF\" marker: decoded anyway, 0 or 1 records, no error and no truncate")

# 9. A file that does not start with "PATCH" is REJECTED, loudly. This is the one input the
#    decoder does refuse, and it is the one that matters most: an IPS that has been truncated by
#    a bad transfer, or an `.ips` file that is really something else, would otherwise decode as
#    records at whatever offsets its first five bytes happened to spell. The refusal is a
#    `SystemExit`, which at module scope exits 1 and prints the message - the same shape
#    `patch_rom_ips.py` uses for "no such file" and "refusing to overwrite".
for bad, why in ((b"PATC" + b"\x00" * 20, "a truncated magic"),
                 (b"patch" + rec(0x00, b"\x01") + EOF_MAGIC, "a lower-case magic"),
                 (b"\x00" * 32, "an all-zero file"),
                 (b"", "an empty file")):
    try:
        decode(bad)
    except SystemExit as e:
        assert "not an IPS file" in str(e), (why, str(e))
        # The message quotes what it actually saw, so a reader can tell WHICH file is wrong
        # rather than being told that some file is. `code` is the string, not an int, and the
        # interpreter turns that into exit status 1.
        assert str(e).endswith(repr(bad[:5])), (why, str(e))
        assert not isinstance(e.code, int), (why, e.code)
    else:
        raise AssertionError(f"a file with {why} decoded instead of being rejected")
# ... and a file that DOES start with "PATCH" is not rejected for being short: "PATCH" alone is
#     a patch with no records, which check 20 shows the patcher cannot use but the parser accepts.
assert decode(PATCH_MAGIC) == ([], None)
print('9. bad magic rejected: 4 inputs refused with "not an IPS file: starts {...}", '
      'string SystemExit -> exit 1; a bare "PATCH" is still accepted')

# 10. The TRUNCATE record, in the position the format actually puts it: AFTER the "EOF" marker.
#     The code breaks out of the record loop on "EOF" (`i += 3`, line 45) and reads a 3-byte
#     tail afterwards (lines 59-61). That is correct - the IPS format documents the truncation
#     extension as "the end-of-file marker MAY BE FOLLOWED by a three-byte length to which the
#     resulting file should be truncated" (fileformats.archiveteam.org/wiki/IPS_(binary_patch_
#     format), and Romhackwiki quotes it the same way) - and it is what Lunar IPS and Snes9x do.
#     It is the DOCSTRING that is wrong; see 10b. A tail of any other length is not a truncate
#     and is ignored, which is also the format's position: the field is optional and its absence
#     is the empty tail.
recs, trunc = decode(patch_blob(rec(0x8000, b"\x01\x02\x03\x04"), tail=bytes([0x00, 0x00, 0x80])))
assert recs == [(0x8000, b"\x01\x02\x03\x04")] and trunc == 0x80, (recs, trunc)
assert decode(patch_blob()) [1] is None, "no tail must not become a truncate of 0"
assert decode(patch_blob(rec(0, b"\x01"), tail=b"\x00\x00"))[1] is None, \
    "a 2-byte tail is not a truncate"
assert decode(patch_blob(rec(0, b"\x01"), tail=bytes([0, 0, 0x80, 0x00])))[1] is None, \
    "a 4-byte tail is not a truncate"
print("10. truncate read from after EOF: $00080 picked up; 0-, 2- and 4-byte tails are not "
      "truncates")

# 10b. MISMATCH, not a parser defect: `ips_decode.py`'s OWN docstring puts the truncate field
#      "between the last record and 'EOF'", which is NOT where the format puts it (see 10). So
#      the parser is right and its documentation is wrong, and the consequence is that anyone
#      who writes a patch - or a second patcher - from this docstring produces a file the parser
#      misreads completely silently.
#
#      Shown end to end: a patch built to the DOCSTRING's layout is not truncated at all, and
#      the 3-byte truncate field is parsed as a record HEADER instead. The two bytes that follow
#      it are the first two of "EOF" = 0x454F = 17743, which become a LENGTH, so the parser
#      writes the third byte of the marker - "F", 0x46 - at the offset the truncate field
#      happened to spell. Exit 0, "base UNCHANGED", and a ROM that is exactly the wrong size.
mislaid = (PATCH_MAGIC + rec(0x8000, b"\x01\x02\x03\x04") + bytes([0x00, 0x00, 0x80])
           + EOF_MAGIC)
recs, trunc = decode(mislaid)
assert trunc is None, f"the docstring-layout truncate was picked up after all: {trunc}"
assert len(recs) == 2, recs
bogus_off, bogus_data = recs[1]
assert bogus_off == 0x80 and bogus_data == b"F", (bogus_off, bogus_data)
mis_base = fresher("p10b_base.nes", bytes(0x20010))
mis_out = unused("p10b_out.nes")
mis_ips = fresher("p10b.IPS", mislaid)
code, mis_text, _ = run_patcher(mis_base, mis_ips, mis_out)
assert code == 0, (code, mis_text)
assert len(mis_out.read_bytes()) == PRG_SIZE, "the docstring-layout truncate shrank nothing"
assert mis_out.read_bytes()[0x80] == 0x46, "the bogus record's byte is not where it was predicted"
assert "UNCHANGED" in mis_text, mis_text
print(f"MISMATCH 10b. a patch built to the DOCSTRING's layout (truncate before EOF): exit 0, "
      f"trunc={trunc}, ROM still {PRG_SIZE} bytes, and a spurious {bogus_data!r} written at "
      f"${bogus_off:05X}")
print("            ips_decode.py:9 says \"between the last record and 'EOF'\"; the format puts it "
      "after. The fix is one line of docstring, not of code.")

# 10c. A SHRINKING truncate, end to end through the patcher. `patch_rom_ips.py` applies the
#      writes, then `data = data[:trunc]` (line 64) - and the tail is applied AFTER the zero-pad,
#      so a patch that both extends and truncates cannot double-count. This is the path the
#      brief names and which had never been run in this tree.
shrink_base = fresher("p10c_base.nes", bytes(range(256)) * 2)          # 512 bytes, 0x00-0xFF twice
shrink_out = unused("p10c_out.nes")
shrink_ips = fresher("p10c.IPS", patch_blob(rec(0x0008, b"\xAA\xBB"), tail=b"\x00\x00\x80"))
code, shrink_text, _ = run_patcher(shrink_base, shrink_ips, shrink_out)
shrunk = shrink_out.read_bytes()
assert code == 0, (code, shrink_text)
assert len(shrunk) == 0x80 == 128, len(shrunk)             # 512 -> 128, so a real shrink
assert shrunk[:8] == bytes(range(8)), shrunk[:8].hex()
assert shrunk[8:10] == b"\xAA\xBB", shrunk[8:10].hex()
# ... and the 118 surviving bytes after the write are untouched, so the shrink dropped the TAIL
# and not the middle: bytes 10..127 are base bytes 10..127, unmodified.
assert shrunk == bytes(range(8)) + b"\xAA\xBB" + bytes(range(0x0A, 0x80)), shrunk[:12].hex()
assert "truncates to" not in shrink_text, shrink_text      # that line is ips_decode.py's, not this
print(f'10c. shrinking truncate: 512 bytes + a 2-byte write at $0008 -> {len(shrunk)} bytes, '
      f"first 10 {shrunk[:10].hex()} (the write survives, the tail does not)")

# 10d. DEFECT - a truncate LARGER than the base does not extend the file. `data[:trunc]` on a
#      shorter buffer returns the whole buffer, so the output stays the base's length and the
#      patch's stated size is silently not honoured. The format is not explicit about whether the
#      field may extend a file, so this is a coin-flip on the spec and not an unambiguous bug -
#      but "truncate to $400" printing nothing while producing 256 bytes is the kind of thing
#      that reads as a working patch. The zero-pad branch (check 19) already knows how to grow a
#      file, and the truncate is applied after it, so honouring this is one `else`.
grow_base = fresher("p10d_base.nes", bytes(0x100))
grow_out = unused("p10d_out.nes")
grow_ips = fresher("p10d.IPS", patch_blob(rec(0x0010, b"\x01"), tail=bytes([0x00, 0x04, 0x00])))
code, grow_text, _ = run_patcher(grow_base, grow_ips, grow_out)
assert code == 0, (code, grow_text)
assert len(grow_out.read_bytes()) == 0x100, len(grow_out.read_bytes())     # spec would say 0x400
print(f"DEFECT 10d. a truncate LARGER than the base is ignored: \"truncate to $00400\" on a "
      f"$00100 base produced {len(grow_out.read_bytes())} bytes, not 1024")

# 10e. DEFECT - a truncate to ZERO is ignored, because `if trunc:` (line 63) treats 0 as absent.
#      Degenerate in practice, and harmless in the sense that nothing is lost, but it is the same
#      falsy-value bug as 10d and it means `trunc is not None` is not the test the code means.
zero_base = fresher("p10e_base.nes", bytes(0x100))
zero_out = unused("p10e_out.nes")
zero_ips = fresher("p10e.IPS", patch_blob(rec(0x0010, b"\x01"), tail=bytes([0x00, 0x00, 0x00])))
code, zero_text, _ = run_patcher(zero_base, zero_ips, zero_out)
assert code == 0, (code, zero_text)
assert len(zero_out.read_bytes()) == 0x100, len(zero_out.read_bytes())      # spec would say 0
print(f"DEFECT 10e. a truncate to $000000 is ignored: `if trunc:` at patch_rom_ips.py:63 reads 0 "
      f"as absent, so the output is {len(zero_out.read_bytes())} bytes rather than 0")

# 11. DEFECT - a record whose declared length runs past the end of the file is silently
#     SHORTENED rather than rejected, and the cursor then walks into the terminator. The
#     patcher has no other validation of an `.ips` file, and a transfer that cut one short is
#     the most likely way a wrong one arrives - so "the file was truncated in transit" and "the
#     file is fine, this patch is small" have to be told apart, and they are not.
#     It does not raise: `blob[i:i + ln]` (line 56) is a forgiving Python slice, so the
#     record comes back with fewer bytes than its own header claims and no exception is raised.
#     Worse, in this example it swallows two bytes of the "EOF" marker as data and then invents
#     a second, empty record out of what is left.
short = PATCH_MAGIC + bytes([0x00, 0x00, 0x20, 0x00, 0x04]) + b"\xDE\xAD" + EOF_MAGIC
recs, trunc = decode(short)
assert trunc is None, trunc
assert len(recs) == 2, recs
assert recs[0] == (0x20, b"\xDE\xAD" + EOF_MAGIC[:2]), recs[0]
assert len(recs[0][1]) == 4 and recs[0][1] != b"\xDE\xAD\xBE\xEF", recs[0]
assert recs[1] == (0x46, b""), recs[1]
print(f"DEFECT 11. a record declaring 4 bytes with 2 present decoded as {recs[0]} - "
      f"silently short, and it ate 2 bytes of the EOF marker")
print("          no exception, trunc=None: this is the misread that produces a wrong hack")

# 12. `apply_patch` zero-extends a write that starts past the end of the base (lines 68-70).
far = apply_patch(bytes(16), [(0x20, b"\x01\x02")])
assert len(far) == 0x22, len(far)
assert bytes(far[0x20:0x22]) == b"\x01\x02", far[0x20:].hex()
assert bytes(far[:0x20]) == bytes(0x20), "the gap must be zeros, not garbage"
print(f"12. a write at ${0x20:04X} into a 16-byte base grew it to {len(far)} bytes, "
      f"the {0x20 - 16}-byte gap zero-filled")

# 13. ... and a write that STRADDLES the end takes its tail from the patch, not from zeros.
#     This is the case a naive `if off > len(out): extend` gets wrong, and it is the same
#     length arithmetic the patcher does at lines 56-62. The base is 0x11 bytes so that the two
#     base bytes the patch does NOT cover are distinguishable from the extension.
straddle = apply_patch(b"\x11" * 10, [(8, b"\xAA\xBB\xCC\xDD")])
assert len(straddle) == 12, len(straddle)
assert bytes(straddle) == b"\x11" * 8 + b"\xAA\xBB\xCC\xDD", straddle.hex()
print(f"13. a 4-byte write at offset 8 into a 10-byte base: {len(straddle)} bytes, "
      f"tail {bytes(straddle[10:]).hex()} from the patch not from zeros")

# 14. ... and an EMPTY record still extends. `end = off + 0`, so `end > len(out)` is true for
#     any offset past the end and `out.extend(b"\x00" * (off - len(out)))` runs. Only reachable
#     from check 6's RLE count of 0, so it is rare - but it is the one way a patch that writes
#     nothing changes the file's size, and `patch_rom_ips.py` has its own copy of the same
#     arithmetic where `hi` is the max over records, so an empty record there is harmless.
grown = apply_patch(bytes(10), [(20, b"")])
assert len(grown) == 20, len(grown)
assert bytes(grown) == bytes(20), grown.hex()
print(f"14. an empty record at offset 20 into a 10-byte base grew it to {len(grown)} bytes "
      f"(edge case, reachable only from an RLE count of 0)")

# =============================================================================================
# PATCHER - `testing/patch_rom_ips.py`, lines 39-76
# =============================================================================================

# 15. THE INVARIANT. journal/47's entire return on keeping a copy of a 131 KB file is that the
#     patcher does not write over the base. In the script that is enforced only by PRINTING the
#     base md5 before and after (lines 47 and 70-73) and a human noticing. Here it is asserted:
#     the base file's bytes are compared, not its length and not the printed note.
base = fresher("p15_base.nes", bytes(range(256)) * 8)          # 2048 bytes, every value present
ips = fresher("p15.IPS", patch_blob(rec(0x0100, b"\xC0\xFF\xEE"), rle(0x0200, 5, 0x7E)))
out = unused("p15_out.nes")
before_bytes, before_md5 = base.read_bytes(), md5_of(base)
code, text, msg = run_patcher(base, ips, out)
assert code == 0, (code, text)
assert out.exists(), text
assert base.read_bytes() == before_bytes, "the patcher modified the base ROM"
assert md5_of(base) == before_md5, f"base md5 moved {before_md5} -> {md5_of(base)}"
print(f"15. base untouched: {len(before_bytes)} bytes and md5 {before_md5} identical after a "
      f"successful 2-record patch")

# ... and untouched after a REFUSED patch and after a patch that fails to decode. The refusal
#     path returns before `write_bytes`, and the decode failure returns even earlier; neither
#     opens the base for writing, and that is worth pinning separately from the happy path.
out.write_bytes(b"SENTINEL-OUTPUT")
code, text, msg = run_patcher(base, ips, out)
assert code == 1, (code, text)
assert "refusing to overwrite" in msg, msg
assert base.read_bytes() == before_bytes and md5_of(base) == before_md5, \
    "a REFUSED patch still touched the base ROM"
bad_ips = fresher("p15_bad.IPS", b"NOTAPS" + b"\x00" * 32)
never = unused("p15_never.nes")
code, text, msg = run_patcher(base, bad_ips, never)
assert code == 1, (code, text)
assert "not an IPS file" in msg, msg
assert not never.exists(), "a failed decode still wrote an output file"
assert base.read_bytes() == before_bytes and md5_of(base) == before_md5, \
    "a FAILED patch still touched the base ROM"
print("15b. base untouched after a refused patch and after a patch whose magic is wrong")

# 16. An existing output file is refused, and it is left exactly as it was. Two paths reach the
#     guard with the base untouched, so both are checked: an output that exists, and `out` that
#     is the base itself. The second is the mistake that would destroy a 131 KB cartridge with
#     no argument typo to explain it.
existing = fresher("p16_out.nes", b"SENTINEL-OUTPUT")
code, text, msg = run_patcher(base, ips, existing)
assert code == 1, (code, text)
assert existing.read_bytes() == b"SENTINEL-OUTPUT", "the existing output file was modified"
assert base.read_bytes() == before_bytes, "the refusal touched the base"
print(f"16. existing output refused: exit {code}, file still "
      f"{existing.read_bytes()!r}, base still {before_md5[:8]}...")

same = fresher("p16_same.nes", bytes(range(256)))
same_md5 = md5_of(same)
code, text, msg = run_patcher(same, ips, same)                    # base == out
assert code == 1, (code, text)
assert same.read_bytes() == bytes(range(256)), "passing the base as its own output wrote it"
assert md5_of(same) == same_md5, "base==out overwrote the base"
print(f"16b. base passed as its own output: refused, file still md5 {same_md5[:8]}...")

# 16c. The refusal as a COMMAND, not as a function call, because that is how the next phase
#      will meet it: a `raise SystemExit("...")` carries a string, and the interpreter's exit
#      status for a string code is 1 while the text goes to stderr. A shell wrapper that greps
#      stdout for the message finds nothing, so the stream the message lands on is part of the
#      contract, and only a subprocess can show it.
proc = subprocess.run([sys.executable, "testing/patch_rom_ips.py", str(base), str(ips),
                       str(existing)], cwd=_ROOT, capture_output=True, text=True)
assert proc.returncode == 1, (proc.returncode, proc.stdout, proc.stderr)
assert "refusing to overwrite" in proc.stderr, proc.stderr
assert "refusing to overwrite" not in proc.stdout, proc.stdout
assert existing.read_bytes() == b"SENTINEL-OUTPUT", "the subprocess clobbered the existing file"
assert base.read_bytes() == before_bytes, "the subprocess touched the base"
print(f"16c. as a command: exit {proc.returncode}, message on stderr "
      f"({proc.stderr.strip()!r}), nothing on stdout, both files untouched")

# 17. The success line says UNCHANGED, and says it with the digest, so a reader can compare it
#     against `zelda/emulator.py:VERIFIED_ROM_MD5` without trusting the tool that printed it.
code, text, msg = run_patcher(base, ips, unused("p17_out.nes"))
assert code == 0, (code, text)
assert f"base   md5 {before_md5}  UNCHANGED" in text, text
assert "*** CHANGED ***" not in text, text
assert "base   md5" in text and text.count("UNCHANGED") == 1, text
print(f'17. success line pinned: "base   md5 {before_md5}  UNCHANGED"')

# 18. The failure line says *** CHANGED ***. Unreachable honestly - see WHAT IT DOES NOT CLAIM
#     #3 - so `md5` is substituted to take the second reading of the base. The substitute also
#     fakes the "wrote ... md5" line; only the last line is asserted.
real_md5 = patcher.md5
seen = {"n": 0}


def drifting_md5(p):
    seen["n"] += 1
    return real_md5(p) if seen["n"] == 1 else "0" * 32


patcher.md5 = drifting_md5
try:
    code, text, msg = run_patcher(base, ips, unused("p18_out.nes"))
finally:
    patcher.md5 = real_md5
assert seen["n"] >= 2, seen
assert code == 0, (code, text)
assert "*** CHANGED ***" in text, text
assert "UNCHANGED" not in text, "the bare word UNCHANGED must not survive next to the warning"
print(f'18. the other branch, forced: "base   md5 {"0" * 32}  *** CHANGED ***"')

# 19. The zero-pad branch, and the wording of the line that tells a reader the output is
#     LONGER than the cartridge it came from. journal/47's failure mode was a patched ROM two
#     bytes longer than stock under the stock filename, so this line is the only warning.
short_base = fresher("p19_base.nes", bytes(0x100))
out = unused("p19_out.nes")
code, text, msg = run_patcher(short_base,
                              fresher("p19.IPS", patch_blob(rec(0x100, b"\xAB\xCD"))), out)
assert code == 0, (code, text)
assert "base is short by 2 byte(s); extending to $00102" in text, text
assert len(out.read_bytes()) == 0x102, len(out.read_bytes())
assert out.read_bytes()[-2:] == b"\xAB\xCD", out.read_bytes()[-2:].hex()
# The GAP case, which the 2-byte Automap case below cannot prove: a write that starts 4 bytes
# past the end must land 4 bytes past the end, not be spliced onto the end. A bytearray slice
# assignment past the end APPENDS, so skipping the extend branch happens to give the right
# answer for a write that starts exactly at the end - which is why check 21 alone would not
# catch a broken zero-pad branch.
gap_out = unused("p19b_out.nes")
code, text, msg = run_patcher(short_base, fresher("p19b.IPS", patch_blob(rec(0x104, b"\xAB\xCD"))),
                              gap_out)
gap = gap_out.read_bytes()
assert len(gap) == 0x106, len(gap)
assert gap[0x100:0x104] == b"\x00\x00\x00\x00", \
    f"the 4-byte gap is not zeros: {gap[0x100:0x104].hex()}"
assert gap[0x104:0x106] == b"\xAB\xCD", gap[0x104:].hex()
print('19. zero-pad branch: "base is short by 2 byte(s); extending to $00102", and a write '
      '4 bytes past the end zero-fills the 4-byte gap instead of splicing')

# 20. DEFECT - a valid patch with no records at all kills the patcher. `hi = max(...)` over an
#     empty sequence (line 50) raises ValueError, which is not a SystemExit, so it is a
#     traceback rather than the clean "not an IPS file" style error the script uses elsewhere.
empty_ips = fresher("p20.IPS", patch_blob())
empty_base = fresher("p20_base.nes", bytes(0x100))
empty_out = unused("p20_out.nes")
raised = None
try:
    run_patcher(empty_base, empty_ips, empty_out)
except ValueError as e:
    raised = e
assert isinstance(raised, ValueError), f"an empty patch no longer raises ValueError: {raised!r}"
assert not empty_out.exists(), "an empty patch still wrote an output file"
print(f"DEFECT 20. an empty patch (PATCH+EOF, 0 records) raises {type(raised).__name__}: "
      f"{raised} from patch_rom_ips.py:50")

# =============================================================================================
# THE REAL-WORLD CASE - Automap0.2.IPS, testing/patch_rom_ips.py:8-14
# =============================================================================================

# 21. The docstring's own example, rebuilt exactly: Automap0.2.IPS needs $20012 bytes and
#     stock Rev 1 is $20010, short by exactly 2. A 2-byte write at $20010 must produce a
#     $20012 file whose last two bytes are the patch's.
auto_base = fresher("p21_base.nes", bytes(PRG_SIZE))
auto_out = unused("p21_out.nes")
auto_ips = fresher("p21.IPS", patch_blob(rec(0x20010, b"\xDE\xAD")))
code, text, msg = run_patcher(auto_base, auto_ips, auto_out)
assert code == 0, (code, text)
produced = auto_out.read_bytes()
assert len(produced) == 0x20012 == PRG_SIZE + 2, len(produced)
assert produced[-2:] == b"\xDE\xAD", produced[-4:].hex()
assert produced[:PRG_SIZE] == bytes(PRG_SIZE), "the 131,088 stock bytes were modified"
assert "base is short by 2 byte(s); extending to $20012" in text, text
print(f"21. Automap0.2 case: ${PRG_SIZE:05X} + a 2-byte write at ${PRG_SIZE:05X} -> "
      f"${len(produced):05X} ({len(produced)} bytes), last two {produced[-2:].hex()}")

# 22. End to end against the real cartridge, on a COPY. The IPS is six records - plain, RLE,
#     multi-byte, one past $10000, and a deliberate OVERLAP with the first one - pinned as a
#     literal below so the bytes on the wire are not whatever this file's encoder produced today.
#
#     The overlap is the point. IPS semantics are "apply the records in order, later wins on an
#     overlap", and with only disjoint records the order is unobservable: reversing the list
#     produces a byte-identical ROM and every other check here still passes. Record 6 rewrites
#     $0042-$0043, which record 1 already covered, so the expected values below are NOT record
#     1's - they are record 6's. That is what makes the diff assertion able to fail on a
#     patcher that applies hunks out of order.
E2E_IPS = bytes.fromhex(
    "5041544348" "0000400004aabbccdd" "00072000021122" "010000000000075a"
    "00a5a500050102030405" "01fff00008deadbeeffeedf00d" "00004200029998" "454f46")
E2E_WRITES = [(0x0040, b"\xAA\xBB\xCC\xDD"), (0x0720, b"\x11\x22"), (0x10000, b"\x5A" * 7),
              (0x0A5A5, b"\x01\x02\x03\x04\x05"),
              (0x1FFF0, b"\xDE\xAD\xBE\xEF\xFE\xED\xF0\x0D"), (0x0042, b"\x99\x98")]
E2E_RECORDS = [rec(0x0040, b"\xAA\xBB\xCC\xDD"), rec(0x0720, b"\x11\x22"),
               rle(0x10000, 7, 0x5A), rec(0x0A5A5, b"\x01\x02\x03\x04\x05"),
               rec(0x1FFF0, b"\xDE\xAD\xBE\xEF\xFE\xED\xF0\x0D"), rec(0x0042, b"\x99\x98")]
assert patch_blob(*E2E_RECORDS) == E2E_IPS, \
    "the literal IPS above and the encoder disagree; fix the literal, not the encoder"
assert len(E2E_IPS) == 62, len(E2E_IPS)   # 5 PATCH + 9 + 7 + 8 + 10 + 13 + 7 + 3 EOF
# The offsets are chosen for the two tables this file reads: none of them is inside the 16-byte
# iNES header (0..15), and none is inside the damage table at $72CA..$7329. Check 24 is what
# proves the second one, and check 25 what proves the first; if either ever fails, the offset
# list is why, and moving it is a deliberate act rather than a lucky accident.
assert not (set(range(16)) & {o for o, _ in E2E_WRITES}), "an offset is inside the iNES header"
assert not ({o + i for o, d in E2E_WRITES for i in range(len(d))}
            & set(range(HARM_OFF, HARM_OFF + HARM_LEN))), "an offset is inside the damage table"
# The overlap has to actually overlap, or check 23 proves nothing about ordering. Record 1
# covers $0040-$0043 and record 6 starts at $0042, so the ranges intersect and the two share
# two bytes.
first = {o + i for o, d in E2E_WRITES[:1] for i in range(len(d))}
last = {o + i for o, d in E2E_WRITES[5:] for i in range(len(d))}
assert first & last == {0x42, 0x43}, (sorted(first & last), "the test records do not overlap")
e2e_base = fresher("e2e_base.nes", stock_bytes)               # a copy: roms/ is never opened
e2e_ips = fresher("e2e.IPS", E2E_IPS)
e2e_out = unused("e2e_patched.nes")
code, e2e_text, _ = run_patcher(e2e_base, e2e_ips, e2e_out)
assert code == 0, (code, e2e_text)
patched = e2e_out.read_bytes()
assert len(patched) == PRG_SIZE, len(patched)                 # nothing past the end, no padding
assert md5_of(e2e_out) != stock_md5, "the patch produced a byte-identical ROM"
assert e2e_base.read_bytes() == stock_bytes, "the base copy was modified"
assert md5_of(e2e_base) == stock_md5
print(f"22. e2e on a copy: {len(patched)} bytes, md5 {md5_of(e2e_out)} != stock, "
      f"base copy still {stock_md5}")

# 23. THE STRONGEST CHECK IN THIS FILE. The output must differ from stock in exactly the bytes
#     the IPS wrote, and nowhere else - compared byte by byte over the whole 131,088, not by
#     length and not by a checksum. An off-by-one in the offset decode writes the right bytes
#     one position out and produces a ROM that is the same size, has the same header, boots,
#     and is not the hack. This is the assertion that would catch it.
#
#     The expected values are built by applying the records IN ORDER to a dict, so the overlap
#     resolves the way the format says it must: the last writer wins. Reversing the patcher's
#     loop then fails here, at $0042, and nowhere else.
expected = {}
for off, data in E2E_WRITES:
    for i, byte in enumerate(data):
        expected[off + i] = byte
actual = {i: patched[i] for i in range(PRG_SIZE) if patched[i] != stock_bytes[i]}
assert len(expected) == 26, len(expected)
# Two different failures, said differently. Wrong INDICES means a write landed in the wrong
# place (an offset decode bug); the right indices with the wrong VALUES means the right bytes
# were written in the right order and something else was - which is what an out-of-order patcher
# looks like on an overlapping patch, and the first version of this message hid it.
extra, missing = sorted(set(actual) - set(expected)), sorted(set(expected) - set(actual))
wrong_val = sorted(i for i in set(actual) & set(expected) if actual[i] != expected[i])
assert not (extra or missing), (
    f"the diff is not the write set: {len(actual)} bytes differ, expected {len(expected)}; "
    f"{len(extra)} written where the IPS did not say ({[hex(i) for i in extra[:6]]}), "
    f"{len(missing)} not written ({[hex(i) for i in missing[:6]]})")
assert not wrong_val, (
    f"{len(wrong_val)} byte(s) differ in VALUE at the right offsets, so the writes landed in the "
    f"wrong ORDER or overlapped wrongly: "
    + ", ".join(f"${i:05X} is ${actual[i]:02X}, said ${expected[i]:02X}"
                for i in wrong_val[:6]))
assert expected[0x42] == 0x99 and expected[0x43] == 0x98, \
    "the expected values came from the FIRST record, so order is untested"
assert patched[0x42] == 0x99 and patched[0x41] == 0xBB, (patched[0x41:0x44].hex())
print(f"23. the diff is EXACTLY the {len(actual)} written bytes over all {PRG_SIZE:,} "
      f"(${min(actual):05X}..${max(actual):05X}), correct values, overlap last-writer-wins")

# 24. THE WORK-RAM-NEUTRAL SMOKE CHECK, emulator-free. `harm_halfhearts` is the one place in
#     the navigator that asserts a cartridge-sensitive fact about the bytes on disk: it reads
#     96 bytes at file offset 0x72CA and asserts the first 8 (zelda/overworld.py:480-499).
#     The five writes above were chosen to miss 0x72CA-0x7329, so the navigator's damage model
#     must come out byte-identical on the patched cartridge. It does.
from zelda import overworld                                             # noqa: E402
from zelda.emulator import ROM                                          # noqa: E402

assert Path(ROM).resolve() == STOCK.resolve(), f"the harness resolves a different ROM: {ROM}"


def harm_vector(rom_path):
    os.environ["ZELDA_ROM"] = str(rom_path)
    overworld._HARM = None                       # the table is memoised in a module global
    try:
        return [overworld.harm_halfhearts(t) for t in range(HARM_LEN)]
    finally:
        os.environ.pop("ZELDA_ROM", None)
        overworld._HARM = None


stock_harm = harm_vector(STOCK)
assert harm_vector(e2e_out) == stock_harm, "the patched cartridge decodes the damage table "\
    "differently, so the navigator would route around a different set of enemies"
# Object types 0, 1 and 2 read straight out of the cartridge's own bytes: 0 costs nothing (old
# men, Bubbles), 1 is four half-hearts (a Lynel), 2 is two. If these were literals rather than
# reads of $72CA the whole cartridge-sensitivity argument would be circular.
assert stock_harm[0] == 0 and stock_harm[1] == 4 and stock_harm[2] == 2, stock_harm[:3]
assert len(stock_harm) == HARM_LEN == 96
print(f"24. damage table on the patched cartridge: all {HARM_LEN} half-heart values identical to "
      f"stock; object types 0,1,2 = {stock_harm[0]},{stock_harm[1]},{stock_harm[2]} half-hearts")

# 24b. ... and where the check STOPS. Two patches inside the same 96-byte table, one where the
#      assert can see it and one where it cannot.
head_out = unused("e2e_harm_head.nes")
code, _, _ = run_patcher(e2e_base, fresher("e2e_hh.IPS", patch_blob(rec(HARM_OFF, b"\x00"))),
                         head_out)
assert code == 0
caught = None
try:
    harm_vector(head_out)
except AssertionError as e:
    caught = str(e)
assert caught == "damage table moved", f"a write at ${HARM_OFF:05X} was not caught: {caught!r}"
print(f'24b. a write at ${HARM_OFF:05X} IS caught: AssertionError("damage table moved")')

# The blind spot, and the reason the offsets above were chosen. The assert pins `tab[:8]`, i.e.
# $72CA-$72D1. The other 88 bytes of the table are read into _HARM and used by the navigator
# with nothing checking them, so a patch anywhere in $72D2-$7329 changes what can hurt Link and
# nothing in this repository says so. THIS is the case the project cannot currently detect -
# not the head of the table, which raises.
blind_out = unused("e2e_harm_blind.nes")
blind_off = HARM_OFF + 8
assert stock_bytes[blind_off] == 0x80, hex(stock_bytes[blind_off])
code, _, _ = run_patcher(e2e_base, fresher("e2e_hb.IPS", patch_blob(rec(blind_off, b"\x00"))),
                         blind_out)
assert code == 0
blind_harm = harm_vector(blind_out)                # no AssertionError: this is the point
assert blind_harm[8] == 0 and stock_harm[8] == 1, (stock_harm[8], blind_harm[8])
assert blind_harm != stock_harm, "the blind-spot patch changed nothing, so this proves nothing"
moved = [i for i in range(HARM_LEN) if blind_harm[i] != stock_harm[i]]
assert moved == [8], moved
print(f"DEFECT 24b. a write at ${blind_off:05X} is INVISIBLE: no assert fires, and "
      f"harm_halfhearts(8) silently goes {stock_harm[8]} -> {blind_harm[8]} "
      f"(88 of the table's 96 bytes are unchecked)")
print(f"          the next phase's patches are trusted because they replay cleanly; a patch in "
      f"${blind_off:05X}-${HARM_OFF + HARM_LEN - 1:05X} would change the game's rules")

# 25. The iNES header survives, and is reported the way `zelda/emulator.py` will read it. A
#     patcher that wrote one byte at the wrong offset in the first 16 produces a ROM that boots
#     differently or not at all, and the failure would be misread as the game having changed.
#     (skills/oc-cartridge-revision-identity: with a 128 KiB PRG image the mapper's fixed bank
#     sits at file offset +$10000, so a header byte and a banked byte are one mistake apart.)
assert stock_bytes[:4] == b"NES\x1a" and patched[:4] == b"NES\x1a", (stock_bytes[:4], patched[:4])
assert stock_bytes[:16] == patched[:16], "the 16-byte iNES header was modified"
assert "header: PRG 128K  CHR 0K  mapper 001" in e2e_text, \
    [ln for ln in e2e_text.splitlines() if "header" in ln]
assert stock_bytes[5] == 0, "CHR 0 in the header means CHR-RAM, not no graphics"
print('25. iNES header intact: "header: PRG 128K  CHR 0K  mapper 001" '
      "(CHR 0 = CHR-RAM, mapper 001 = MMC1)")

# 26. ... and that header line is READ, not a constant. If it were hardcoded, check 25 would
#     pass on every ROM including a broken one, which is exactly the kind of check that asserts
#     nothing. An IPS that writes byte 4 must change what the printer says.
hdr_out = unused("e2e_hdr.nes")
code, htext, _ = run_patcher(e2e_base, fresher("e2e_hdr.IPS", patch_blob(rec(0x04, b"\x00"))),
                             hdr_out)
assert code == 0, (code, htext)
assert "header: PRG 0K  CHR 0K  mapper 001" in htext, \
    [ln for ln in htext.splitlines() if "header" in ln]
assert hdr_out.read_bytes()[:16] != stock_bytes[:16], "the header write did not land"
print('26. the header line is read from the output: writing byte 4 turns "PRG 128K" into '
      '"PRG 0K", so check 25 is not a constant')

# =============================================================================================
# The cartridge, after everything.
# =============================================================================================
assert STOCK.read_bytes() == stock_bytes, "roms/ changed during this file's run"
assert md5_of(STOCK) == VERIFIED_MD5 == stock_md5, f"roms/ md5 moved: {md5_of(STOCK)}"
print(f"stock cartridge after: md5 {md5_of(STOCK)} (unchanged; roms/ was only ever read)")

print("all checks passed")
