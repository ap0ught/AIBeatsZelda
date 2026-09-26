"""What the viewer sees as hesitation. From the per-frame trace of the recorded run:

  stretches : maximal runs of frames in normal play (mode 5, unpaused) inside one room
  need      : frames a straight walk of the stretch's net displacement takes (1.5 px a frame)
  excess    : frames beyond that - standing, walking that cancels itself out (around things, back and forth), fighting

Stretches are split into FIGHT (a kill or a sword swing happened), ITEM (B used: bomb fuse, candle, recorder) and
TRANSIT (neither). TRANSIT excess is pure overhead: nothing had to die, Link only had to get across.

  loiter    : episodes where Link's net movement over 1.5 s is under 16 px with no A/B/Start pressed - 'thinking'

usage: ZELDA_ROUTE=4 python progress_audit.py [top]"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import bisect
import sys

import record_run

top = int(sys.argv[1]) if len(sys.argv) > 1 else 25
FPS = 60.0988
m = record_run.boundaries("fullgame")
ks = sorted(m)


def seg_of(fr):
    i = bisect.bisect_right(ks, fr) - 1
    return m[ks[i]] if i >= 0 else "?"


def ts(fr):
    s = fr / FPS
    return f"{int(s // 60):2d}:{s % 60:04.1f}"


rows = []
with open("logs/fullgame_run.trace.txt", encoding="utf-8", errors="replace") as f:
    for line in f:
        p = line.rstrip("\n").split("\t")
        kv = dict(t.split("=") for t in p[2].split() if "=" in t)
        rows.append((set(b for b in p[1].split(",") if b and b != "-"), int(kv["mode"]), int(kv["paused"]), int(kv["level"]),
                     int(kv["room"]), int(kv["x"]), int(kv["y"]), int(kv["kills"]), int(kv["hp"])))
n = len(rows)
zelda = max(ks)                       # last boundary ~ end of play; fine for totals

# ---- stretches
st = []
j = 0
while j < n:
    b, mode, paused, lvl, room = rows[j][:5]
    if mode == 5 and not paused:
        a = j
        while j < n and rows[j][1] == 5 and not rows[j][2] and rows[j][3] == lvl and rows[j][4] == room:
            j += 1
        st.append((a, j))
    else:
        j += 1

tot = {"FIGHT": [0, 0, 0, 0], "ITEM": [0, 0, 0, 0], "TRANSIT": [0, 0, 0, 0]}   # frames, need, still, detour
worst = []
for a, e in st:
    if e - a < 4:
        continue
    path = still = kills = swings = bs = hurt = 0
    for k in range(a + 1, e):
        dx = abs(rows[k][5] - rows[k - 1][5]); dy = abs(rows[k][6] - rows[k - 1][6])
        if dx + dy > 8:                # a warp / knock-through inside one stretch: not walking
            continue
        path += dx + dy
        still += (dx + dy == 0)
        kills += rows[k][7] > rows[k - 1][7]
        hurt += rows[k][8] < rows[k - 1][8]
        swings += ("A" in rows[k][0]) and ("A" not in rows[k - 1][0])
        bs += ("B" in rows[k][0]) and ("B" not in rows[k - 1][0])
    net = abs(rows[e - 1][5] - rows[a][5]) + abs(rows[e - 1][6] - rows[a][6])
    need = net / 1.5
    kind = "FIGHT" if (kills or swings) else ("ITEM" if bs else "TRANSIT")
    t = tot[kind]
    t[0] += e - a; t[1] += need; t[2] += still; t[3] += max(0, path - net) / 1.5
    worst.append(((e - a) - need, kind, a, e, still, (path - net) / 1.5, kills, swings, hurt))

play = sum(t[0] for t in tot.values())
print(f"run {n} frames = {ts(n)}; normal play {play} = {ts(play)}; everything else (scrolls, menus, caves, fanfares) {n - play} = {ts(n - play)}")
print(f"{'kind':8s} {'frames':>7s} {'time':>7s} {'straight-walk need':>19s} {'excess':>7s} {'= standing':>11s} {'+ cancelled walking':>20s}")
for kind, (fr, need, still, det) in tot.items():
    print(f"{kind:8s} {fr:7d} {ts(fr):>7s} {need:19.0f} {fr - need:7.0f} {still:11d} {det:20.0f}")

print(f"\nTRANSIT stretches (nothing killed, no swing, no item) with the most excess - 'going around' and 'thinking':")
print(f"{'video':>7s} {'segment':16s} {'frames':>6s} {'excess':>6s} {'still':>5s} {'cancelled':>9s} {'hit':>3s}")
for ex, kind, a, e, still, det, kills, swings, hurt in sorted((w for w in worst if w[1] == "TRANSIT"), reverse=True)[:top]:
    print(f"{ts(a):>7s} {seg_of(a):16s} {e - a:6d} {ex:6.0f} {still:5d} {det:9.0f} {hurt:3d}")

# ---- loiter episodes
W, R = 90, 16
lo = []
j = 0
flag = [False] * n
for k in range(W, n):
    ok = all(rows[q][1] == 5 and not rows[q][2] for q in (k - W, k)) and rows[k][4] == rows[k - W][4]
    if not ok:
        continue
    if abs(rows[k][5] - rows[k - W][5]) + abs(rows[k][6] - rows[k - W][6]) >= R:
        continue
    if any(rows[q][1] != 5 or rows[q][2] or (rows[q][0] & {"A", "B", "Start"}) for q in range(k - W, k + 1)):
        continue
    for q in range(k - W, k + 1):
        flag[q] = True
k = 0
while k < n:
    if flag[k]:
        a = k
        while k < n and flag[k]:
            k += 1
        lo.append((k - a, a))
    else:
        k += 1
print(f"\nloiter (under {R}px of progress in {W} frames, no A/B/Start): {len(lo)} episodes, {sum(l for l, _ in lo)} frames = {ts(sum(l for l, _ in lo))}")
for length, a in sorted(lo, reverse=True)[:top]:
    print(f"  {ts(a):>7s} {seg_of(a):16s} {length:5d} frames ({length / FPS:4.1f}s)")

# ---- short stops
b = {"4-7": 0, "8-15": 0, "16-23": 0, "24-59": 0, "60+": 0}
c = dict.fromkeys(b, 0)
k = 1
while k < n:
    if rows[k][1] == 5 and not rows[k][2] and rows[k][5:7] == rows[k - 1][5:7] and not (rows[k][0] & {"A", "B", "Start"}):
        a = k
        while k < n and rows[k][1] == 5 and not rows[k][2] and rows[k][5:7] == rows[a][5:7] and not (rows[k][0] & {"A", "B", "Start"}):
            k += 1
        L = k - a
        key = "4-7" if 4 <= L < 8 else "8-15" if 8 <= L < 16 else "16-23" if 16 <= L < 24 else "24-59" if 24 <= L < 60 else "60+" if L >= 60 else None
        if key:
            b[key] += L; c[key] += 1
    else:
        k += 1
print("\nstops with no A/B/Start held, by length (count, frames):", {k2: (c[k2], b[k2]) for k2 in b}, "total", sum(b.values()), "=", ts(sum(b.values())))
