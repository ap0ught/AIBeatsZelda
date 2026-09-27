"""Which cartridge this process is asserting, and where everything in it lives.

    python3 -c "from zelda.profile import active; print(active().describe())"

Stage 0a of #9. The goal is that every fact which is *true of one cartridge* is named,
measured and recorded as such, rather than scattered through the code as literals — and
that "which cartridge is this process asserting?" is answered by reading one object rather
than by grepping for a filename.

## Why this exists when `emulator.py` already has `ROM`

Because `ROM` is a `Path` and this is an *identity plus a geometry*. Three defects made the
difference concrete, and all three are cache-shaped:

1. `owmap.py` did `ROM_PATH = ROM` at **import time**, so a `ZELDA_ROM` set after import
   was ignored — the module had already captured the stock path.
2. `romdata.py` cached the ROM bytes in a bare module global `_rom`, forever, with no key.
3. `owmap.py` cached the PRG behind `@lru_cache(maxsize=1)`. `maxsize=1` is not a cache key;
   it is a cache *size*. Swap the ROM and the old bytes are still there, so a two-cartridge
   workflow in one process silently serves the first cartridge's geometry — the same
   failure shape as FINDINGS §3.3, where a patched ROM under the stock filename made the
   project's central claim quietly unreproducible.

So the property being protected is not "global versus local". It is that **the cache key
includes the cartridge identity**, and that the selection is recorded rather than inferred.
Every cache here is keyed on the md5.

## Geometry is per-md5, and an unknown cartridge falls back rather than refusing

`GEOMETRY` is keyed by md5, because that is the shape that supports a second cartridge
without touching anything else. There is one entry, for stock Rev 1.

An **unknown** cartridge deliberately falls back to the stock geometry with
`matched=False` set, and still decodes. That is not a gap, it is the point of doing 0a
before 0b: refusing here would be a behaviour change, and #9's 0a gate is "decode output
must be byte-identical to today, the expected answer being *no change at all, provably*".
A patched ROM must keep decoding the way it does now — wrongly, but observably — so that
the refusal is a separate, deliberate change with its own gate. `describe()` and every
gate run print the md5, so a fallback cannot pass unnoticed.

## What is deliberately NOT here yet

- **No RAM addresses.** Those are Stage 0b, and they are behaviour-risking: they rewired
  twenty sites the route's success predicates depend on. Doing them in the same change as
  the geometry would make a divergence untraceable.
- **No provenance stamps** on `knowledge/*.json` (Stage 1).
- **No gate command** (Stage 2). Note that it must not be a daemon: concurrent BizHawk
  instances contend for the single `.bridge_port`, so a background replay loop collides
  with real work and produces exactly the silent hang FINDINGS §3.2 describes.
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path

from .emulator import ROM, ROM_NAME, VERIFIED_ROM_MD5, _ROM_CANDIDATES

# iNES header: 16 bytes, so PRG content starts here. Both decoders hardcoded 16.
HEADER = 16


@dataclass(frozen=True)
class Geometry:
    """Where things live inside one cartridge's PRG. Every field is a property of the
    cartridge, not of the harness, which is exactly why it is named rather than inlined."""

    # RoomLayoutsOW - 16 bytes per screen id, the overworld tile layout
    ow_layouts: int = 0x15418
    # the 16-entry column directory that locates each screen block
    ow_col_dir: int = 0x19D0F
    # primary/secondary square tables, 12 bytes in, 0x38 then 64
    ow_squares: int = 0x16970
    ow_squares_skip: int = 12
    # the lightning / screen-effect table
    ow_effects: int = 0x18400
    # Armos: 7 item bytes then 7 tile bytes
    armos: int = 0x10CB2
    # the 128-room dungeon grid, shared by levels 1-6; levels 7-9 follow it
    room_tables: int = 0x18700
    room_tables_l7_9: int = 0x18700 + 0x300
    # bytes per room-column stride inside those tables
    room_stride: int = 0x80


# One entry. A second cartridge adds a row here and nothing else changes shape.
GEOMETRY: dict[str, Geometry] = {
    VERIFIED_ROM_MD5: Geometry(),
}


@dataclass(frozen=True)
class Profile:
    """An immutable answer to "which cartridge is this?" - identity, not a path."""

    path: Path
    md5: str
    geometry: Geometry
    matched: bool          # False: this md5 has no geometry of its own, stock was used

    @property
    def name(self) -> str:
        return self.path.name

    def describe(self) -> str:
        """One line, for every gate to print. A run that cannot say which cartridge it
        asserted is not a run whose numbers mean anything."""
        return (f"{self.md5}  {'matched' if self.matched else 'UNRECOGNISED, stock geometry'}  "
                f"{self.path}")

    def unverified_reason(self) -> str | None:
        """Why this is not the cartridge run6 was measured on, or None."""
        if self.md5 == VERIFIED_ROM_MD5:
            return None
        return (f"{self.path}\n  md5 {self.md5}\n  expected {VERIFIED_ROM_MD5} "
                f"(No-Intro USA Rev 1)\n  this is not the cartridge the run6 fingerprint "
                f"was computed on; anything measured with it is a different game")


def candidate_paths() -> tuple[Path, ...]:
    return _ROM_CANDIDATES


def selected_path() -> Path:
    """Which cartridge, resolved NOW rather than at import.

    The import-time capture was defect 1: `ZELDA_ROM` set after `import zelda.owmap` was
    ignored, because the module had already read the environment and stored the result.
    Resolving per call is what makes a two-cartridge workflow possible in one process.
    """
    env = os.environ.get("ZELDA_ROM")
    if env:
        return Path(env)
    return next((p for p in _ROM_CANDIDATES if p.exists()), _ROM_CANDIDATES[0])


def _md5(path: Path) -> str:
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


_by_path: dict[str, Profile] = {}


def resolve(path: Path | str | None = None) -> Profile:
    """The profile for a cartridge, built once per distinct path.

    Cached on the *resolved path string*, so asking again is free and asking for a
    different cartridge builds a different one. The old `lru_cache(maxsize=1)` could not
    express "a different cartridge" at all.
    """
    p = Path(path) if path is not None else selected_path()
    key = str(p.resolve() if p.exists() else p)
    prof = _by_path.get(key)
    if prof is None:
        md5 = _md5(p)
        geom = GEOMETRY.get(md5)
        prof = Profile(path=p, md5=md5, geometry=geom or GEOMETRY[VERIFIED_ROM_MD5],
                       matched=geom is not None)
        _by_path[key] = prof
    return prof


def active() -> Profile:
    """The profile for whatever `ZELDA_ROM` currently selects."""
    return resolve(None)


# ---- cartridge bytes, cached on identity -------------------------------------------
# The point of keying on md5 rather than on a bare global or a maxsize: a second cartridge
# in the same process gets its own entry, and neither can serve the other's bytes.
_bytes_by_md5: dict[str, bytes] = {}
_prg_by_md5: dict[str, bytes] = {}


def rom_bytes(profile: Profile | None = None) -> bytes:
    prof = profile or active()
    data = _bytes_by_md5.get(prof.md5)
    if data is None:
        data = Path(prof.path).read_bytes()
        _bytes_by_md5[prof.md5] = data
    return data


def prg(profile: Profile | None = None) -> bytes:
    """PRG content, i.e. the cartridge minus the iNES header."""
    prof = profile or active()
    data = _prg_by_md5.get(prof.md5)
    if data is None:
        data = rom_bytes(prof)[HEADER:]
        _prg_by_md5[prof.md5] = data
    return data


def keyed_cache(fn):
    """Memoize on `(cartridge md5, *args)`.

    Two `lru_cache(maxsize=None)` decorators in `owmap.py` were keyed on the room alone,
    with no cartridge in the key. The Stage 0a byte-identical gate did **not** catch that:
    with one cartridge in the process, a missing key makes no difference. It only shows up
    when a second cartridge is decoded in the same process, which is precisely the case
    nobody was testing.

    The md5 is read *here* rather than passed by the caller on purpose. A cache keyed on
    `(md5, room)` where each call site supplies the md5 is one forgotten argument away from
    silently serving the wrong cartridge's geometry again - the same defect, moved. Reading
    it inside the wrapper means a call site cannot get it wrong.
    """
    store: dict = {}

    def wrapper(*args):
        key = (active().md5, args)
        if key not in store:
            store[key] = fn(*args)
        return store[key]

    wrapper.__name__ = fn.__name__
    wrapper.__doc__ = fn.__doc__
    wrapper.cache_clear = store.clear          # for tests, and for bounding memory
    wrapper.__wrapped__ = fn
    return wrapper
