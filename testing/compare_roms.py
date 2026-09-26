"""Does a patched ROM play the same game? Replay identical inputs on both and diff RAM.

    python3 testing/compare_roms.py <stock.nes> <patched.nes> [frames] [run]

Replays the first N frames of a recorded run on each ROM and compares work RAM,
so a cosmetic patch can be told apart from one that perturbs the game. This is
the gate any ROM hack has to pass before it is allowed near a verified run: the
run's whole correctness claim is a RAM fingerprint, and a patch that shifts a
byte breaks it for reasons that have nothing to do with the player.

Reports the first differing address and a count, plus the state fields the bot
actually navigates by. A hack that draws an automap should show differences only
in cartridge WRAM ($6000-$7FFF, where the map buffer lives) and in CHR RAM; a
difference anywhere in $0000-$07FF is a red flag.

Emulators are launched sequentially and closed, so this is safe to run while
nothing else is using BizHawk.
"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib

import sys
from pathlib import Path

from zelda import BizHawk, replay

# Where a cosmetic automap hack is allowed to write.
COSMETIC_RANGES = ((0x6000, 0x8000, "cart WRAM (map buffer)"),)


def replay_to(rom: Path, frames, upto: int, tag: str) -> tuple[bytes, bytes]:
    old = Path("zelda/emulator.py").read_text()
    import os
    os.environ["ZELDA_ROM"] = str(rom)
    import importlib
    import zelda.emulator as E
    importlib.reload(E)
    try:
        with E.BizHawk(log_name=f"cmp_{tag}.log") as emu:
            i = 0
            while i < upto:
                j = i
                while j < len(frames) and frames[j] == frames[i]:
                    j += 1
                emu.step(frames[i], min(j, upto) - i)
                i = min(j, upto)
            st = emu.state()
            print(f"  {tag:8s} f{upto}: mode={st.mode} level={st.level} room={st.room:#04x} "
                  f"pos=({st.x},{st.y}) hearts={st.hearts} bombs={st.bombs} "
                  f"rupees={emu.byte(0x66D)} keys={emu.byte(0x66E)} triforce={emu.byte(0x671):02X}")
            return emu.ram(0x0000, 0x0800), emu.bus(0x6000, 0x2000)
    finally:
        os.environ.pop("ZELDA_ROM", None)
        importlib.reload(E)


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    stock, patched = Path(sys.argv[1]), Path(sys.argv[2])
    upto = int(sys.argv[3]) if len(sys.argv) > 3 else 4000
    name = sys.argv[4] if len(sys.argv) > 4 else "run6"

    src = Path(f"runs/{name}/inputs.txt")
    if not src.exists():
        src = Path(f"logs/{name}.inputs.txt")
    frames = replay.load_inputs(src)
    upto = min(upto, len(frames))
    print(f"replaying {upto} frames of {src} on two ROMs\n")

    a, ac = replay_to(stock, frames, upto, "stock")
    b, bc = replay_to(patched, frames, upto, "patched")

    # Work RAM is the game's own state. Anything different here means the patch
    # changed the game, not the picture.
    diff = [i for i in range(0x800) if a[i] != b[i]]
    print(f"\n$0000-$07FF work RAM: {len(diff)} byte(s) differ")
    if diff:
        print(f"  first ${diff[0]:04X}, last ${diff[-1]:04X}")
        print("  " + ", ".join(f"${d:04X}({a[d]:02X}->{b[d]:02X})" for d in diff[:12])
              + (" ..." if len(diff) > 12 else ""))
        print("  -> the patch changes GAME STATE. It is not cosmetic.")
    else:
        print("  IDENTICAL - the patch leaves the game's own state alone on this path")

    # Cartridge WRAM is where a map buffer would live, and is expected to differ.
    cdiff = [i for i in range(0x2000) if ac[i] != bc[i]]
    print(f"\n$6000-$7FFF cart WRAM: {len(cdiff)} byte(s) differ"
          + (f", first ${0x6000 + cdiff[0]:04X}, last ${0x6000 + cdiff[-1]:04X}" if cdiff else ""))
    if cdiff:
        print("  -> this is where an automap would draw, so differences here are expected")

    if not diff:
        print("\nVERDICT: same game, different picture. Safe to *watch*, "
              "not safe to verify against.")


if __name__ == "__main__":
    main()
