"""The overworld explored with bookmarks (day one): the real trace of the exploration session (logs/explore_L3.trace.txt),
drawn as a map graph growing screen by screen - a node lights when a screen is first entered, an edge when Link walks
from one to the next, and a jump back to a bookmark is drawn as a dashed return. Ends on the seven-screen route.
usage: python youtube/gfx_explore.py [out.mp4]"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).parent))
import gfx
from build import render_frames

out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("youtube/clips_v3/explore_graph.mp4")
out.parent.mkdir(parents=True, exist_ok=True)
rows = []
with open("logs/explore_L3.trace.txt", encoding="utf-8", errors="replace") as f:
    for line in f:
        kv = dict(t.split("=") for t in line.rstrip("\n").split("\t")[2].split() if "=" in t)
        rows.append((int(kv["mode"]), int(kv["room"]), int(kv["x"]), int(kv["y"])))
# events: (frame, kind, room, prev)  kind = enter (walked in) | jump (bookmark load: non-adjacent room change)
events = []
prev = None
for k, (mode, room, x, y) in enumerate(rows):
    if mode != 5:
        continue
    if prev is None:
        events.append((k, "start", room, None))
    elif room != prev:
        adjacent = abs((room & 0xF) - (prev & 0xF)) + abs((room >> 4) - (prev >> 4)) == 1
        events.append((k, "enter" if adjacent else "jump", room, prev))
    prev = room
ROUTE = [0x77, 0x76, 0x66, 0x65, 0x64, 0x63, 0x73, 0x74]      # the route it found: W, N, W, W, W, S, E
CELL = 64
OX, OY = 96, 88
def pos(room):
    return OX + (room & 0xF) * CELL + CELL // 2, OY + (room >> 4) * CELL + CELL // 2

SPEED = 16                                   # trace frames per video frame
def frames():
    seen = {}
    edges = set()
    jumps = []
    ei = 0
    total = len(rows) // SPEED + int(4 * gfx.FPS)
    for v in range(total):
        t = min(len(rows) - 1, v * SPEED)
        while ei < len(events) and events[ei][0] <= t:
            k, kind, room, pv = events[ei]
            seen.setdefault(room, v)
            if kind == "enter":
                edges.add((min(pv, room), max(pv, room)))
            elif kind == "jump":
                jumps.append((v, pv, room))
            ei += 1
        im, d = gfx.canvas()
        d.text((32, 22), "DAY ONE - FINDING LEVEL 3 WITHOUT A MAP", font=gfx.FB[22], fill=gfx.GOLD)
        d.text((32, 52), "read the screen's tiles, save a bookmark, walk out one exit, note where you land, jump back, try the next",
               font=gfx.F[13], fill=gfx.DIM)
        # the 16 x 8 grid of the overworld, unknown screens dark
        for r in range(8):
            for c in range(16):
                x, y = OX + c * CELL, OY + r * CELL
                d.rectangle((x + 2, y + 2, x + CELL - 2, y + CELL - 2), outline=(24, 30, 40))
        for a, b in edges:
            d.line(pos(a) + pos(b), fill=gfx.BLUE, width=3)
        for (jv, a, b) in jumps[-6:]:
            age = v - jv
            if age < 40:
                col = gfx.blend(gfx.SAND, 1 - age / 40)
                ax, ay = pos(a); bx, by = pos(b)
                n = 12
                for i in range(n):
                    if i % 2 == 0:
                        d.line((ax + (bx - ax) * i / n, ay + (by - ay) * i / n, ax + (bx - ax) * (i + 1) / n, ay + (by - ay) * (i + 1) / n), fill=col, width=2)
        for room, sv in seen.items():
            x, y = pos(room)
            age = v - sv
            glow = max(0.0, 1 - age / 30)
            col = gfx.blend(gfx.GOLD, 0.35 + 0.65 * glow) if room not in ROUTE or t < len(rows) - 1 else gfx.GREEN
            d.rectangle((x - 24, y - 24, x + 24, y + 24), fill=(20 + int(60 * glow), 30 + int(60 * glow), 50), outline=col, width=2)
            d.text((x, y), f"{room:02X}", font=gfx.F[16], fill=col, anchor="mm")
        cur = rows[t][1]
        if rows[t][0] == 5:
            x, y = pos(cur)
            d.rectangle((x - 28, y - 28, x + 28, y + 28), outline=gfx.GREEN, width=3)
        d.text((32, gfx.H - 60), f"screens seen: {len(seen):2d}   bookmark jumps: {len(jumps):2d}   trace frame {t:5d}", font=gfx.F[16], fill=gfx.TEXT)
        if t >= len(rows) - 1:
            d.text((32, gfx.H - 34), "route found: 77 > 76 > 66 > 65 > 64 > 63 > 73 > 74   (west, north, west x3, south, east: around the river)",
                   font=gfx.FB[16], fill=gfx.GREEN)
            for a, b in zip(ROUTE, ROUTE[1:]):
                d.line(pos(a) + pos(b), fill=gfx.GREEN, width=5)
        yield im

render_frames(frames(), out)
print("wrote", out)
