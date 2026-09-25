"""Calibrate the overworld router against the third run's own overworld crossings."""
import glob, json, os, re, time
from zelda import owroute

rows = []
for f in glob.glob("logs/checkpoints/fullgame_*.json"):
    d = json.load(open(f))
    m = re.search(r"mode=(\w\w)/\w\w L(\d) room=([0-9a-f]{2}) pos=\((\d+),(\d+)\)", d["summary"])
    rows.append((d["frames"], os.path.basename(f)[9:-5], int(m.group(1), 16), int(m.group(2)), int(m.group(3), 16),
                 int(m.group(4)), int(m.group(5)), d.get("hearts")))
rows.sort()
legs = []
for (f0, n0, mo0, l0, r0, x0, y0, h0), (f1, n1, mo1, l1, r1, x1, y1, h1) in zip(rows, rows[1:]):
    if l0 == 0 and l1 == 0 and mo0 == 5 and mo1 == 5 and r0 != r1 and (abs((r0 & 15) - (r1 & 15)) + abs((r0 >> 4) - (r1 >> 4))) == 1:
        legs.append((n1, r0, x0, y0, r1, x1, y1, f1 - f0))
print(len(legs), "single-screen overworld crossings in the run")
t0 = time.time()
res = []
for n, r0, x0, y0, r1, x1, y1, fr in legs:
    ladder = True          # distances barely differ; bridges only add options
    a = owroute.nearest_free(r0, x0, y0, ladder)
    if a is None:
        continue
    d, end, rooms = owroute.leg(a, r1, ladder)
    if d is None:
        res.append((n, fr, None, r0, r1)); continue
    horiz = (r0 >> 4) == (r1 >> 4)
    walk = d - (owroute.SCROLL_H if horiz else owroute.SCROLL_V)
    res.append((n, fr, walk, horiz))
print(f"routed in {time.time()-t0:.1f}s")
bad = [r for r in res if r[2] is None]
print("unroutable:", [(r[0], hex(r[3]), hex(r[4])) for r in bad])
ok = [r for r in res if r[2] is not None]
for horiz in (True, False):
    xs = [(fr - walk) for n, fr, walk, h in ok if h == horiz]
    xs.sort()
    print("horizontal" if horiz else "vertical", "crossings:", len(xs), " overhead (actual - walking) median", xs[len(xs)//2],
          " p25", xs[len(xs)//4], " p75", xs[3*len(xs)//4], " min", xs[0])
