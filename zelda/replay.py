"""Replay an input log from power-on in a fresh emulator and compare the final state."""
from __future__ import annotations

import os
from pathlib import Path

from .emulator import BizHawk, State, LOGS_DIR, ROM, unverified_rom_reason


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


def verify(inputs_path: Path, expected_fp: str | None = None, log=print,
           rom: Path | None = None) -> tuple[State, str]:
    """Replay and report the final state and work-RAM sha1.

    Refuses to run against a cartridge that is not the verified one. A fingerprint is
    only meaningful next to the bytes it was computed from: run6's 3115e31f... belongs
    to md5 614fb308..., and replaying the same inputs on a patched cartridge produces a
    different number that says nothing about the run. Set ZELDA_ALLOW_UNVERIFIED_ROM=1
    to override - that is for working out *why* a patch diverges, and the MISMATCH it
    reports then is the answer, not a failure.
    """
    rom = Path(rom or ROM)
    reason = unverified_rom_reason(rom) if expected_fp is not None else None
    if reason and os.environ.get("ZELDA_ALLOW_UNVERIFIED_ROM") != "1":
        raise SystemExit(
            f"refusing to verify against an unverified cartridge:\n  {reason}\n"
            f"  the expected fingerprint belongs to the verified ROM, so a comparison here\n"
            f"  is meaningless. Restore roms/, point ZELDA_ROM at the stock cartridge, or set\n"
            f"  ZELDA_ALLOW_UNVERIFIED_ROM=1 if finding the divergence is the point.")
    frames = load_inputs(inputs_path)
    with BizHawk(rom=rom, log_name="replay.log") as emu:
        s = run_inputs(emu, frames)
        fp = fingerprint(emu)
        emu.screenshot(Path(inputs_path).stem + "_replay")
    log(f"replayed {len(frames)} frames -> {s}\n  ram sha1 {fp}")
    if expected_fp is not None:
        log("  MATCH" if fp == expected_fp else "  MISMATCH")
    return s, fp
