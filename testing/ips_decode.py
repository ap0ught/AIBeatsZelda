"""Decode an IPS patch file and report which addresses it writes.

    python3 testing/ips_decode.py <file.ips> [--base <file.nes>]

IPS format: the literal string "PATCH", then a series of records, then "EOF".
Each record is a 3-byte big-endian offset, a 2-byte big-endian length, and that
many bytes of replacement data. A length of 0 means an RLE record instead: the
next 2 bytes are a run length and the byte after is the value to repeat. An
optional 3-byte truncate length sits between the last record and "EOF".

Why this is here
----------------
`Automap Plus.IPS` (v0.2, 2011) is a Zelda 1 hack that draws the automap. Any
automap hack has to *read* the map and compass state out of RAM to draw it, so
the addresses it touches are the game's own map-reading code - which is the
direct route to the open question in issue #5, where $0668 changes two bits at
no cost and does not behave like an owned map.

With --base, the patch is applied to a ROM in memory and the differing regions
are annotated with the surrounding original bytes, so each hunk can be read in
context instead of as bare hex.
"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib

import sys
from pathlib import Path

HDR = b"PATCH"
END = b"EOF"


def decode(blob: bytes):
    """-> (records, truncate_len_or_None). records: (offset, bytes) pairs."""
    if blob[:5] != HDR:
        raise SystemExit(f"not an IPS file: starts {blob[:5]!r}")
    recs = []
    i = 5
    n = len(blob)
    while i < n:
        if blob[i:i + 3] == END:
            i += 3
            break
        off = int.from_bytes(blob[i:i + 3], "big")
        ln = int.from_bytes(blob[i + 3:i + 5], "big")
        i += 5
        if ln == 0:
            run = int.from_bytes(blob[i:i + 2], "big")
            val = blob[i + 2:i + 3]
            i += 3
            recs.append((off, val * run))
        else:
            recs.append((off, blob[i:i + ln]))
            i += ln
    trunc = None
    tail = blob[i:]
    if len(tail) == 3:
        trunc = int.from_bytes(tail, "big")
    return recs, trunc


def apply_patch(rom: bytes, recs) -> bytearray:
    out = bytearray(rom)
    for off, data in recs:
        end = off + len(data)
        if end > len(out):
            out.extend(b"\x00" * (end - len(out)))
        out[off:end] = data
    return out


def hexdump(b: bytes) -> str:
    return " ".join(f"{x:02X}" for x in b)


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        raise SystemExit(__doc__)
    src = Path(args[0])
    base = None
    if "--base" in sys.argv:
        base = Path(sys.argv[sys.argv.index("--base") + 1])

    recs, trunc = decode(src.read_bytes())
    print(f"{src.name}: {len(recs)} record(s), "
          f"{sum(len(d) for _, d in recs)} bytes written"
          + (f", truncates to ${trunc:06X}" if trunc else ""))

    # Group into contiguous runs so related hunks read as blocks.
    runs: list[tuple[int, list]] = []
    for off, data in recs:
        if runs and off <= runs[-1][0] + len(b"".join(d for _, d in runs[-1][1])):
            runs[-1][1].append((off, data))
        else:
            runs.append((off, [(off, data)]))

    for start, group in runs:
        lo = min(o for o, _ in group)
        hi = max(o + len(d) for o, d in group)
        size = hi - lo
        where = ""
        if lo < 0x8000:
            where = "  [PRG-ROM, fixed bank]"
        elif lo < 0x10000:
            where = "  [PRG-ROM, switchable bank]"
        else:
            where = "  [CHR-ROM / beyond]"
        print(f"\n  ${lo:04X}-${hi:04X}  {size:>4} bytes{where}")
        if size <= 64:
            for o, d in group:
                print(f"    ${o:04X}: {hexdump(d)}")
        else:
            print(f"    ({size} bytes, too long to list; use --base to see context)")

    if base is None:
        return

    rom = bytearray(base.read_bytes())
    patched = apply_patch(rom, recs)
    print(f"\napplied to {base.name} ({len(rom)} bytes) -> {len(patched)} bytes")
    diff = [i for i in range(min(len(rom), len(patched))) if rom[i] != patched[i]]
    print(f"{len(diff)} bytes differ from the base ROM")
    for lo, group in runs:
        hi = max(o + len(d) for o, d in group)
        s, e = max(0, lo - 8), min(len(patched), hi + 8)
        print(f"\n  --- context for ${lo:04X}-${hi:04X} ---")
        print(f"  before: ...{hexdump(bytes(rom[s:lo]))} | {hexdump(bytes(rom[lo:hi]))} | "
              f"{hexdump(bytes(rom[hi:e]))}...")
        print(f"  after:  ...{hexdump(bytes(patched[s:lo]))} | {hexdump(bytes(patched[lo:hi]))} | "
              f"{hexdump(bytes(patched[hi:e]))}...")


if __name__ == "__main__":
    main()
