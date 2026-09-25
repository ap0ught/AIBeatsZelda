"""Per-segment hesitation table from the recorded trace: play frames, straight-walk need, standing, self-cancelling
walking, swings, kills, hits. usage: ZELDA_ROUTE=4 python seg_excess.py [top] [trace]"""
import bisect
import sys

import record_run

top = int(sys.argv[1]) if len(sys.argv) > 1 else 40
trace = sys.argv[2] if len(sys.argv) > 2 else "logs/fullgame_run.trace.txt"
m = record_run.boundaries("fullgame")
ks = sorted(m)
rows = []
with open(trace, encoding="utf-8", errors="replace") as f:
    for line in f:
        p = line.rstrip("\n").split("\t")
        kv = dict(t.split("=") for t in p[2].split() if "=" in t)
        rows.append((set(b for b in p[1].split(",") if b and b != "-"), int(kv["mode"]), int(kv["paused"]), int(kv["level"]),
                     int(kv["room"]), int(kv["x"]), int(kv["y"]), int(kv["kills"]), int(kv["hp"])))
n = len(rows)
out = []
for i, k in enumerate(ks):
    a, b = k, (ks[i + 1] if i + 1 < len(ks) else n)
    play = still = swings = kills = hurt = 0
    path = need = 0.0
    sa = None
    for j in range(max(a, 1), min(b, n)):
        r, q = rows[j], rows[j - 1]
        inplay = r[1] == 5 and not r[2]
        if inplay and (sa is None):
            sa = j
        if (not inplay or r[4] != q[4] or j == min(b, n) - 1) and sa is not None:
            e = j if not inplay or r[4] != q[4] else j + 1
            need += (abs(rows[e - 1][5] - rows[sa][5]) + abs(rows[e - 1][6] - rows[sa][6])) / 1.5
            sa = j if (inplay and r[4] != q[4]) else None
        if not inplay:
            continue
        play += 1
        d = abs(r[5] - q[5]) + abs(r[6] - q[6])
        if q[1] == 5 and d <= 8:
            path += d
            still += d == 0
        kills += r[7] > q[7]
        hurt += r[8] < q[8]
        swings += ("A" in r[0]) and ("A" not in q[0])
    out.append((play - need, m[k], b - a, play, need, still, path / 1.5 - need, swings, kills, hurt))
print(f"{'segment':16s} {'total':>6s} {'play':>6s} {'need':>6s} {'excess':>6s} {'still':>6s} {'cancel':>6s} {'swing':>5s} {'kill':>4s} {'hit':>3s}")
for ex, name, tot, play, need, still, canc, sw, ki, hu in sorted(out, reverse=True)[:top]:
    print(f"{name:16s} {tot:6d} {play:6d} {need:6.0f} {ex:6.0f} {still:6d} {canc:6.0f} {sw:5d} {ki:4d} {hu:3d}")
tot_ex = sum(o[0] for o in out)
print(f"sum of excess over all {len(out)} segments: {tot_ex:.0f} frames = {tot_ex / 60.0988 / 60:.1f} min; top {top}: "
      f"{sum(o[0] for o in sorted(out, reverse=True)[:top]):.0f}")
