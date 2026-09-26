"""Find the frame a cartridge stops surviving, with progress and a screenshot at the end.

    python3 testing/find_death_frame.py [inputs] [every] [rom]

Replays an input log and reports progress every N frames, then the exact frame the
bridge dropped - with a screenshot of the last good state, so the failure has a
picture attached.

Written because a patched cartridge that boots and plays for a while is much
harder to diagnose than one that fails at once, and "it is not working" needs a
frame number before it needs a theory. EmuHawk exiting with code 0 is not a crash
message; it just means the bridge stopped answering.

Progress goes to stdout unbuffered, so run it detached and tail the file:

    nohup python3 -u testing/find_death_frame.py > /tmp/death.txt 2>&1 &
"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib

import sys
import time
from pathlib import Path

from zelda import BizHawk, replay
from zelda.emulator import ROM

inputs = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("runs/run6/inputs.txt")
every = int(sys.argv[2]) if len(sys.argv) > 2 else 2000
rom = Path(sys.argv[3]) if len(sys.argv) > 3 else ROM

frames = replay.load_inputs(inputs)
print(f"cartridge : {rom}")
print(f"md5       : {__import__('hashlib').md5(rom.read_bytes()).hexdigest()}")
print(f"input log : {inputs}  ({len(frames)} frames)")
print(f"progress  : every {every} frames", flush=True)

t0 = time.time()
i = 0
last_good = 0
last_state = None
try:
    with BizHawk(rom=rom, log_name="deathframe.log") as emu:
        print("  connected", flush=True)
        while i < len(frames):
            j = i
            while j < len(frames) and frames[j] == frames[i]:
                j += 1
            last_state = emu.step(frames[i], j - i)
            i = j
            last_good = i
            if i % every < (j - i):
                el = time.time() - t0
                rate = i / el if el else 0
                print(f"  f{i:>7}  {last_state}  {rate:6.0f} f/s  "
                      f"eta {(len(frames) - i) / rate / 60:5.1f} min", flush=True)
        print(f"\nSURVIVED the whole log: {len(frames)} frames", flush=True)
        print(f"  final state {emu.state()}", flush=True)
        print(f"  ram sha1 {replay.fingerprint(emu)}", flush=True)
        print("  shot:", emu.screenshot("deathframe_end"), flush=True)
except Exception as e:
    el = time.time() - t0
    print(f"\nDIED after {last_good} frames ({el:.0f}s, {last_good / el:.0f} f/s)",
          flush=True)
    print(f"  last good state: {last_state}", flush=True)
    print(f"  {type(e).__name__}: {e}", flush=True)
    print(f"  reached {last_good / len(frames) * 100:.1f}% of the log", flush=True)
    print("  see logs/deathframe.log", flush=True)
