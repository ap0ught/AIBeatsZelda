"""Lookahead planner: real path distances, context-scaled caution, no air swings, arrows that land.

Owner's notes on the 58-minute run: Link "struggles navigating the walkway" (Level 4), "attacks nothing stuck
on a wall piece for way too long" (Level 9's Like Likes), the Pols Voice "get one shot by arrows" but he used the
sword, and bosses can be fought "more aggressive as you fill up on life once you beat the boss".

Causes, read off the code:
  * shaping used MANHATTAN distance, so a block or a strip of water between Link and the spot he wanted left
    every hold either blocked (-120) or "further away", and a swing (cost 5.6) became the best move: Link swung
    at the air against a wall piece. Now a BFS over the room's walkable lattice gives true walking distance.
  * plan_reach offered swings always; now only with something killable within reach.
  * a half heart cost 800-1600 points against 0.5 per frame, whatever Link's health. Now scaled by caution():
    full price when he is low, ~1/3 when healthy, ~1/8 when a Triforce refill is coming (bosses).
  * a "shoot" branch looked 26 frames ahead; an arrow needs longer to cross a room, so shots that would have
    killed scored as misses and the planner walked up and used the sword. Shots now roll out 44 frames.
"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import ast
import pathlib

p = pathlib.Path("zelda/lookahead.py")
raw = p.read_bytes()
crlf = b"\r\n" in raw
t = raw.decode("utf-8").replace("\r\n", "\n")


def sub(old, new, what):
    global t
    n = t.count(old)
    assert n == 1, f"{what}: {n} matches"
    t = t.replace(old, new)
    print("  applied:", what)


sub('''DIRS4 = ("Up", "Down", "Left", "Right")
OPPOSITE = {"Up": "Down", "Down": "Up", "Left": "Right", "Right": "Left"}
''', '''DIRS4 = ("Up", "Down", "Left", "Right")
OPPOSITE = {"Up": "Down", "Down": "Up", "Left": "Right", "Right": "Left"}

# Set by the runner for segments whose damage is about to be refilled (a boss: the Triforce piece
# behind it restores every heart), or None to price damage from Link's own health.
CAUTION_OVERRIDE = [None]
OLD_PLANNER = [False]          # True restores Manhattan shaping and flat damage prices (A/B probes)


def caution(s) -> float:
    """How much a lost half heart is worth right now, as a multiplier on the planners' damage prices."""
    if OLD_PLANNER[0]:
        return 1.0
    if CAUTION_OVERRIDE[0] is not None:
        return CAUTION_OVERRIDE[0]
    h, c = s.hearts, max(1, s.containers)
    if h <= 2.0:
        return 1.5
    if h <= 3.5:
        return 1.0
    if h >= 8 or (h >= 5 and h / c >= 0.75):
        return 0.3
    return 0.55


