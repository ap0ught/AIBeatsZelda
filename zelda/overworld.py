"""Navigation from the game's own tile map, for the overworld and dungeon rooms.

Model (measured, see journal/02-navigator.md):
  * The current screen's 8x8 pattern ids live at $6530, 32 columns x 22 rows, column-major.
  * Link's body box is 16x16 starting 3 px below his RAM y. A position is legal when every 8x8
    cell under the box is walkable. Collision is per 8x8 cell, not per 16x16 tile.
  * Link's y is always 5 mod 8; x is any value but we plan on multiples of 8.
  * The overworld and dungeons use different pattern tables, so tile knowledge is kept per context.

Walkability of pattern ids is a knowledge base that starts with a few seeds and is extended by
experiment: when a planned step fails, the cells that step would have entered are the suspects.
"""
from __future__ import annotations

import heapq
import json
from pathlib import Path

from .emulator import BizHawk, State, HARNESS_DIR
from . import ram

KB_PATH = HARNESS_DIR / "knowledge" / "tiles.json"

PLAY_TOP = 64
COLS, ROWS = 32, 22           # 8x8 cells
DIRS = {"Up": (0, -8), "Down": (0, 8), "Left": (-8, 0), "Right": (8, 0)}

ENEMY_NAMES = {
    0x01: "Blue Lynel", 0x02: "Red Lynel", 0x03: "Blue Moblin", 0x04: "Red Moblin", 0x05: "Blue Goriya",
    0x06: "Red Goriya", 0x07: "Red Octorok", 0x08: "Red Octorok (fast)", 0x09: "Blue Octorok",
    0x0A: "Blue Octorok (fast)", 0x0B: "Red Darknut", 0x0C: "Blue Darknut", 0x0D: "Blue Tektite",
    0x0E: "Red Tektite", 0x0F: "Blue Leever", 0x10: "Red Leever", 0x11: "Zora", 0x12: "Vire", 0x13: "Zol",
    0x14: "Gel", 0x15: "Gel", 0x16: "Pols Voice", 0x17: "Like Like", 0x18: "Little Digdogger", 0x1A: "Peahat",
    0x1B: "Blue Keese", 0x1C: "Red Keese", 0x1D: "Black Keese", 0x1E: "Armos", 0x1F: "Boulders", 0x20: "Boulder",
    0x21: "Ghini", 0x22: "Flying Ghini", 0x23: "Blue Wizzrobe", 0x24: "Red Wizzrobe", 0x27: "Wallmaster",
    0x28: "Rope", 0x2A: "Stalfos", 0x2B: "Bubble", 0x2C: "Blue Bubble", 0x2D: "Red Bubble",
    # Bosses and set pieces. Only the ones this run has actually met and measured are named;
    # anything else still prints as a hex id so a tour tells me honestly that it saw something new.
    0x32: "Dodongo", 0x33: "Gohma (red)", 0x34: "Gohma (blue)", 0x36: "Digdogger",
    0x37: "Digdogger (split)", 0x38: "Little Digdogger", 0x3C: "Manhandla",
    0x40: "old man's fire", 0x43: "Gleeok head", 0x44: "Gleeok neck",
    0x4B: "old man", 0x4C: "old man",
}


def enemy_name(t: int) -> str:
    return ENEMY_NAMES.get(t, f"enemy {t:02X}")


import threading as _threading
_KB_LOCK = _threading.RLock()


def _read_json(path, default=None):
    """Read a knowledge file under the lock, retrying briefly: on Windows a reader that has the file open makes
    another thread's os.replace fail with 'Access is denied', which killed a scout's thread mid-search."""
    import time as _t
    for _ in range(5):
        with _KB_LOCK:
            try:
                return json.loads(path.read_text())
            except (OSError, ValueError):
                pass
        _t.sleep(0.02)
    return {} if default is None else default


def _write_json(path, obj) -> None:
    import os
    import time as _t
    with _KB_LOCK:
        tmp = path.with_suffix(".tmp%d_%d" % (os.getpid(), _threading.get_ident()))
        try:
            tmp.write_text(json.dumps(obj, indent=1))
            for _ in range(5):
                try:
                    os.replace(tmp, path)
                    return
                except OSError:
                    _t.sleep(0.03)
        except OSError:
            pass
        finally:
            try:
                if tmp.exists():
                    tmp.unlink()
            except OSError:
                pass


class TileKB:
    """Which 8x8 pattern ids Link can stand on, per context. Persisted so learning carries over."""

    SEEDS = {
        "ow": ({0x26, 0xDC, 0xDD, 0xDE, 0xDF, 0xD5, 0xD7, 0xF3, 0x24, 0x76, 0x77},   # 76/77 = raft dock
               {0xD8, 0xD9, 0xDA, 0xDB, 0xD4, 0xD6, 0xCE, 0xCF, 0xD0, 0xD1, 0xD2, 0xD3}),
        "dg": ({0x74, 0x75, 0x76, 0x77, 0x24, 0x68, 0x70, 0x71, 0x72, 0x73}, {0xF5, 0xF6}),   # 70-73 = stairs
        "cl": ({0x24, 0x6F, 0xF3}, {0xFA}),   # cellars (mode 9): black floor, ladders, open dark; gray bricks solid
    }

    def __init__(self, path: Path = KB_PATH):
        self.path = path
        self.ctx = {c: {"walkable": set(w), "solid": set(s), "evidence": {}} for c, (w, s) in self.SEEDS.items()}
        if path.exists():
            d = _read_json(path)
            if "walkable" in d:                     # old single-context file: it was all overworld
                d = {"ow": d}
            for c, v in d.items():
                k = self.ctx.setdefault(c, {"walkable": set(), "solid": set(), "evidence": {}})
                k["walkable"] |= set(v.get("walkable", []))
                k["solid"] |= set(v.get("solid", []))
                k["evidence"].update(v.get("evidence", {}))
        self.current = "ow"

    def use(self, level: int, mode: int = 5) -> None:
        self.current = "cl" if mode == 9 else "dg" if level else "ow"

    def save(self) -> None:
        # Several scouts learn at once now: merge with what is on disk, write to a temp file, swap it in.
        import os
        with _KB_LOCK:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            disk = _read_json(self.path)
            for c, v in disk.items():
                if c in self.ctx and isinstance(v, dict):
                    mine = self.ctx[c]
                    mine["walkable"] |= {x for x in v.get("walkable", []) if x not in mine["solid"]}
                    mine["solid"] |= {x for x in v.get("solid", []) if x not in mine["walkable"]}
            _write_json(self.path, {c: {"walkable": sorted(v["walkable"]), "solid": sorted(v["solid"]),
                                        "evidence": v["evidence"]} for c, v in self.ctx.items()})

    @property
    def walkable(self) -> set:
        return self.ctx[self.current]["walkable"]

    @property
    def solid(self) -> set:
        return self.ctx[self.current]["solid"]

    def is_water(self, tid: int) -> bool:
        return tid == 0xF4 if self.current == "dg" else (0x90 <= tid < 0xA0 if self.current == "ow" else False)

    def is_walkable(self, tid: int, optimistic: bool) -> bool:
        if self.is_water(tid):
            return False           # only ever crossed on the stepladder (legal()'s cells_ok)
        if tid in self.solid:
            return False
        if tid in self.walkable:
            return True
        return optimistic          # unknown ids: trust them only when asked to explore

    def learn(self, tid: int, walkable: bool, why: str) -> None:
        if self.is_water(tid):
            return                 # stepping on water means the ladder was under him; learn nothing
        (self.walkable if walkable else self.solid).add(tid)
        (self.solid if walkable else self.walkable).discard(tid)
        self.ctx[self.current]["evidence"][f"{tid:02x}"] = why
        self.save()


