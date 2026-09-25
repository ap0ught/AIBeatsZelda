#!/usr/bin/env python3
"""Watch a run play out in real time, with sound.

The search harness runs unthrottled and silent on purpose - a 4-6 hour search
does not care what 37 minutes of wall clock feels like, and BizHawk's audio
device is pure overhead when nobody is listening. That is why `replay.verify()`
finishes 136,526 frames in about three minutes.

This plays the same inputs at the NES's real 60 fps with audio on, so the run
can just be watched. Same input log, same emulator, same result - only the
throttle and the sound differ.

  python3 watch_run.py                          # the shipped 37:02 run, from power-on
  python3 watch_run.py --seconds 300            # first five minutes only
  python3 watch_run.py --from 40000             # skip ahead silently, then watch

The emulator window is a normal window on your desktop; bring it to the front
and listen. Determinism note: `--from` emulates the skipped frames unthrottled
and only then switches to realtime, which changes nothing but the clock. The
final RAM fingerprint is identical either way - `replay.verify()` proves it.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from zelda import BizHawk, replay

DEFAULT_INPUTS = Path("runs/run6/inputs.txt")
DEFAULT_FINGERPRINT = "3115e31ff1a9b16e732160f81fe478a5052668ff"


def fmt(seconds: float) -> str:
    s = int(round(seconds))
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--inputs", type=Path, default=DEFAULT_INPUTS)
    ap.add_argument("--from", dest="skip", type=int, default=0, metavar="N",
                    help="emulate the first N frames unthrottled, then start watching")
    ap.add_argument("--seconds", type=float, default=0, metavar="S",
                    help="stop after S seconds of realtime playback (0 = play to the end)")
    ap.add_argument("--no-sound", action="store_true")
    ap.add_argument("--expect", default=DEFAULT_FINGERPRINT,
                    help="fingerprint the run must end on (empty string to skip the check)")
    args = ap.parse_args()

    frames = replay.load_inputs(args.inputs)
    total = len(frames)
    print(f"{args.inputs}: {total} frames = {fmt(total / 60)} of game time at 60 fps")

    t0 = time.time()
    with BizHawk(log_name="watch.log", fast=False) as emu:
        # fast=False leaves BizHawk at its configured defaults: frame limiter on,
        # sound on. Say so explicitly anyway - config.ini is user-editable, and a
        # silent run that looks broken is worse than a loud failure.
        emu.cmd("normal" if not args.no_sound else "sound 0")
        print("sound: %s, speed: %s" % ("off" if args.no_sound else "on", "realtime (60 fps)"))
        print("bring the EmuHawk window to the front to watch. Ctrl-C to stop.\n")

        i = 0
        skip = max(0, min(args.skip, total))
        if skip:
            print(f"skipping the first {skip} frames unthrottled (about {skip / 700:.0f}s)...")
            emu.fast()
            while i < skip:
                j = i
                while j < skip and frames[j] == frames[i]:
                    j += 1
                emu.step(frames[i], j - i)
                i = j
            emu.cmd("sound 0" if args.no_sound else "normal")
            print("skipped.\n")

        played = 0.0
        limit_frames = int(args.seconds * 60) if args.seconds else total
        last = time.time()
        while i < min(total, skip + limit_frames):
            j = i
            while j < min(total, skip + limit_frames) and frames[j] == frames[i]:
                j += 1
            emu.step(frames[i], j - i)
            i, played = j, (i - skip) / 60.0
            now = time.time()
            if now - last >= 2.0:
                fps = (i - skip) / max(now - t0 - skip / 700.0, 1e-6)
                print(f"  f{i:>7} / {total}  {fmt(played)}  ({fps:4.1f} fps)", end="\r", flush=True)
                last = now
        print(" " * 70)
        s = emu.state()
        fp = replay.fingerprint(emu)
        complete = i >= total
        print(f"\n{'finished' if complete else 'stopped'} at frame {i}: {s}")
        print(f"  ram sha1 {fp}")
        if not complete:
            # A deliberately truncated watch will not match, and saying MISMATCH
            # would be reporting a bug where the user asked for a preview.
            print(f"  partial run, not checking the fingerprint "
                  f"(played {i - skip} of {total} frames)")
        elif args.expect:
            print("  MATCH" if fp == args.expect else f"  MISMATCH (expected {args.expect})")
            if fp != args.expect:
                return 1
        print(f"  {fmt(played)} watched, {time.time() - t0:.0f}s wall clock")
    return 0


if __name__ == "__main__":
    sys.exit(main())
