"""Replay an input log one frame at a time and record the full state line for every frame."""
from __future__ import annotations

from pathlib import Path

from .emulator import BizHawk, LOGS_DIR
from .replay import load_inputs


def trace(inputs_path: Path, out: Path | None = None) -> Path:
    frames = load_inputs(inputs_path)
    out = out or (LOGS_DIR / (Path(inputs_path).name.replace(".inputs.txt", "") + ".trace.txt"))
    with BizHawk(log_name="trace.log") as emu, open(out, "w") as f:
        s = emu.state()
        f.write(f"{s.frame}\t\t{emu.cmd('state')}\n")
        for btn in frames:
            s = emu.step(btn, 1)
            f.write(f"{s.frame}\t{','.join(btn)}\t{emu.cmd('state')}\n")
    return out


if __name__ == "__main__":
    import sys
    print(trace(Path(sys.argv[1])))
