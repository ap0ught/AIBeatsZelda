"""Whole-run accounting from the recorded per-frame trace: for each segment, how many frames Link was in normal
play (mode 5, unpaused), how many of those he stood still with no button that explains it, and how many frames
were not play at all (scrolls, menus, caves, cutscenes). Sorted by idle frames.
usage: python idle_report.py [top_n]"""
import sys

import record_run

top = int(sys.argv[1]) if len(sys.argv) > 1 else 40
import json
m = {int(k): v for k, v in json.load(open("logs/run3a_marks.json")).items()}
ks = sorted(m)
rows = []
with open("logs/fullgame_run.trace.txt", encoding="utf-8", errors="replace") as f:
    for line in f:
        p = line.rstrip("\n").split("\t")
        kv = dict(t.split("=") for t in p[2].split() if "=" in t)
        rows.append((p[1], int(kv["mode"]), int(kv["x"]), int(kv["y"]), int(kv["paused"])))
n = len(rows)
out = []
tot = {"play": 0, "still": 0, "idle": 0, "nonplay": 0}
for i, k in enumerate(ks):
    a, b = k, (ks[i + 1] if i + 1 < len(ks) else n)
    play = still = idle = nonplay = 0
    for j in range(max(a, 1), min(b, n)):
        btn, mode, x, y, paused = rows[j]
        if mode != 5 or paused:
            nonplay += 1
            continue
        play += 1
        if (x, y) == (rows[j - 1][2], rows[j - 1][3]):
            still += 1
            if not btn or btn in ("", "-"):
                idle += 1
    out.append((idle, still, play, nonplay, m[k], b - a))
    tot["play"] += play; tot["still"] += still; tot["idle"] += idle; tot["nonplay"] += nonplay
print(f"run: {n} frames; play {tot['play']}, standing still in play {tot['still']} "
      f"({100 * tot['still'] / max(1, tot['play']):.0f}%), of which no button held {tot['idle']}; "
      f"not play (scrolls, menus, caves, cutscenes) {tot['nonplay']}")
print(f"{'segment':16s} {'frames':>6s} {'play':>6s} {'still':>6s} {'idle':>6s} {'nonplay':>7s}")
for idle, still, play, nonplay, name, length in sorted(out, reverse=True)[:top]:
    print(f"{name:16s} {length:6d} {play:6d} {still:6d} {idle:6d} {nonplay:7d}")
