"""Where the frames go in the current full-game run: per-segment cost from the checkpoint chain, the most
expensive segments, and totals by area. Usage: python seg_costs.py [top_n]"""
import glob
import json
import os
import re
import sys

top = int(sys.argv[1]) if len(sys.argv) > 1 else 40
rows = []
for f in glob.glob("logs/checkpoints/fullgame_*.json"):
    d = json.load(open(f))
    rows.append((d["frames"], os.path.basename(f)[len("fullgame_"):-5], d.get("hearts"), d.get("keys"), d.get("bombs")))
rows.sort()
prev = 0
segs = []
for fr, name, h, k, b in rows:
    segs.append((fr - prev, name, fr, h, k, b))
    prev = fr


def area(n: str) -> str:
    m = re.match(r"(l\d|g9|m9|s9|r\d|p\d|w\d|wl\d|dm9|hc|ms|sw|sh\d|cave|buy)", n)
    return m.group(1) if m else n.split("_")[0]


print(f"{len(segs)} segments, {prev} frames = {prev / 60.0988 / 60:.1f} min")
print("--- most expensive")
for c, n, fr, h, k, b in sorted(segs, reverse=True)[:top]:
    print(f"  {n:16s} {c:6d}   at {fr:7d}  hearts {h} keys {k} bombs {b}")
tot = {}
for c, n, *_ in segs:
    tot[area(n)] = tot.get(area(n), 0) + c
print("--- by area")
for a, c in sorted(tot.items(), key=lambda t: -t[1])[:30]:
    print(f"  {a:8s} {c:7d}  {c / 60.0988:6.0f} s")