def read_cells(emu: BizHawk) -> list[list[int]]:
    """cells[row][col] of 8x8 pattern ids for the current screen."""
    b = emu.bus(0x6530, COLS * ROWS)
    return [[b[c * ROWS + r] for c in range(COLS)] for r in range(ROWS)]


def read_enemies(emu: BizHawk) -> list[tuple[int, int, int, int, int]]:
    """(slot, type, x, y, hp) for every live object slot 1..11.
    Per the disassembly: ObjType=$34F, ObjX=$70, ObjY=$84, ObjHP=$485, all indexed by slot (0 = Link)."""
    ts = emu.ram(0x34F, 12)
    xs = emu.ram(0x70, 12)
    ys = emu.ram(0x84, 12)
    hp = emu.ram(0x485, 12)
    # types >= 0x60 are effects and pickups (bomb smoke 0x60, cave items 0x6A...), not monsters
    return [(i, ts[i], xs[i], ys[i], hp[i]) for i in range(1, 12) if ts[i] and ts[i] < 0x60]


def read_room_item(emu: BizHawk) -> tuple[int, int, int] | None:
    """(type, x, y) of the item lying in the room, if any (object slot 0x13)."""
    if emu.byte(0xBF) == 0xFF:      # item slot status: FF = nothing lying here ($AB/$83/$97 are then stale)
        return None
    t = emu.byte(0xAB)              # item id; 0x00 is bombs, so 0 is a real item here
    return t, emu.byte(0x83), emu.byte(0x97)


