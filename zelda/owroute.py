"""Walking distances over the WHOLE overworld, from the cartridge's own map (zelda/owmap.py).

Nodes are Link positions on the navigator's 8 px lattice (the same `box_cells` hitbox and the same tile knowledge
the navigator steers by), edges are 8 px steps and screen changes. Water is a wall without the stepladder and a
one-square bridge with it. The two maze screens are modelled as the game plays them: the Lost Woods (0x61) lets
Link out to the EAST freely and to the west only by the north-west-south-west sequence; the Lost Hills (0x1B)
let him out to the WEST freely and north only by going up four times. The raft docks are fixed-cost edges.

Costs are frames. They are calibrated against the third run's own overworld crossings (calibrate())."""
from __future__ import annotations

import heapq
import json
from functools import lru_cache
from pathlib import Path

from . import owmap
from .overworld import box_cells, water_bridges, OW_WATER_IDS

HARNESS = Path(__file__).resolve().parent.parent
STEP = 8 / 1.5                 # frames per 8 px at Link's walking speed
SCROLL_H = 135                 # a horizontal screen change incl. settle: median over 64 crossings of the third run
SCROLL_V = 106                 # vertical: median over 46
WOODS_WEST = 1013              # 0x61 entered from the east, out to 0x60: measured (woods_0..3 of the third run)
HILLS_NORTH = 967              # 0x1B up four times into 0x0B: measured (hills_1..4)
RAFT = 420                     # a raft ride, dock to landing

XS = range(0, 241, 8)
YS = range(61, 222, 8)


@lru_cache(maxsize=1)
def _kb():
    tk = json.loads((HARNESS / "knowledge" / "tiles.json").read_text(encoding="utf-8"))
    return set(tk["ow"]["walkable"]), set(tk["ow"]["solid"])


def walkable_tile(t: int) -> bool:
    walk, solid = _kb()
    if t in OW_WATER_IDS:
        return False
    if t in walk:
        return True
    if t in solid:
        return False
    return t < 0x89                 # the cartridge's own rule for tiles nobody has stood on yet


@lru_cache(maxsize=None)
def free(room: int, ladder: bool) -> frozenset:
    cells = owmap.cells(room)
    bridge = set()
    if ladder:
        v, h = water_bridges(cells, OW_WATER_IDS)
        bridge = v | h
    out = set()
    for x in XS:
        for y in YS:
            if y + 19 > 64 + 176:
                continue
            ok = True
            for cy, cx in box_cells(x, y):
                if cy > 21 or cx > 31:
                    ok = False
                    break
                if (cy, cx) in bridge:
                    continue
                if not walkable_tile(cells[cy][cx]):
                    ok = False
                    break
            if ok:
                out.add((x, y))
    return frozenset(out)


def neighbors(node, ladder: bool):
    room, x, y = node
    f = free(room, ladder)
    for dx, dy in ((8, 0), (-8, 0), (0, 8), (0, -8)):
        if (x + dx, y + dy) in f:
            yield (room, x + dx, y + dy), STEP
    col, row = room & 15, room >> 4
    if x == 0 and col > 0 and room != 0x61:
        if (240, y) in free(room - 1, ladder):
            yield (room - 1, 240, y), SCROLL_H
    if x == 240 and col < 15 and room != 0x1B:
        if (0, y) in free(room + 1, ladder):
            yield (room + 1, 0, y), SCROLL_H
    if y == 61 and row > 0 and room not in (0x61, 0x1B):
        if (x, 221) in free(room - 16, ladder):
            yield (room - 16, x, 221), SCROLL_V
    if y == 221 and row < 7 and room not in (0x61, 0x1B):
        if (x, 61) in free(room + 16, ladder):
            yield (room + 16, x, 61), SCROLL_V
    # the mazes, as fixed-cost edges from wherever Link stands on the screen's relevant edge
    if room == 0x61 and x == 0 and (240, y) in free(0x60, ladder):
        yield (0x60, 240, y), WOODS_WEST
    if room == 0x1B and y == 61 and (x, 221) in free(0x0B, ladder):
        yield (0x0B, x, 221), HILLS_NORTH


def dijkstra(start, ladder: bool, goal=None, limit: float = 1e9):
    dist = {start: 0.0}
    prev = {}
    pq = [(0.0, start)]
    while pq:
        d, n = heapq.heappop(pq)
        if d > dist.get(n, 1e18):
            continue
        if goal is not None and goal(n):
            return d, n, prev
        if d > limit:
            break
        for m, c in neighbors(n, ladder):
            nd = d + c
            if nd < dist.get(m, 1e18):
                dist[m] = nd
                prev[m] = n
                heapq.heappush(pq, (nd, m))
    return (None, None, prev) if goal is not None else (dist, None, prev)


def nearest_free(room: int, x: int, y: int, ladder: bool = False, radius: int = 40):
    best = None
    for fx, fy in free(room, ladder):
        d = abs(fx - x) + abs(fy - y)
        if d <= radius and (best is None or d < best[0]):
            best = (d, (room, fx, fy))
    return best[1] if best else None


def rooms_on(prev, end) -> list:
    path = [end]
    while path[-1] in prev:
        path.append(prev[path[-1]])
    out = []
    for n in reversed(path):
        if not out or out[-1] != n[0]:
            out.append(n[0])
    return out


def leg(a, b_room: int, ladder: bool, b_xy=None):
    """Cheapest walk from node `a` to screen `b_room` (or to the lattice point nearest b_xy on it)."""
    if b_xy is None:
        goal = lambda n: n[0] == b_room
    else:
        t = nearest_free(b_room, b_xy[0], b_xy[1], ladder)
        if t is None:
            return None, None, []
        goal = lambda n: n == t
    d, end, prev = dijkstra(a, ladder, goal)
    if d is None:
        return None, None, []
    return d, end, rooms_on(prev, end)
