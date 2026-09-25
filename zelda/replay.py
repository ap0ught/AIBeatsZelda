"""Replay an input log from power-on in a fresh emulator and compare the final state."""
from __future__ import annotations

from pathlib import Path

from .emulator import BizHawk, State, LOGS_DIR


def load_inputs(path: Path) -> list[tuple[str, ...]]:
    frames = []
    for line in Path(path).read_text().splitlines():
        if line.startswith("#"):
            continue
        frames.append(tuple(b for b in line.split(",") if b))
    return frames


def run_inputs(emu: BizHawk, frames: list[tuple[str, ...]]) -> State:
    """Feed frames, batching runs of identical input into single step calls."""
    i = 0
    s = emu.state()
    while i < len(frames):
        j = i
        while j < len(frames) and frames[j] == frames[i]:
            j += 1
        s = emu.step(frames[i], j - i)
        i = j
    return s


def fingerprint(emu: BizHawk) -> str:
    import hashlib
    return hashlib.sha1(emu.ram(0, 0x800)).hexdigest()


def verify(inputs_path: Path, expected_fp: str | None = None, log=print) -> tuple[State, str]:
    frames = load_inputs(inputs_path)
    with BizHawk(log_name="replay.log") as emu:
        s = run_inputs(emu, frames)
        fp = fingerprint(emu)
        emu.screenshot(Path(inputs_path).stem + "_replay")
    log(f"replayed {len(frames)} frames -> {s}\n  ram sha1 {fp}")
    if expected_fp is not None:
        log("  MATCH" if fp == expected_fp else "  MISMATCH")
    return s, fp
