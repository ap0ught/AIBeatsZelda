"""Apply an IPS patch to a base NES ROM.

    python3 testing/patch_rom_ips.py <base.nes> <hack.IPS> <out.nes>

Never writes over the base ROM. The output goes where you say, and the base's
MD5 is printed before and after so you can prove it was not touched.

Padding
-------
An IPS is a list of writes against the *file*, with no declared length. If the
highest write lands past the end of the base - which happens when a hack was
authored against a slightly different revision - the file is extended with zeros
to cover it. That is what every IPS patcher does. `Automap0.2.IPS` needs
$20012 bytes and stock Rev 1 is $20010, so it is short by exactly 2.

Legal note: this only transforms a ROM you already have into a ROM you already
had, for local study. The output is not redistributable, and `*.nes` is
gitignored here so it cannot be committed by accident. Keep patched ROMs outside
the repo.
"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib

import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ips_decode import decode          # noqa: E402  (needs the path set above)


def md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    base, ips, out = (Path(a) for a in sys.argv[1:4])
    for p in (base, ips):
        if not p.exists():
            raise SystemExit(f"no such file: {p}")

    before = md5(base)
    recs, trunc = decode(ips.read_bytes())
    data = bytearray(base.read_bytes())
    hi = max(o + len(d) for o, d in recs)

    print(f"base   {base.name}  {len(data)} bytes  md5 {before}")
    print(f"patch  {ips.name}  {len(recs)} record(s), {sum(len(d) for _, d in recs)} bytes"
          f", highest write ${hi:05X}")

    padded = 0
    if hi > len(data):
        padded = hi - len(data)
        data.extend(b"\x00" * padded)
        print(f"       base is short by {padded} byte(s); extending to ${len(data):05X}")
    for off, d in recs:
        data[off:off + len(d)] = d
    if trunc:
        data = data[:trunc]

    if out.exists():
        raise SystemExit(f"refusing to overwrite {out}")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(bytes(data))
    after = md5(base)

    print(f"wrote  {out}  {len(data)} bytes  md5 {md5(out)}")
    print(f"base   md5 {after}  {'UNCHANGED' if after == before else '*** CHANGED ***'}")
    if data[:4] == b"NES\x1a":
        print(f"       header: PRG {data[4] * 16}K  CHR {data[5] * 8}K  "
              f"mapper {((data[6] >> 4) | (data[7] & 0xF0)):03d}")


if __name__ == "__main__":
    main()
