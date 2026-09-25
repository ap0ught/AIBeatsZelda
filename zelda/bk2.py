"""Write a BizHawk .bk2 movie from a per-frame input log so EmuHawk can replay / dump it."""
from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path
from typing import Iterable

from .emulator import ROM, LOGS_DIR

# NES controller mnemonics in BizHawk's log order.
ORDER = ("Up", "Down", "Left", "Right", "Select", "Start", "B", "A")
MNEMONIC = {"Up": "U", "Down": "D", "Left": "L", "Right": "R",
            "Select": "s", "Start": "S", "B": "B", "A": "A"}
LOG_KEY = "LogKey:#Reset|Power|#P1 Up|P1 Down|P1 Left|P1 Right|P1 Select|P1 Start|P1 B|P1 A|"


def frame_line(buttons: Iterable[str]) -> str:
    held = set(buttons)
    return "|..|" + "".join(MNEMONIC[b] if b in held else "." for b in ORDER) + "|"


def rom_sha1(rom: Path = ROM) -> str:
    data = rom.read_bytes()
    if data[:4] == b"NES\x1a":
        data = data[16:]   # BizHawk hashes the ROM without the iNES header
    return hashlib.sha1(data).hexdigest().upper()


def write_bk2(frames: list[tuple[str, ...]], out: Path, *, author: str = "AI bot",
              game_name: str = "Legend of Zelda, The", rom: Path = ROM, comment: str = "") -> Path:
    header = "\n".join([
        "MovieVersion BizHawk v2.0.0",
        f"Author {author}",
        "emuVersion Version 2.11.1",
        "OriginalEmuVersion Version 2.11.1",
        "Platform NES",
        f"GameName {game_name}",
        f"SHA1 {rom_sha1(rom)}",
        "rerecordCount 0",
        "Core quickerNES",
        "BoardName MMC1",
    ]) + "\n"
    log = "[Input]\n" + LOG_KEY + "\n" + "\n".join(frame_line(f) for f in frames) + "\n[/Input]\n"
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("Header.txt", header)
        z.writestr("Input Log.txt", log)
        z.writestr("Comments.txt", comment + ("\n" if comment else ""))
        z.writestr("Subtitles.txt", "")
    return out


def from_inputs_file(path: Path, out: Path | None = None, **kw) -> Path:
    from .replay import load_inputs
    frames = load_inputs(path)
    out = out or (LOGS_DIR / (Path(path).name.replace(".inputs.txt", "") + ".bk2"))
    return write_bk2(frames, out, **kw)
