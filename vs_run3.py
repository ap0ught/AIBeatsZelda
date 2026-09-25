"""Live run against the archived third run (41:15): frames at the newest common checkpoint, and the segments
that differ most so far. usage: python vs_run3.py [top]"""
import glob
import json
import os
import sys

top = int(sys.argv[1]) if len(sys.argv) > 1 else 8


def load(base):
    rows = sorted((json.load(open(f))["frames"], os.path.basename(f)[9:-5], json.load(open(f)).get("hearts"))
                  for f in glob.glob(base + "/fullgame_*.json"))
    out, prev = {}, 0
    for fr, n, h in rows:
        out[n] = (fr, fr - prev, h)
        prev = fr
    return out, [n for _, n, _ in rows]


old, _ = load("logs/archive/third_run_20260919b/checkpoints")
new, order = load("logs/checkpoints")
common = [n for n in order if n in old]
if not common:
    raise SystemExit("no common checkpoints yet")
last = common[-1]
print(f"at {last}: run 4 {new[last][0]} frames ({new[last][2]} hearts)  run 3 {old[last][0]} ({old[last][2]} hearts)  "
      f"delta {new[last][0] - old[last][0]:+d}")
diffs = sorted(((new[n][1] - old[n][1], n, old[n][1], new[n][1]) for n in common), key=lambda t: t[0])
print("biggest gains:", ", ".join(f"{n} {o}->{w} ({d:+d})" for d, n, o, w in diffs[:top]))
print("biggest losses:", ", ".join(f"{n} {o}->{w} ({d:+d})" for d, n, o, w in diffs[::-1][:top] if d > 0))
