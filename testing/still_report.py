"""Every stretch of the recorded run where Link stood still in normal play for >= N frames, with the likely
reason: a subscreen trip (Start pressed), a bomb fuse / candle / recorder (B pressed just before), sword swings
(A pressed during it), or nothing at all. The unexplained ones are the planner dithering or waiting.
usage: python still_report.py [min_frames] [top]"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import sys

import record_run

N = int(sys.argv[1]) if len(sys.argv) > 1 else 24
top = int(sys.argv[2]) if len(sys.argv) > 2 else 60
m = record_run.boundaries("fullgame")
ks = sorted(m)
rows = []
with open("logs/fullgame_run.trace.txt", encoding="utf-8", errors="replace") as f:
    for line in f:
        p = line.rstrip("\n").split("\t")
        kv = dict(t.split("=") for t in p[2].split() if "=" in t)
        rows.append((p[1], int(kv["mode"]), int(kv["x"]), int(kv["y"]), int(kv["bitem"])))


def seg_of(fr):
    import bisect
    i = bisect.bisect_right(ks, fr) - 1
    return m[ks[i]] if i >= 0 else "?"


runs = []
j = 1
n = len(rows)
while j < n:
    if rows[j][1] == 5 and (rows[j][2], rows[j][3]) == (rows[j - 1][2], rows[j - 1][3]):
        a = j
        while j < n and rows[j][1] == 5 and (rows[j][2], rows[j][3]) == (rows[a][2], rows[a][3]):
            j += 1
        if j - a >= N:
            btns = {}
            for k in range(a, j):
                for b in rows[k][0].split(","):
                    if b:
                        btns[b] = btns.get(b, 0) + 1
            before = set()
            for k in range(max(0, a - 6), a + 4):
                before |= {b for b in rows[k][0].split(",") if b}
            if "Start" in btns:
                why = "subscreen"
            elif "B" in before or "B" in btns:
                why = f"B item {rows[a][4]} (fuse/flame/tune)"
            elif btns.get("A", 0) >= 2:
                why = "swinging"
            elif not btns:
                why = "NOTHING HELD"
            else:
                why = "pushing " + "/".join(sorted(btns))
            runs.append((j - a, a, seg_of(a), why, btns))
    else:
        j += 1
by = {}
for length, a, seg, why, btns in runs:
    key = why.split(" ")[0] if not why.startswith("B item") else "B item"
    by[key] = by.get(key, 0) + length
print(f"{len(runs)} still stretches >= {N} frames, {sum(r[0] for r in runs)} frames in all:")
for k, v in sorted(by.items(), key=lambda t: -t[1]):
    print(f"   {k:12s} {v:6d}")
print("longest that are neither a subscreen nor a B item:")
shown = 0
for length, a, seg, why, btns in sorted(runs, reverse=True):
    if why == "subscreen" or why.startswith("B item"):
        continue
    print(f"   {length:4d} frames at {a:6d}  {seg:14s} {why}  {btns if btns else ''}")
    shown += 1
    if shown >= top:
        break