class Lattice:
    """Where Link can stand in this room on the 8 px grid, and walking distances over it.

    Built once per planning call from the tile map (walls, blocks, water the ladder cannot span), so
    "how far is that spot" means how far Link has to WALK, not how far it is through a wall."""

    def __init__(self, emu: BizHawk):
        from .overworld import (TileKB, read_cells, legal, water_bridges, WATER_IDS, OW_WATER_IDS,
                                LADDER_FLAG, BLOCK_IDS)
        s = emu.state()
        kb = TileKB()
        kb.use(s.level, s.mode)
        cells = read_cells(emu)
        ok = water_bridges(cells, WATER_IDS if s.level else OW_WATER_IDS) if emu.byte(LADDER_FLAG) else None
        both = (ok[0] | ok[1]) if ok else None
        self.free = set()
        for x in range(0, 241, 8):
            for y in range(61, 206, 8):
                if s.level:
                    inside = 32 <= x <= 208 and 93 <= y <= 189
                    lane = (x == 120 and (y < 93 or y > 189)) or (y == 141 and (x < 32 or x > 208))
                    if not (inside or lane):
                        continue
                from .overworld import box_cells
                if any(cells[cy][cx] in BLOCK_IDS for cy, cx in box_cells(x, y) if 0 <= cy < 22 and 0 <= cx < 32):
                    continue
                if legal(cells, kb, x, y, True, None, both):
                    self.free.add((x, y))

    @staticmethod
    def snap(x: int, y: int) -> tuple:
        return (x + 4) // 8 * 8, (y - 5 + 4) // 8 * 8 + 5

    def nearest_free(self, x: int, y: int, radius: int = 24):
        p = self.snap(x, y)
        if p in self.free:
            return p
        best = None
        for q in self.free:
            d = abs(q[0] - x) + abs(q[1] - y)
            if d <= radius and (best is None or d < best[0]):
                best = (d, q)
        return best[1] if best else None

    def field(self, sources) -> dict:
        """Steps (8 px each) from every reachable lattice point to the nearest source."""
        from collections import deque
        dist = {}
        dq = deque()
        for sx, sy in sources:
            q = self.nearest_free(sx, sy)
            if q is not None and q not in dist:
                dist[q] = 0
                dq.append(q)
        free = self.free
        while dq:
            cx, cy = dq.popleft()
            d = dist[(cx, cy)] + 1
            for n in ((cx + 8, cy), (cx - 8, cy), (cx, cy + 8), (cx, cy - 8)):
                if n in free and n not in dist:
                    dist[n] = d
                    dq.append(n)
        return dist

    def walk(self, field: dict, x: int, y: int, fallback: float) -> float:
        """Walking distance in pixels from (x, y) according to `field`, or `fallback` if off the lattice."""
        q = self.snap(x, y)
        if q in field:
            return 8.0 * field[q] + abs(q[0] - x) + abs(q[1] - y)
        q = self.nearest_free(x, y, 12)
        if q is not None and q in field:
            return 8.0 * field[q] + abs(q[0] - x) + abs(q[1] - y)
        return fallback
''', "caution(), Lattice")

# ---- plan_fight: lattice + caution + shoot rollout
sub('''    frames = 0
    ignore = static_slots(emu)
    FUSE = 86            # a bomb's blast lands well after a normal rollout, so give it its own
    last_dir = None      # for the anti-dithering penalty
''', '''    frames = 0
    ignore = static_slots(emu)
    FUSE = 86            # a bomb's blast lands well after a normal rollout, so give it its own
    ARROW = 44           # ...and so does an arrow: it needs this long to cross most of a room
    last_dir = None      # for the anti-dithering penalty
    lattice = None if OLD_PLANNER[0] else Lattice(emu)
