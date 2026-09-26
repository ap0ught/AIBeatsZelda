"""Per-frame rupee trace around the compass/map transitions. Is a 15-rupee map
purchase actually happening, and if so how far from the bit change?

    python3 testing/probe_map_window.py [run] [centre_frame ...]

Why this exists
---------------
`testing/probe_map.py` found that $0668's bits change with no rupee movement,
which argues the bits are not a map purchase. But its reads are sampled once per
run of identical inputs, and the on-screen rupee counter *animates* on a
transaction: sampling a 60-rupee purchase can yield -3 then -57, and a 15-rupee
purchase can look like a scatter of -1s. So "no rupees moved" is not yet proof
of "nothing was bought" - it may only mean the movement fell between samples.

This samples $066D every single frame in a window around each centre, which
resolves the animation, and reports the exact trajectory plus whether the net
change over the window equals a map (15) or a compass (15).

Frames are 0-based and a screenshot is taken at each end of the window, so the
before/after state can be checked by eye.

Per the user's references, which are the canonical source for these encodings:
  https://datacrystal.tcrf.net/wiki/The_Legend_of_Zelda/RAM_map
  https://datacrystal.tcrf.net/wiki/The_Legend_of_Zelda/Notes
Both are Cloudflare-gated to scripted requests; archive.org snapshots are
recorded in zelda/ram.py.
"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib

import sys
from pathlib import Path

from zelda import BizHawk, ram, replay

MAP_PRICE = 15
WIN = 900          # frames either side of each centre

name = sys.argv[1] if len(sys.argv) > 1 else "run6"
centres = [int(a) for a in sys.argv[2:]] or [9853, 92997]

frames = replay.load_inputs(Path(f"runs/{name}/inputs.txt"))
print(f"{name}: {len(frames)} frames; per-frame window trace, +/-{WIN} around "
      f"{centres}")

for centre in centres:
    lo, hi = max(0, centre - WIN), min(len(frames), centre + WIN)
    trace: list[tuple[int, int, int, int]] = []   # frame, rupees, compass, map
    with BizHawk(log_name=f"mapwin_{centre}.log") as emu:
        # bulk fast-forward to the window, then read every single frame inside it
        i = 0
        while i < lo:
            j = i
            while j < len(frames) and frames[j] == frames[i]:
                j += 1
            emu.step(frames[i], min(j, lo) - i)
            i = min(j, lo)
        while i <= hi:
            emu.step(frames[i], 1)
            trace.append((i, emu.byte(ram.RUPEES), emu.byte(ram.COMPASS),
                          emu.byte(ram.MAP)))
            i += 1
        before = str(emu.screenshot(f"mapwin_f{lo:06d}_before"))
        after = str(emu.screenshot(f"mapwin_f{hi:06d}_after"))

    if not trace:
        print(f"  centre f{centre}: window empty")
        continue

    r0, r1 = trace[0][1], trace[-1][1]
    c0, c1 = trace[0][2], trace[-1][2]
    m0, m1 = trace[0][3], trace[-1][3]
    print(f"\n=== centre f{centre}  window f{lo}..f{hi} ({len(trace)} frames) ===")
    print(f"  rupees ${ram.RUPEES:02X}: {r0} -> {r1}   net {r1 - r0:+d}"
          + ("   <- 15, consistent with a map or compass" if r1 - r0 == -MAP_PRICE else ""))
    print(f"  compass ${ram.COMPASS:02X}: {c0:02X} -> {c1:02X}")
    print(f"  map     ${ram.MAP:02X}: {m0:02X} -> {m1:02X}")

    # every frame where the map or compass byte changes, with the rupees around it
    for k in range(1, len(trace)):
        f, rp, cp, mp = trace[k]
        pf, prp, pcp, pmp = trace[k - 1]
        if (cp, mp) != (pcp, pmp):
            bits = [b + 1 for b in range(8) if (mp >> b) & 1 and not (pmp >> b) & 1]
            print(f"  f{f}: compass {pcp:02X}->{cp:02X}  map {pmp:02X}->{mp:02X}  "
                  f"gained L{',L'.join(map(str, bits)) or '-'}  "
                  f"rupees {prp}->{rp} ({rp - prp:+d})")
            lo_i = max(0, k - 12)
            print(f"        rupees leading up: "
                  f"{[t[1] for t in trace[lo_i:k + 1]]}")

    # distinct rupee values in the window, and how long each was held
    holds: list[tuple[int, int, int]] = []      # value, first frame, count
    for f, rp, _, _ in trace:
        if holds and holds[-1][0] == rp:
            holds[-1] = (rp, holds[-1][1], holds[-1][2] + 1)
        else:
            holds.append((rp, f, 1))
    print(f"  rupee holds: " + "  ".join(
        f"{v}@{st}({c}f)" for v, st, c in holds if c >= 3))
    print(f"  shots: {before.split('/')[-1]}  {after.split('/')[-1]}")
