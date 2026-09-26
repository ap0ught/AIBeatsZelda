"""Summarise what Link did in one segment of the recorded run, from the per-frame trace.

usage: python trace_phases.py <segment> [min_still]
Prints a compressed timeline: stretches where Link stood still (with what was pressed), stretches
where he moved (net displacement), and mode changes. Frames are absolute run frames."""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import bisect
import sys

import record_run

seg = sys.argv[1]
min_still = int(sys.argv[2]) if len(sys.argv) > 2 else 12
m = record_run.boundaries("fullgame")
ks = sorted(m)
i = [m[k] for k in ks].index(seg)
a, b = ks[i], (ks[i + 1] if i + 1 < len(ks) else 10 ** 9)
rows = []
with open("logs/fullgame_run.trace.txt", encoding="utf-8", errors="replace") as f:
    for n, line in enumerate(f, 1):
        if n <= a:
            continue
        if n > b:
            break
        p = line.rstrip("\n").split("\t")
        kv = dict(t.split("=") for t in p[2].split() if "=" in t)
        rows.append((int(p[0]), p[1], int(kv["mode"]), int(kv["x"]), int(kv["y"]), int(kv["hp"]) & 15,
                     int(kv["hpfrac"]), int(kv["room"]), int(kv["bitem"]), int(kv["paused"]), int(kv["keys"]),
                     int(kv["bombs"]), int(kv["rupees"])))
print(f"{seg}: frames {a + 1}-{b} ({len(rows)} frames), room {rows[0][7]:02X} -> {rows[-1][7]:02X}, "
      f"keys {rows[0][10]}->{rows[-1][10]} bombs {rows[0][11]}->{rows[-1][11]} rupees {rows[0][12]}->{rows[-1][12]} "
      f"bitem {rows[0][8]}->{rows[-1][8]}")
# phases
out = []
j = 0
while j < len(rows):
    fr, inp, mode, x, y = rows[j][:5]
    k = j
    if mode != 5:
        while k + 1 < len(rows) and rows[k + 1][2] == mode:
            k += 1
        out.append((rows[j][0], rows[k][0], f"mode {mode:02X}" + (" (paused/subscreen)" if rows[j][9] else "")))
    else:
        # still stretch?
        while k + 1 < len(rows) and rows[k + 1][2] == 5 and rows[k + 1][3:5] == (x, y):
            k += 1
        if k - j + 1 >= min_still:
            presses = {}
            for r in rows[j:k + 1]:
                for bt in r[1].split(","):
                    if bt:
                        presses[bt] = presses.get(bt, 0) + 1
            out.append((rows[j][0], rows[k][0], f"STILL at ({x},{y}) {k - j + 1} fr, pressed {presses or 'nothing'}"))
        else:
            # moving stretch: extend until a long still or a mode change
            k = j
            while k + 1 < len(rows) and rows[k + 1][2] == 5:
                # look ahead for a still run of min_still
                x2, y2 = rows[k + 1][3:5]
                q = k + 1
                while q + 1 < len(rows) and rows[q + 1][2] == 5 and rows[q + 1][3:5] == (x2, y2):
                    q += 1
                if q - (k + 1) + 1 >= min_still:
                    break
                k = q
            a_cnt = sum(1 for r in rows[j:k + 1] if "A" in r[1].split(","))
            b_cnt = sum(1 for r in rows[j:k + 1] if "B" in r[1].split(","))
            path = abs(rows[k][3] - x) + abs(rows[k][4] - y)
            walked = sum(abs(rows[t + 1][3] - rows[t][3]) + abs(rows[t + 1][4] - rows[t][4]) for t in range(j, k))
            out.append((rows[j][0], rows[k][0], f"move ({x},{y})->({rows[k][3]},{rows[k][4]}) {k - j + 1} fr, walked {walked}px net {path}px"
                        + (f", A x{a_cnt // 2}" if a_cnt else "") + (f", B x{b_cnt // 2}" if b_cnt else "")))
    j = k + 1
hp0 = None
for f0, f1, txt in out:
    print(f"  {f0:7d}-{f1:7d} ({f1 - f0 + 1:4d})  {txt}")
h = [(r[5] + (1 if r[6] >= 0x80 else 0.5 if r[6] > 0 else 0)) for r in rows]
print(f"  hearts {h[0]} -> {h[-1]} (min {min(h)})")