def box_cells(x: int, y: int) -> list[tuple[int, int]]:
    """8x8 cells covered by Link's body box at RAM position (x, y)."""
    top = y + 3 - PLAY_TOP
    out = []
    for cy in range(top // 8, (top + 15) // 8 + 1):
        for cx in range(x // 8, (x + 15) // 8 + 1):
            out.append((cy, cx))
    return out


WATER_IDS = {0xF4}                       # dungeon water
OW_WATER_IDS = set(range(0x90, 0xA0))    # overworld water (rivers, ponds, the sea)
LADDER_FLAG = 0x663


def entrance_spots(cells) -> list:
    """(x, y) of cave/dungeon doorways on an overworld screen: the black tile 0x24 with the dark
    arch 0xF3 above it. Crossings must route around these or Link walks into a cave by accident."""
    out = []
    for r in range(2, 21):
        for c in range(1, 31):
            if cells[r][c] == 0x24 and cells[r - 1][c] == 0xF3:
                out.append(((c // 2) * 16, 64 + (r // 2) * 16 - 3))
    return out


def water_bridges(cells, ids=None) -> tuple:
    """Water the stepladder can span, split by direction of travel. The ladder bridges a gap
    exactly one 16px tile wide with land on both sides, and only in that direction: a vertical gap
    can be crossed going up or down, never walked along sideways. Returns (vertical, horizontal).

    `ids` selects which tiles count as water - dungeon water and overworld water are drawn with
    completely different tiles, and for a long time this only knew about the dungeon ones, which
    is why Link could never cross the river on the way to Death Mountain."""
    ids = WATER_IDS if ids is None else ids
    WATER_IDS_LOCAL = ids
    vert, horz = set(), set()
    for tr in range(11):
        for tc in range(16):
            r, c = tr * 2, tc * 2
            if cells[r][c] not in WATER_IDS_LOCAL:
                continue
            quad = {(r, c), (r, c + 1), (r + 1, c), (r + 1, c + 1)}
            if (tr > 0 and tr < 10 and cells[r - 2][c] not in WATER_IDS_LOCAL
                    and cells[r + 2][c] not in WATER_IDS_LOCAL):
                vert |= quad
            if (tc > 0 and tc < 15 and cells[r][c - 2] not in WATER_IDS_LOCAL
                    and cells[r][c + 2] not in WATER_IDS_LOCAL):
                horz |= quad
    return vert, horz


# Dungeon locked-door graphics (both orientations). Walking into one with a key opens it.
LOCKED_DOOR_IDS = {0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0xA6, 0xA7,   # east/west locked doors
                   0x98, 0x99, 0x9A, 0x9B, 0x9C, 0x9D, 0x9E, 0x9F}   # north/south locked doors


def legal(cells, kb: TileKB, x: int, y: int, optimistic: bool = False, extra: set | None = None,
          cells_ok: set | None = None) -> bool:
    if x < 0 or x > 240 or y + 3 < PLAY_TOP or y + 19 > PLAY_TOP + 176:
        return False
    for cy, cx in box_cells(x, y):
        t = cells[cy][cx]
        if cells_ok and (cy, cx) in cells_ok:
            continue
        if extra and t in extra:
            continue
        if not kb.is_walkable(t, optimistic):
            return False
    return True


Y_PHASE = [5]     # Link's y is 5 mod 8 in rooms; cellars use a different phase, measured on entry


def set_phase(y: int) -> None:
    Y_PHASE[0] = y % 8


def snap(x: int, y: int) -> tuple[int, int]:
    ph = Y_PHASE[0]
    return (x // 8) * 8, ((y - ph) // 8) * 8 + ph


TRAP = 0x49      # blade trap: sits in a corner, slides at Link when he enters its row or column


_HARM: list | None = None


def harm_halfhearts(t: int) -> int:
    """Contact damage of an object type in half hearts, straight from the cartridge
    (ObjTypeToDamagePoints, Rev 1 file offset 0x72CA: low nibble whole hearts, bit 7 a half).
    0 means touching it costs nothing: old men, Bubbles, items. The navigator used to wait ten
    seconds for an old man's flame to "move out of the way" and route half a screen around a
    burrowed Leever; what matters is only what can actually hurt, and how much."""
    global _HARM
    if _HARM is None:
        from .romdata import rom
        tab = rom()[0x72CA:0x72CA + 0x60]
        assert tab[:8] == bytes([0x60, 0x02, 0x01, 0x80, 0x80, 0x01, 0x80, 0x80]), "damage table moved"
        _HARM = [((v & 0x0F) * 2 + (1 if v & 0x80 else 0)) for v in tab]
    return _HARM[t] if 0 <= t < len(_HARM) else 1


# How hard the path planner leans away from enemies. 1.0 is the go-through-them default the owner
# asked for; Navigator.go raises it when Link is nearly dead.
AVOID = [1.0]
_NO_CUT = {0x49, 0x2B, 0x2C, 0x2D, 0x40, 0x11, 0x1A, 0x01, 0x02, 0x0B, 0x0C}   # traps, Bubbles, Zora, Peahat, Lynel, Darknut
OLD_AVOIDANCE = [False]      # True restores the pre-2026-09-18 wide berth and waiting (A/B probes)


def enemy_penalty(enemies, x: int, y: int, scale: float = 1.0) -> int:
    """Extra path cost for standing at (x, y) near enemies. Contact range is ~16 px.
    Blade traps can't be killed; their whole row and column are a danger band instead."""
    if not OLD_AVOIDANCE[0]:
        pen = 0.0
        for _, t, ex, ey, _ in enemies:
            if t == TRAP:
                if abs(ey - y) < 18 or abs(ex - x) < 18:
                    pen += 30
                if (ex in (32, 208)) and (ey in (93, 189)):
                    continue
            hh = harm_halfhearts(t)
            d = max(abs(ex - x), abs(ey - y))
            # a step is 8 px (about five frames); half a heart is worth roughly 60-150 frames while
            # Link is healthy, and only a fraction of near passes actually connect
            if hh >= 3:
                # one or two HEARTS a touch (Lynels, Blue Darknuts, Wizzrobes, Gibdos): these are not
                # the "basic mobs" worth walking through - keep a real distance
                if d < 24:
                    pen += 25 * hh
                elif d < 40:
                    pen += 5 * hh
                elif d < 56:
                    pen += 1.5 * hh
            elif t < 0x40 and t not in _NO_CUT:
                # weak and killable: walking through its patch should cost about what cutting it down does
                # (two swings, ~5 steps in all), not a detour round the room
                if d < 16:
                    pen += 2.5
                elif d < 28:
                    pen += 0.8
            elif d < 16:
                pen += 5 * hh
            elif d < 28:
                pen += 1.5 * hh
        return int(pen * scale)
    pen = 0
    for _, t, ex, ey, _ in enemies:
        if t == TRAP:
            # a trap parked in a corner owns its row and column; a trap that has left its corner is
            # a fast projectile and gets the full enemy treatment below as well
            if abs(ey - y) < 18 or abs(ex - x) < 18:
                pen += 30          # crossing is fine; lingering is not (the executor never stops in a line)
            parked = (ex in (32, 208)) and (ey in (93, 189))
            if parked:
                continue
        d = max(abs(ex - x), abs(ey - y))
        if d < 24:
            pen += 120
        elif d < 40:
            pen += 25
        elif d < 56:
            pen += 6
    return pen


def plan(cells, kb: TileKB, start: tuple[int, int], goal, optimistic: bool = False,
         blocked: set | None = None, enemies=(), extra: set | None = None, forbid=None,
         cells_ok: set | None = None, pen_scale: float = 1.0, reluctant: str | None = None) -> list[str] | None:
    """Dijkstra over 8 px steps, penalising cells near enemies. goal(x, y) -> bool.
    `extra` are tile ids to treat as walkable for this plan (e.g. locked doors when holding a key).
    `forbid(x, y)` -> True marks positions that must not be entered (used to route around a threat)."""
    blocked = blocked or set()
    start = snap(*start)

    def ok(x, y, d):
        return legal(cells, kb, x, y, optimistic, extra,
                     (cells_ok[0] if d in ("Up", "Down") else cells_ok[1]) if cells_ok else None)

    # Link can legitimately be standing somewhere this checker calls illegal: the collision box
    # here is his whole 16x16 sprite, while the game lets him overlap scenery, and a screen
    # transition drops him half inside the edge. When that happens every neighbour looks blocked
    # and the planner reports "no path" - which on screen is Link standing still doing nothing.
    # So while he is in a square that fails the check, let him move at all costs: he is escaping.
    stuck = {}

    def escaping(pos):
        if pos not in stuck:
            # Standing on the stepladder is NOT being stuck. This only checked the vertical bridge
            # set, so a position on a HORIZONTAL ladder crossing counted as "stuck in scenery" and
            # was allowed to move anywhere at all - straight up a river, for instance.
            stuck[pos] = not any(ok(pos[0], pos[1], d) for d in ("Up", "Down", "Left", "Right"))                 and not legal(cells, kb, pos[0], pos[1], optimistic, extra)
        return stuck[pos]

    dist = {start: 0}
    prev = {start: None}
    pq = [(0, 0, start)]
    n = 0
    while pq:
        cost, _, cur = heapq.heappop(pq)
        if cost > dist.get(cur, 1 << 30):
            continue
        if goal(*cur):
            path = []
            while prev[cur] is not None:
                p, d = prev[cur]
                path.append(d)
                cur = p
            return path[::-1]
        # Standing on the stepladder (his box overlaps bridged water), Link can only carry on along
        # the axis he stepped onto it by - the game will not let him turn off its side.
        on_ladder_axis = None
        if cells_ok and prev[cur] is not None:
            if any(c in cells_ok[0] or c in cells_ok[1] for c in box_cells(*cur)):
                on_ladder_axis = prev[cur][1] in ("Up", "Down")
        for d, (dx, dy) in DIRS.items():
            nxt = (cur[0] + dx, cur[1] + dy)
            ok_cells = None
            if cells_ok:
                ok_cells = cells_ok[0] if d in ("Up", "Down") else cells_ok[1]
            if (cur, d) in blocked:
                continue
            if on_ladder_axis is not None and (d in ("Up", "Down")) != on_ladder_axis:
                continue
            if not legal(cells, kb, nxt[0], nxt[1], optimistic, extra, ok_cells):
                # escaping only ever excuses a solid tile, never a step off the screen: that
                # would scroll into the next room instead of getting unstuck
                on_screen = 0 <= nxt[0] <= 240 and nxt[1] + 3 >= PLAY_TOP and nxt[1] + 19 <= PLAY_TOP + 176
                if not (escaping(cur) and on_screen):
                    continue
            if forbid is not None and forbid(*nxt) and not goal(*nxt):
                continue
            nc = cost + 1 + (enemy_penalty(enemies, nxt[0], nxt[1], pen_scale) if enemies else 0)
            if reluctant is not None and cur == start and d == reluctant:
                nc += 12                     # turning straight back is only right when it clearly pays
            if nc < dist.get(nxt, 1 << 30):
                dist[nxt] = nc
                prev[nxt] = (cur, d)
                n += 1
                heapq.heappush(pq, (nc, n, nxt))
    return None


EDGE_GOALS = {
    "Left":  lambda x, y: x == 0,
    "Right": lambda x, y: x == 240,
    "Up":    lambda x, y: y == 61,
    "Down":  lambda x, y: y == 205,
}

# Dungeon rooms exit through doors in the middle of each wall; the passage is two cells wide.
DOOR_GOALS = {
    "Left":  lambda x, y: x <= 32 and y == 141,
    "Right": lambda x, y: x >= 208 and y == 141,
    "Up":    lambda x, y: y <= 85 and x == 120,
    "Down":  lambda x, y: y >= 189 and x == 120,
}


_OPP = {"Up": "Down", "Down": "Up", "Left": "Right", "Right": "Left"}
import os as _os
_NAV_DEBUG = bool(_os.environ.get("ZELDA_NAV_DEBUG"))


class NavError(RuntimeError):
    pass


SHUTTER_CLOSED_IDS = {0xA8, 0xA9, 0xAA, 0xAB, 0xAC, 0xAD, 0xAE, 0xAF}
BLOCK_IDS = {0xB0, 0xB1, 0xB2, 0xB3}


class LinkDied(NavError):
    pass


class Navigator:
    def __init__(self, emu: BizHawk, kb: TileKB | None = None, log=print):
        self.emu, self.kb, self.log = emu, kb or TileKB(), log
        self.blocked: dict[tuple, set] = {}      # (level, room) -> {(pos, dir)} moves proven impossible
        self.jitter = None                       # (rng, probability): random pauses, used by search
        self.allow_entrances = False             # walking into a cave mid-crossing is never wanted

    # -- execution ------------------------------------------------------
    def _check_alive(self, s: State) -> None:
        if s.hearts <= 0 or s.mode == 0x08:
            self.emu.note("LINK DIED. Game over screen; this attempt is void")
            raise LinkDied(f"Link died at {s}")
        if s.mode in (0x04, 0x0A, 0x0B, 0x10) and not s.level and not self.allow_entrances:
            # a cave mouth is walkable ground to a path planner; treat stumbling in as a failed
            # attempt so the search simply keeps a crossing that stayed outside
            self.emu.note("Walked into a cave by accident; abandoning this attempt")
            raise NavError("walked into a cave")

    def _step_to(self, d: str, target: tuple[int, int], max_frames: int = 40, stall_ok: int = 6) -> State | None:
        """Hold d until Link reaches target (8 px away). None if he stalls."""
        emu = self.emu
        last, stall = None, 0
        for _ in range(max_frames):
            s = emu.step(d, 1)
            self._check_alive(s)
            if s.mode not in (5, 9):
                return s
            if (s.x, s.y) == target:
                return s
            if (s.x, s.y) == last:
                stall += 1
                if stall >= stall_ok:
                    return None
            else:
                stall = 0
            last = (s.x, s.y)
        return None

    def _unlock(self, d: str, pos, target, cells) -> State | None:
        """Lean on a locked door with a key until it opens (the map changes), then step through."""
        emu = self.emu
        keys0 = emu.state().keys
        emu.note(f"Locked door ahead and we have {keys0} key(s): pushing {d} until it opens")
        for _ in range(90):
            s = emu.step(d, 1)
            self._check_alive(s)
            if s.keys < keys0:
                break
        else:
            emu.note("The door didn't open")
            return None
        emu.note(f"Door unlocked ({s.keys} keys left)")
        s = emu.step((), 10)            # the door graphic changes a few frames after the key is used
        new = read_cells(emu)
        for r in range(ROWS):
            cells[r][:] = new[r]
        return self._step_to(d, target, 60, stall_ok=20)

    def static_items(self) -> set:
        """Slots holding things that never move and cannot hurt Link (rupee caches and the like).
        Detected by branching on an in-memory savestate, so the run itself loses no frames."""
        emu = self.emu
        s = emu.state()
        key = (s.level, s.room, s.frame // 4096)
        if key in getattr(self, "_static_cache", {}):
            return self._static_cache[key]
        before = {e[0]: (e[2], e[3], e[4]) for e in read_enemies(emu)}
        root = emu.msave()
        emu.cmd("step 10 -")
        after = {e[0]: (e[2], e[3], e[4]) for e in read_enemies(emu)}
        emu.mload(root)
        emu.mfree(root)
        out = {slot for slot, v in before.items()
               if slot in after and after[slot] == v and v[2] == 0}
        if not hasattr(self, "_static_cache"):
            self._static_cache = {}
        self._static_cache[key] = out
        if out:
            emu.note(f"{len(out)} objects here never move and have no health: pickups, not enemies")
        return out

    def live_enemies(self):
        static = self.static_items()
        return [e for e in read_enemies(self.emu) if e[0] not in static]

    def threats(self):
        """Objects that can actually hurt Link on contact RIGHT NOW. Leaves out what the game itself
        skips in its collision code: harmless types (old men, Bubbles, pickups), burrowed Leevers
        (state != 3) and submerged Zoras (state outside 2-4) - neither is even drawn - and a Red
        Wizzrobe between teleports. A burrowed Leever is what Link spent 15 seconds attacking the
        air at on the way to Level 4."""
        emu = self.emu
        static = self.static_items()
        st = emu.ram(0xAC, 12)
        out = []
        for e in read_enemies(emu):
            slot, t = e[0], e[1]
            if slot in static or harm_halfhearts(t) == 0:
                continue
            if t in (0x5E, 0x5F):
                # 0x5F is Link's own STEPLADDER: the game spawns it as an object on the water tile in front
                # of him. Counted as a threat, it made every ladder crossing look dangerous exactly when
                # Link reached it - he paced up to the water and away again for sixty re-plans. (0x5E is
                # the recorder's secret.) Neither can hurt anything.
                continue
            if t in (0x0F, 0x10) and st[slot] != 3:
                continue
            if t == 0x11 and st[slot] not in (2, 3, 4):
                continue
            if t == 0x24 and (st[slot] & 0xC0) == 0:
                continue
            out.append(e)
        return out

    def _in_the_way(self, s, d: str, enemies):
        """A killable enemy directly ahead within sword reach, or None."""
        from .lookahead import NEVER_CHASE
        best = None
        for e in enemies:
            t = e[1]
            if t >= 0x40 or (t in NEVER_CHASE and t not in (0x01, 0x02)) or t in (0x0B, 0x0C):
                continue                      # bosses/flames, the unkillable, and Darknuts' shields
                # (Lynels are never CHASED, but one standing in the lane is cut down like anything else)
            ex, ey = e[2] - s.x, e[3] - s.y
            if d == "Right":
                ahead, off = ex, ey
            elif d == "Left":
                ahead, off = -ex, ey
            elif d == "Down":
                ahead, off = ey, ex
            else:
                ahead, off = -ey, ex
            if 0 < ahead <= 30 and abs(off) <= 10:
                if best is None or ahead < best[0]:
                    best = (ahead, e)
        return best[1] if best else None

    def _danger(self, enemies, x: int, y: int, radius: int = 22) -> tuple | None:
        from .lookahead import NEVER_CHASE
        for e in enemies:
            if e[1] in (0x11, 0x1A) and max(abs(e[2] - x), abs(e[3] - y)) >= 18:
                continue          # a Zora in the water is a hazard to route around, not to wait on
            if e[1] == TRAP and (e[2] in (32, 208)) and (e[3] in (93, 189)):
                continue          # parked traps are handled by the path penalty; never "wait" for one
            if 0x50 <= e[1] < 0x60:
                continue          # projectiles (rocks 0x53, fireballs 0x56...): waiting never helps
            if max(abs(e[2] - x), abs(e[3] - y)) < (radius + 10 if e[1] == TRAP else radius):
                return e
        return None

    def go(self, goal, describe: str, optimistic: bool = True, max_replans: int = 60) -> State:
        """Plan-execute-learn until goal(x, y) holds or the screen changes."""
        emu = self.emu
        s = emu.state()
        self.kb.use(s.level, s.mode)
        set_phase(s.y if s.mode == 9 else 5)     # rooms/overworld: fixed grid; cellars: measured
        if any(t == 0x4B for t in emu.ram(0x34F, 12)):
            # an old man is talking: Link is frozen until the text finishes. Hold a direction until he moves.
            s0 = s
            moving = 0
            last = (s.x, s.y)
            for _ in range(400):
                s = emu.step("Up" if s.y > 141 else "Down", 1)
                moving = moving + 1 if (s.x, s.y) != last else 0
                last = (s.x, s.y)
                if moving >= 3:
                    break
            if s.frame - s0.frame > 30:
                emu.note(f"Old man's text held Link for {s.frame - s0.frame} frames")
        cells = read_cells(emu)
        key = (s.level, s.room)
        hearts0 = s.hearts
        announced = False
        waits = 0
        attempt = 0
        frames_budget = 4000
        f_start = s.frame
        swung: dict = {}
        last_dir = None
        while attempt < max_replans and s.frame - f_start < frames_budget:
            enemies = self.live_enemies() if OLD_AVOIDANCE[0] else self.threats()
            pen_scale = 1.0 if OLD_AVOIDANCE[0] else (
                (5.0 if s.hearts <= 2.0 else 2.5 if s.hearts <= 3.0 else 1.5 if s.hearts < 6.0 else 1.0)
                * getattr(self, "avoid_bias", 1.0))
            extra = set(LOCKED_DOOR_IDS) if (s.level and s.keys > 0) else None
            cells_ok = (water_bridges(cells, WATER_IDS if s.level else OW_WATER_IDS)
                        if emu.byte(LADDER_FLAG) else None)
            ents = [] if (s.level or self.allow_entrances) else entrance_spots(cells)
            # Link often stands on a doorway (he just walked out of one), so never forbid the
            # square he is already on, or he would have nowhere legal to step.
            here = (s.x, s.y)
            ent_forbid = (lambda x, y: (any(abs(x - ex) < 14 and abs(y - ey) < 14 for ex, ey in ents)
                                        and max(abs(x - here[0]), abs(y - here[1])) > 12)) if ents else None
            path = plan(cells, self.kb, (s.x, s.y), goal, optimistic, self.blocked.get(key), enemies, extra,
                        cells_ok=cells_ok, forbid=ent_forbid, pen_scale=pen_scale,
                        reluctant=None if OLD_AVOIDANCE[0] else _OPP.get(last_dir))
            if _NAV_DEBUG:
                print(f"    nav@({s.x},{s.y}) last={last_dir} enemies={[(e[1], e[2], e[3]) for e in enemies]} path={(path or [])[:8]}", flush=True)
            if path is None:
                if optimistic:
                    raise NavError(f"no path to {describe} from ({s.x},{s.y}) even through unknown tiles")
                return self.go(goal, describe, optimistic=True, max_replans=max_replans - attempt)
            if not announced or attempt % 10 == 0:
                emu.note(f"Planned {len(path)} steps to {describe}"
                         + (f", steering around {len(enemies)} enemies" if enemies else "")
                         + (" (re-plan)" if attempt else ""))
                announced = True
            pos = snap(s.x, s.y)
            if pos != (s.x, s.y):
                s = self._align(pos)
            if not path:
                return s
            # with enemies about, execute only a few steps before re-planning against their new positions
            horizon = 2 if enemies else len(path)
            for d in path[:horizon]:
                dx, dy = DIRS[d]
                target = (pos[0] + dx, pos[1] + dy)
                if enemies and not OLD_AVOIDANCE[0]:
                    # GO THROUGH THEM. Never stand and wait for something to move (the one exception
                    # is a blade trap already sliding at the next step), and if something killable is
                    # right in front, cut it down on the way - 12 frames - instead of walking round it.
                    trap = next((e for e in enemies if e[1] == TRAP
                                 and not ((e[2] in (32, 208)) and (e[3] in (93, 189)))
                                 and max(abs(e[2] - target[0]), abs(e[3] - target[1])) < 32), None)
                    if trap is not None and waits < 12:
                        waits += 1
                        s = emu.step((), 4)
                        self._check_alive(s)
                        attempt -= 1
                        break
                    foe = None if getattr(self, "no_kill", False) else self._in_the_way(s, d, enemies)
                    if foe is not None and swung.get(foe[0], 0) < 3:
                        if not swung:
                            emu.note(f"{enemy_name(foe[1])} in the way at ({foe[2]},{foe[3]}): cutting through it")
                        swung[foe[0]] = swung.get(foe[0], 0) + 1
                        emu.step(d, 1)
                        emu.step("A", 2)
                        s = emu.step((), 9)
                        self._check_alive(s)
                        attempt -= 1          # a swing is not a failed plan
                        break
                threat = self._danger(enemies, *target) if (enemies and OLD_AVOIDANCE[0]) else None
                if threat:
                    # progress beats patience: look for a path that keeps clear of everything nearby
                    near = [e for e in enemies if max(abs(e[2] - s.x), abs(e[3] - s.y)) < 64]
                    detour = plan(cells, self.kb, (s.x, s.y), goal, optimistic, self.blocked.get(key), enemies, extra,
                                  forbid=lambda x, y: (any(max(abs(e[2] - x), abs(e[3] - y)) < 24 for e in near)
                                                       or (ent_forbid(x, y) if ent_forbid else False)),
                                  cells_ok=cells_ok)
                    if detour and not self._danger(enemies, pos[0] + DIRS[detour[0]][0], pos[1] + DIRS[detour[0]][1]):
                        if waits == 0 or waits % 20 == 0:
                            emu.note(f"{enemy_name(threat[1])} in the way at ({threat[2]},{threat[3]}): detouring instead of waiting")
                        path = detour
                        d = path[0]
                        dx, dy = DIRS[d]
                        target = (pos[0] + dx, pos[1] + dy)
                        threat = None
                from .lookahead import NEVER_CHASE
                if (threat and waits >= 8 and threat[1] < 0x40 and threat[1] not in NEVER_CHASE
                        and not getattr(self, "no_kill", False)):
                    # it won't move and there's no way around: it's in the way, so kill it
                    from .combat import Fighter
                    emu.note(f"{enemy_name(threat[1])} is blocking the only lane at ({threat[2]},{threat[3]}): killing it (in the way)")
                    Fighter(self).attack_slot(threat[0])
                    waits = 0
                    s = emu.state()
                    self._check_alive(s)
                    break
                if threat and waits < 150:
                    # something is right where we want to step: hold still a moment rather than walk into it
                    waits += 1
                    s = emu.step((), 4)
                    self._check_alive(s)
                    if waits in (1, 40, 100):
                        emu.note(f"Waiting: {enemy_name(threat[1])} is at ({threat[2]},{threat[3]}), too close to the next step")
                    attempt -= 1          # waiting is not a failed plan
                    break
                if self.jitter and self.jitter[0].random() < self.jitter[1]:
                    s = emu.step((), self.jitter[0].choice([1, 2, 3, 5, 8] if OLD_AVOIDANCE[0] else [1, 1, 2, 3]))
                    self._check_alive(s)
                door = extra and any(cells[cy][cx] in LOCKED_DOOR_IDS for cy, cx in box_cells(*target))
                r = self._unlock(d, pos, target, cells) if door else self._step_to(d, target)
                if r is None:
                    s = emu.state()
                    # knocked back by a hit, or a monster standing where the step ends: that is not scenery
                    crowd = any(max(abs(e[2] - target[0]), abs(e[3] - target[1])) < 20 for e in self.threats())
                    if s.hearts < hearts0 or crowd:
                        if s.hearts < hearts0:
                            emu.note(f"Knocked back going {d} at {pos} ({s.hearts} hearts left): not a wall, carrying on")
                            hearts0 = s.hearts
                        break
                    self._learn_block(cells, pos, d, target, key)
                    break
                s = r
                last_dir = d
                if (s.x, s.y) == target:
                    for cy, cx in set(box_cells(*target)) - set(box_cells(*pos)):
                        t = cells[cy][cx]
                        if t not in self.kb.walkable and t not in self.kb.solid and t not in LOCKED_DOOR_IDS:
                            self.kb.learn(t, True, f"walked onto it at {target} in room {key[1]:02X}")
                            emu.note(f"Learned tile {t:02X} is walkable (stepped on it)")
                if s.hearts < hearts0:
                    near = min(read_enemies(emu), key=lambda e: abs(e[2] - s.x) + abs(e[3] - s.y), default=None)
                    emu.note(f"MISTAKE (unplanned hit): took damage at ({s.x},{s.y}), {s.hearts} hearts left"
                             + (f"; nearest is a {enemy_name(near[1])} at ({near[2]},{near[3]})" if near else ""))
                    hearts0 = s.hearts
                if s.mode not in (5, 9):
                    return s
                pos = target
            else:
                if horizon >= len(path):
                    return s
            attempt += 1
        raise NavError(f"gave up reaching {describe}")

    def _align(self, pos: tuple[int, int]) -> State:
        """Nudge Link onto the 8 px planning grid (x can be off-grid after horizontal walking)."""
        emu = self.emu
        s = emu.state()
        for _ in range(20):
            if s.x == pos[0]:
                break
            s = emu.step("Right" if s.x < pos[0] else "Left", 1)
            self._check_alive(s)
        return s

    def _learn_block(self, cells, pos, d, target, key) -> None:
        """A planned step failed: find which newly-entered cells are unknown and mark them solid."""
        entered = set(box_cells(*target)) - set(box_cells(*pos))
        ids = {cells[cy][cx] for cy, cx in entered}
        unknown = [t for t in ids if t not in self.kb.walkable and t not in self.kb.solid]
        assumed = [t for t in ids if t in self.kb.walkable]
        self.blocked.setdefault(key, set()).add((pos, d))
        where = f"room {key[1]:02X}" + (f" of level {key[0]}" if key[0] else "")
        if len(unknown) == 1:
            t = unknown[0]
            self.kb.learn(t, False, f"blocked moving {d} into it at {target} in {where}")
            self.emu.note(f"BLOCKED going {d} at {pos}. Only unknown tile there is {t:02X}: learning it's SOLID")
        elif unknown:
            self.emu.note(f"BLOCKED going {d} at {pos}. Suspects {', '.join(f'{t:02X}' for t in unknown)}; marking this move impossible")
        else:
            self.emu.note(f"BLOCKED going {d} at {pos} but every tile ({', '.join(f'{t:02X}' for t in assumed)}) was believed walkable. Model is wrong here (or something is in the way); marking the move impossible")

    # -- doors that need a block pushed -------------------------------------
    def _door_open(self, d: str) -> bool:
        cells = read_cells(self.emu)
        probe = {"Up": [(1, 15), (1, 16), (2, 15), (2, 16)], "Down": [(19, 15), (19, 16), (20, 15), (20, 16)],
                 "Left": [(10, 1), (10, 2), (11, 1), (11, 2)], "Right": [(10, 29), (10, 30), (11, 29), (11, 30)]}[d]
        return any(cells[r][c] == 0x24 for r, c in probe)

    BLOCKS_PATH = HARNESS_DIR / "knowledge" / "blocks.json"

    def known_block(self, level: int, room: int):
        return _read_json(self.BLOCKS_PATH).get(f"L{level}_{room:02x}")

    def remember_block(self, level: int, room: int, br: int, bc: int, push: str) -> None:
        with _KB_LOCK:
            d = _read_json(self.BLOCKS_PATH)
            if d.get(f"L{level}_{room:02x}") == [br, bc, push]:
                return                       # already known: do not rewrite the file for nothing
            d[f"L{level}_{room:02x}"] = [br, bc, push]
            _write_json(self.BLOCKS_PATH, d)

    def push_any_block(self, rng=None) -> bool:
        """Try to shift a block, from whichever side is reachable. Rooms hide staircases behind a
        ring of blocks, and only one of them moves, in one direction. Success is the tile map
        changing. Remembers what worked."""
        emu = self.emu
        s0 = emu.state()
        self.kb.use(s0.level, s0.mode)
        cells = read_cells(emu)
        before = [row[:] for row in cells]
        known = self.known_block(s0.level, s0.room)
        blocks = [(known[0], known[1])] if known else sorted(
            {(r // 2, c // 2) for r in range(2, 20) for c in range(2, 30) if cells[r][c] in BLOCK_IDS})
        emu.note(f"Looking for the block that moves: {len(blocks)} candidate(s)")
        sides = (("Up", 0, 21), ("Down", 0, -19), ("Right", -19, 3), ("Left", 21, 3))
        if known and len(known) >= 3:
            sides = tuple(sorted(sides, key=lambda sd: sd[0] != known[2]))      # the side that worked before first
        for br, bc in blocks:
            bx, by = bc * 16, 64 + br * 16
            for push, ox, oy in sides:
                sx, sy = snap(bx + ox, by + oy)
                if not (8 <= sx <= 232 and 69 <= sy <= 197):
                    continue
                try:
                    self.go(lambda x, y: x == sx and y == sy, f"beside the block at ({bx},{by})",
                            max_replans=40)
                except NavError:
                    continue
                for i in range(90):
                    emu.step(push, 1)
                    # stop the moment the tile map changes instead of leaning on it for 90 frames
                    if i >= 12 and i % 3 == 0:
                        now = read_cells(emu)
                        if any(now[r][c] != before[r][c] for r in range(22) for c in range(32)):
                            break
                now = read_cells(emu)
                if any(now[r][c] != before[r][c] for r in range(22) for c in range(32)):
                    # the map changed when the block LEFT its tile; what it uncovers (stairs, a door) only
                    # appears when it arrives. Wait for the map to change again, or for it to settle.
                    moving = [row[:] for row in now]
                    for _ in range(40):
                        emu.step((), 1)
                        now = read_cells(emu)
                        if any(now[r][c] != moving[r][c] for r in range(22) for c in range(32)):
                            emu.step((), 2)
                            break
                    emu.note(f"That block moved when pushed {push}")
                    self.remember_block(s0.level, s0.room, br, bc, push)
                    return True
        emu.note("No block would move")
        return False

    def push_blocks_for_door(self, d: str) -> bool:
        """Some shutters open only when a block is pushed. Pushable blocks look like fixed ones, so
        the first time we try each block; after that the room's block is remembered."""
        emu = self.emu
        s0 = emu.state()
        cells = read_cells(emu)
        known = self.known_block(s0.level, s0.room)
        if known:
            blocks = [(known[0], known[1])]
            emu.note(f"This room's pushable block is known from before: tile ({known[0]},{known[1]})")
        else:
            blocks = sorted({(r // 2, c // 2) for r in range(4, 18) for c in range(4, 28) if cells[r][c] in BLOCK_IDS})
            emu.note(f"The {d} shutter is still closed with the room clear: trying to push {len(blocks)} block(s) (first visit; the one that moves gets remembered)")
        for br, bc in blocks:
            bx, by = bc * 16, 64 + br * 16
            tx, ty = snap(bx, by + 16 - 3 + 8)
            try:
                self.go(lambda x, y: x == bx and y == ty, f"below the block at ({bx},{by})", max_replans=40)
            except NavError:
                continue
            ee0 = emu.byte(0xEE)
            before = read_cells(emu)
            moved = False
            for i in range(90):
                s = emu.step("Up", 1)
                if emu.byte(0xEE) != ee0:
                    break
                if i >= 12 and i % 3 == 0:
                    now = read_cells(emu)
                    if any(now[r][c] != before[r][c] for r in range(22) for c in range(32)):
                        moved = True
                        break
            if moved:
                # it slid off its tile; what it hides (stairs, a door) shows when it ARRIVES
                sliding = read_cells(emu)
                for _ in range(40):
                    emu.step((), 1)
                    now = read_cells(emu)
                    if emu.byte(0xEE) != ee0 or any(now[r][c] != sliding[r][c] for r in range(22) for c in range(32)):
                        emu.step((), 2)
                        break
            if emu.byte(0xEE) != ee0 or self._door_open(d):
                emu.note(f"That block did it: the {d} door is open")
                self.remember_block(s0.level, s0.room, br, bc, "Up")
                return True
            if moved:
                # a room has one block that moves, and this was it: nothing else is worth leaning on
                emu.note(f"The block at ({bx},{by}) moved (no door opened: it hides something else)")
                self.remember_block(s0.level, s0.room, br, bc, "Up")
                return False
        emu.note("No block opened the door")
        return False

    # -- items ------------------------------------------------------------
    def grab_room_item(self) -> State | None:
        """If an item lies in the room, walk onto it. Returns the state after pickup or None."""
        emu = self.emu
        item = read_room_item(emu)
        if item is None:
            return None
        t, ix, iy = item
        emu.note(f"There's an item on the floor (type {t:02X}) at ({ix},{iy}). Going to grab it")
        tx, ty = snap(ix, iy)
        try:
            s = self.go(lambda x, y: abs(x - tx) <= 8 and abs(y - ty) <= 8, "the item")
        except NavError as e:
            emu.note(f"Couldn't reach the item: {e}")
            return None
        for _ in range(3):
            if read_room_item(emu) is None:
                break
            s = self.go(lambda x, y: x == tx and y == ty, "the item exactly")
            s = emu.wait(4)
        if read_room_item(emu) is None:
            emu.note(f"Picked it up. Keys {s.keys}, bombs {s.bombs}, rupees {s.rupees}")
        return s

    # -- screen transitions --------------------------------------------
    def exit_screen(self, d: str, at: int | None = None) -> State:
        """Walk to the d edge (or door) of this screen and scroll into the next one.
        `at` pins the column (for Up/Down) or row (for Left/Right) to leave from, which matters
        when the next screen is split by water and only one side is any use."""
        emu = self.emu
        s0 = emu.state()
        if s0.mode == 0x0B and not s0.level:
            emu.note("Wandered into a cave; walking back out before crossing")
            for _ in range(400):
                s0 = emu.step("Down", 1)
                if s0.mode == ram.MODE_NORMAL and s0.y < 200:
                    break
            s0 = emu.wait_until(lambda s: s.mode == ram.MODE_NORMAL, 400)
            s0 = emu.wait(2)
        goals = DOOR_GOALS if s0.level else EDGE_GOALS
        what = f"the {d} door" if s0.level else f"the {d} edge"
        if at is not None:
            base = goals[d]
            goals = dict(goals)
            if d in ("Up", "Down"):
                goals[d] = (lambda b, a: (lambda x, y: b(x, y) and x == a))(base, at)
            else:
                goals[d] = (lambda b, a: (lambda x, y: b(x, y) and y == a))(base, at)
            what += f" at {'x' if d in ('Up', 'Down') else 'y'}={at}"
        if s0.level:
            # consult the cartridge's door table before walking up to a door that won't open
            from .romdata import doors
            kind = doors(s0.level, s0.room).get({"Left": "W", "Right": "E", "Up": "N", "Down": "S"}[d])
            self._exit_kind = kind
            from .lookahead import UNKILLABLE
            live = [e for e in read_enemies(emu) if e[1] not in UNKILLABLE and e[1] < 0x50]
            # An OPEN shutter needs nothing killed - and something may still be standing in the object
            # table that cannot be killed at all. Ganon's ash pile keeps his own type (0x3E) and a
            # health byte, so this check sent Link off to "clear" a heap of ashes and failed 12/12
            # attempts at the door out of his room, which had been open since he died.
            if kind == "shutter" and live and emu.byte(0x34D) == 0 and not self._door_open(d):
                from .combat import Fighter
                emu.note(f"The {d} door is a shutter (ROM) and {len(live)} enemies are alive: clearing the room first, staying out of trap lines")
                if not Fighter(self).clear_room():
                    raise NavError(f"couldn't clear the room for the {d} shutter")
            if kind == "shutter" and not self._door_open(d):
                self.push_blocks_for_door(d)
            elif kind == "locked" and s0.keys == 0:
                raise NavError(f"the {d} door is locked and we have no key")
            elif kind == "wall":
                raise NavError(f"the {d} side is a wall (ROM)")
        s = self.go(goals[d], what)
        locked = s0.level and kind == "locked" and s.keys > 0
        if s.mode in (5, 9):
            emu.note(f"At {what}, holding {d}" + (" to unlock it" if locked else " to scroll"))
            last = (s.x, s.y)
            stall = 0
            keys0 = s.keys
            was_locked = locked
            for _ in range(200 if locked else 60):
                s = emu.step(d, 1)
                if not s0.level and s.mode in (0x04, 0x0A, 0x0B, 0x10):
                    # stairs/cave transition modes: Link is going somewhere we did not ask for
                    raise NavError("walked into a cave while leaving the screen")
                self._check_alive(s)
                if s.mode not in (5, 9):
                    break
                if locked and s.keys < keys0:
                    emu.note(f"Door unlocked ({s.keys} keys left); waiting for it to swing open")
                    locked = False
                    stall = 0
                    continue
                stall = stall + 1 if (s.x, s.y) == last else 0
                last = (s.x, s.y)
                # a door that was locked holds Link still while it opens; that is not a stall
                if stall >= (100 if locked else 60 if was_locked else 8):
                    raise NavError(f"{what} did not open: Link is stuck at ({s.x},{s.y})")
        s = emu.wait_until(lambda s: s.mode in (5, 9), 400, buttons=(d,))
        s = emu.wait(2)
        self._check_alive(s)
        emu.note(f"Now in room {s.room:02X} at ({s.x},{s.y})")
        return s
