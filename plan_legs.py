"""Print the screen-by-screen walk for each leg of a planned errand order (router paths, with exit coordinates)."""
import sys
import route_planner as rp
from zelda import owroute

PLAN = ["L3", "h_2C", "r100_0F", "candle_0C", "WS", "L1", "h_47", "L4", "r100_6B", "L8", "L2", "L5", "arrows_44", "bait_34",
        "L7", "MS", "L6", "L9"]
WIND = {"arrows_44": 3, "L9": 5}           # legs that start with a whirlwind ride to this level's door


def path_nodes(a, b, raft, ladder):
    base = rp._install_special_edges(raft)
    try:
        d, end, prev = owroute.dijkstra(a, ladder, goal=lambda n: n == b)
    finally:
        owroute.neighbors = base
    if d is None:
        return None, []
    nodes = [end]
    while nodes[-1] in prev:
        nodes.append(prev[nodes[-1]])
    return d, nodes[::-1]


def describe(nodes):
    out = []
    for p, q in zip(nodes, nodes[1:]):
        if p[0] != q[0]:
            dr = q[0] - p[0]
            d = {1: "Right", -1: "Left", 16: "Down", -16: "Up"}.get(dr, f"jump{dr:+d}")
            at = p[1] if d in ("Up", "Down") else p[2]
            out.append((d, q[0], at))
    return out


if __name__ == "__main__":
    at = "start"
    raft = ladder = False
    for e in PLAN:
        owroute.free.cache_clear()
        src = rp.P[at] if e not in WIND else None
        if e in WIND:
            a = owroute.nearest_free(rp.DOOR_SCREEN[WIND[e]], 0, rp.WHIRL_Y, ladder, radius=120)
        else:
            a = owroute.nearest_free(*rp.P[at], ladder, radius=64)
        b = owroute.nearest_free(*rp.P[e], ladder, radius=64)
        d, nodes = path_nodes(a, b, raft, ladder)
        steps = describe(nodes)
        print(f"{at:10s} -> {e:10s} {'(wind to L%d first) ' % WIND[e] if e in WIND else ''}{d:7.0f} frames, {len(steps):2d} screens: "
              + " ".join(f"{dd[0]}{room:02X}@{c}" for dd, room, c in steps))
        at = e
        if e == "L3":
            raft = True
        if e == "L4":
            ladder = True
