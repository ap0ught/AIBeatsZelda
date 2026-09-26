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

Emulators are launched sequentially and closed. If a previous run was killed
mid-flight, an orphaned EmuHawk can still hold the bridge port and this will hang
silently after printing its header - check `pgrep -af EmuHawk` first.

Note on cart WRAM: this harness runs BizHawk's NullHawk core, which logs
"NullHawk does not implement memory domains", so `bus()` / `ram_domain()` cannot
read $6000-$7FFF at all. An earlier version of this script tried to and simply
hung. It is not a gap worth filling: the run's fingerprint is a sha1 over work
RAM only, so work RAM is the entire question.
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


def replay_to(rom: Path, frames, upto: int, tag: str) -> bytes:
    # Pass the cartridge straight to the constructor. An earlier version swapped it by
    # setting ZELDA_ROM and calling importlib.reload() on zelda.emulator, which is both
    # unnecessary - BizHawk takes rom= - and destructive: reloading the module mid-session
    # re-runs its module-level side effects and changes the class identity the caller
    # already holds, which showed up as BizHawk failing to load the ROM at all.
    try:
        with BizHawk(rom=rom, log_name=f"cmp_{tag}.log") as emu:
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
            return emu.ram(0x0000, 0x0800)
    except FileNotFoundError:
        raise SystemExit(f"no such ROM: {rom}")


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

    a = replay_to(stock, frames, upto, "stock")
    b = replay_to(patched, frames, upto, "patched")

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

    print("\n$6000-$7FFF cart WRAM: not checked - NullHawk does not implement memory")
    print("  domains, so ram_domain/bus cannot read it. It does not matter here: the")
    print("  fingerprint is sha1 over $0000-$07FF only (zelda/replay.py), so work RAM is")
    print("  the whole question. A cosmetic hack's map buffer lives in cart WRAM and is")
    print("  invisible to the bot by construction.")

    if not diff:
        print("\nVERDICT: same game, different picture. Safe to *watch*, "
              "not safe to verify against.")


if __name__ == "__main__":
    main()