''', "plan_fight: lattice")

sub('''        urgency = 1.0 + URGENCY * (frames / max_frames)
        root = emu.msave()
        results = []
        order = list(macros)
        if rng:
            rng.shuffle(order)
        for m in order:
            emu.mload(root)
            s1 = run_macro(emu, m)                       # branch: not recorded
            s2 = emu.step((), FUSE if m[0] == "bomb" else this_rollout)
            hp1, n1 = measure()
            used = {"hold": 8, "wait": 6, "bomb": FUSE, "shoot": 14}.get(m[0], 14)''', '''        urgency = 1.0 + URGENCY * (frames / max_frames)
        dmg_w = damage_weight * caution(s0)
        # true walking distance to the nearest strike spot, from where the enemies are NOW
        spot_field = None
        if lattice is not None and tlist:
            srcs = []
            for e in tlist:
                srcs += [(e[2] - 24, e[3]), (e[2] + 24, e[3]), (e[2], e[3] - 24), (e[2], e[3] + 24)]
            spot_field = lattice.field(srcs)
        root = emu.msave()
        results = []
        order = list(macros)
        if rng:
            rng.shuffle(order)
        for m in order:
            emu.mload(root)
            s1 = run_macro(emu, m)                       # branch: not recorded
            s2 = emu.step((), FUSE if m[0] == "bomb" else ARROW if (m[0] == "shoot" and lattice is not None)
                          else this_rollout)
            hp1, n1 = measure()
            used = {"hold": 8, "wait": 6, "bomb": FUSE, "shoot": 14}.get(m[0], 14)''', "plan_fight: caution + spot field + arrow rollout")

sub('''                dist = min(abs(s2.x - px) + abs(s2.y - py) for px, py in spots)
                shaping = -0.6 * dist - front_pen''', '''                dist = min(abs(s2.x - px) + abs(s2.y - py) for px, py in spots)
                if spot_field:
                    dist = lattice.walk(spot_field, s2.x, s2.y, dist)
                shaping = -0.6 * dist - front_pen''', "plan_fight: walking distance shaping")

sub('''            sc = fight_score(s0, s2, hp0, n0, hp1, n1, used,
                             damage_weight=damage_weight, hp_weight=hp_weight,''', '''            sc = fight_score(s0, s2, hp0, n0, hp1, n1, used,
                             damage_weight=dmg_w, hp_weight=hp_weight,''', "plan_fight: scaled damage weight")

# ---- plan_reach
sub('''    frames = 0
    macros = [("hold", d, 8) for d in DIRS4] + [("wait", None, 4)] + [("swing", d, 0) for d in DIRS4]
    s0 = emu.state()
    room0 = s0.room
    last_dir = None
    while frames < max_frames:
        s0 = emu.state()
        if s0.hearts <= 0:
            return "died"
        if s0.mode not in (5, 9) or s0.room != room0:
            return "arrived" if exit_ok else "left the room"
        if goal(s0.x, s0.y):
            return "arrived"
        root = emu.msave()''', '''    frames = 0
    walk_macros = [("hold", d, 8) for d in DIRS4] + [("wait", None, 4)]
    all_macros = walk_macros + [("swing", d, 0) for d in DIRS4]
    s0 = emu.state()
    room0 = s0.room
    last_dir = None
    lattice = goal_field = None
    if not OLD_PLANNER[0] and getattr(goal, "target", None) is not None:
        lattice = Lattice(emu)
        goal_field = lattice.field([goal.target])
    while frames < max_frames:
        s0 = emu.state()
        if s0.hearts <= 0:
            return "died"
        if s0.mode not in (5, 9) or s0.room != room0:
            return "arrived" if exit_ok else "left the room"
        if goal(s0.x, s0.y):
            return "arrived"
        # a swing is only worth considering with something killable in reach; offered always, it is
        # what Link does when a wall piece blocks every hold - stand there and cut the air
        if OLD_PLANNER[0]:
            macros = all_macros
        else:
            close = any(killable(e) and max(abs(e[2] - s0.x), abs(e[3] - s0.y)) <= 36 for e in read_enemies(emu))
            macros = all_macros if close else walk_macros
        dmg_scale = caution(s0)
        root = emu.msave()''', "plan_reach: lattice, swing gating, caution")

sub('''                    sc = -800 * (s0.hearts - s2.hearts) * 2''', '''                    sc = -800 * dmg_scale * (s0.hearts - s2.hearts) * 2''', "plan_reach: scaled damage")

sub('''        for sc, m, s1 in results:
            d = goal_distance(goal, s1)''', '''        for sc, m, s1 in results:
            d = goal_distance(goal, s1)
            if goal_field:
                d = lattice.walk(goal_field, s1.x, s1.y, d)''', "plan_reach: walking distance to the goal")

ast.parse(t)
p.write_bytes((t.replace("\n", "\r\n") if crlf else t).encode("utf-8"))

# ---- probe_ab: let 'old' also mean the old planner
q = pathlib.Path("probe_ab.py")
s = q.read_text(encoding="utf-8")
if "OLD_PLANNER" not in s:
    s = s.replace("from zelda import overworld, runner", "from zelda import overworld, runner, lookahead")
    s = s.replace('        overworld.OLD_AVOIDANCE[0] = (mode == "old")',
                  '        overworld.OLD_AVOIDANCE[0] = (mode == "old")\n        lookahead.OLD_PLANNER[0] = (mode == "old")')
    q.write_text(s, encoding="utf-8")
print("lookahead patched")
