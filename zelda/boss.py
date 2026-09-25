"""Boss fights. Manhandla first.

Manhandla (Level 3): five objects of type 0x3C, four heads at +/-16 px around a core, 4 hp each.
Bomb power is 40 = 4 hp units, so any part inside a blast dies at once; a blast on the core
takes everything with it. Fireballs are objects of type 0x56 travelling in straight lines.
Measured: a bomb lands ~18 px in front of Link and its blast lands ~78 frames after pressing B.
"""
from __future__ import annotations

from .emulator import BizHawk, State
from .overworld import read_enemies, LinkDied, DIRS, snap, read_cells, legal
from . import ram

MANHANDLA = 0x3C
FIREBALL = 0x56
FUSE = 76
BOMB_LEAD = 18


def parts(emu: BizHawk):
    return [e for e in read_enemies(emu) if e[1] == MANHANDLA]


def fireballs(emu: BizHawk):
    ts = emu.ram(0x34F, 12); xs = emu.ram(0x70, 12); ys = emu.ram(0x84, 12)
    return [(i, xs[i], ys[i]) for i in range(1, 12) if ts[i] == FIREBALL]


def core_of(ps):
    """The part nearest the centroid is the core."""
    if not ps:
        return None
    cx = sum(p[2] for p in ps) / len(ps)
    cy = sum(p[3] for p in ps) / len(ps)
    return min(ps, key=lambda p: abs(p[2] - cx) + abs(p[3] - cy)), (cx, cy)


class Manhandla:
    def __init__(self, nav, rng=None):
        self.nav, self.emu, self.rng = nav, nav.emu, rng
        self.prev_fb = {}
        self.prev_core = None

    def _fb_threat(self, s) -> str | None:
        """If a fireball's line will pass through Link soon, return the direction to sidestep."""
        emu = self.emu
        cur = {i: (x, y) for i, x, y in fireballs(emu)}
        threat = None
        for i, (x, y) in cur.items():
            if i in self.prev_fb:
                px, py = self.prev_fb[i]
                vx, vy = x - px, y - py
                if vx == 0 and vy == 0:
                    continue
                for t in range(0, 40, 4):
                    fx, fy = x + vx * t, y + vy * t
                    if abs(fx - s.x) < 14 and abs(fy - s.y) < 14:
                        # sidestep perpendicular to the fireball's travel
                        if abs(vx) >= abs(vy):
                            threat = "Up" if s.y > 100 else "Down"
                        else:
                            threat = "Left" if s.x > 100 else "Right"
                        break
            if threat:
                break
        self.prev_fb = cur
        return threat

    def _part_threat(self, s, ps, margin: int = 22) -> str | None:
        """Too close to any part: direction away from the swarm."""
        for p in ps:
            if max(abs(p[2] - s.x), abs(p[3] - s.y)) < margin:
                core, (cx, cy) = core_of(ps)
                ax, ay = s.x - cx, s.y - cy
                return ("Right" if ax > 0 else "Left") if abs(ax) >= abs(ay) else ("Down" if ay > 0 else "Up")
        return None

    def _safe_step(self, d: str) -> State:
        emu = self.emu
        s = emu.state()
        cells = read_cells(emu)
        dx, dy = DIRS[d]
        if not legal(cells, self.nav.kb, s.x + dx, s.y + dy, optimistic=True):
            # try the perpendicular directions instead
            for alt in (("Up", "Down") if d in ("Left", "Right") else ("Left", "Right")):
                ax, ay = DIRS[alt]
                if legal(cells, self.nav.kb, s.x + ax, s.y + ay, optimistic=True):
                    return emu.step(alt, 1)
            return emu.step((), 1)
        return emu.step(d, 1)

    def fight(self, max_frames: int = 3000, lead_frames: int | None = None, log=None) -> bool:
        emu = self.emu
        rng = self.rng
        self.nav.kb.use(emu.state().level, emu.state().mode)
        lead_frames = lead_frames or (rng.choice([50, 60, 70, 80]) if rng else 70)
        approach_gap = rng.choice([26, 30, 34]) if rng else 30
        emu.note(f"MANHANDLA: bomb power 4 = one blast kills any part it covers. Leading its drift by {lead_frames} frames")
        hearts0 = emu.state().hearts
        frames = 0
        last_bomb = -999
        hist = []
        while frames < max_frames:
            s = emu.state()
            if s.hearts <= 0:
                raise LinkDied("died to Manhandla")
            if s.hearts < hearts0:
                emu.note(f"MISTAKE (unplanned hit): Manhandla got me, {s.hearts} hearts left")
                hearts0 = s.hearts
            ps = parts(emu)
            if not ps:
                emu.note("MANHANDLA IS DEAD")
                return True
            core, (cx, cy) = core_of(ps)
            hist.append((cx, cy))
            if len(hist) > 12:
                hist.pop(0)
            vx = (hist[-1][0] - hist[0][0]) / max(1, len(hist) - 1)
            vy = (hist[-1][1] - hist[0][1]) / max(1, len(hist) - 1)
            # 1. dodge fireballs and keep out of the swarm
            d = self._fb_threat(s) or self._part_threat(s, ps)
            if d:
                s = self._safe_step(d)
                frames += 1
                continue
            # 2. bomb when ready: stand so the bomb lands where the core will be in FUSE frames
            bomb_active = frames - last_bomb <= FUSE + 10      # our own fuse timer, not $BC (stale after wall bombs)
            if s.bombs > 0 and not bomb_active:
                tx = cx + vx * lead_frames
                ty = cy + vy * lead_frames
                # choose the side to approach from: the one Link is already on, along the row or column
                if abs(s.x - tx) >= abs(s.y - ty):
                    face = "Right" if tx > s.x else "Left"
                    stand = (tx - BOMB_LEAD if face == "Right" else tx + BOMB_LEAD, ty)
                else:
                    face = "Down" if ty > s.y else "Up"
                    stand = (tx, ty - BOMB_LEAD if face == "Down" else ty + BOMB_LEAD)
                sx, sy = snap(int(max(24, min(216, stand[0]))), int(max(77, min(197, stand[1]))))
                if abs(s.x - sx) <= 3 and abs(s.y - sy) <= 3:
                    emu.step(face, 1)
                    emu.step("B", 2)
                    last_bomb = frames
                    emu.note(f"Bomb placed for where the core should be in {lead_frames} frames (core now ({int(cx)},{int(cy)}), drift {vx:+.1f},{vy:+.1f})")
                    frames += 3
                    continue
                # move toward the stand spot, but never inside the swarm's margin
                ddx, ddy = sx - s.x, sy - s.y
                d = ("Right" if ddx > 0 else "Left") if abs(ddx) > abs(ddy) else ("Down" if ddy > 0 else "Up")
                nx, ny = s.x + DIRS[d][0], s.y + DIRS[d][1]
                if any(max(abs(p[2] - nx), abs(p[3] - ny)) < approach_gap - 8 for p in ps):
                    s = emu.step((), 1)
                else:
                    s = self._safe_step(d)
                frames += 1
                continue
            # 3. waiting for the fuse (or out of bombs): back away from the swarm, then hold
            ax, ay = s.x - cx, s.y - cy
            d = ("Right" if ax > 0 else "Left") if abs(ax) >= abs(ay) else ("Down" if ay > 0 else "Up")
            if max(abs(ax), abs(ay)) < 56:
                s = self._safe_step(d)
            else:
                s = emu.step((), 1)
            frames += 1
            if s.bombs == 0 and frames - last_bomb > FUSE + 30:
                emu.note("Out of bombs with parts still alive; giving up this attempt")
                return False
        emu.note("Manhandla fight timed out")
        return False


# ---------------------------------------------------------------- Gleeok
GLEEOK_BODY = 0x43
GLEEOK_SLOTS = range(1, 7)


def gleeok_parts(emu: BizHawk):
    """Gleeok's neck/head segments. Only the body is a typed object; the segments live purely in
    the position and health arrays, which is why a normal enemy scan misses them. Returns
    (slot, type, x, y, hp) like read_enemies, for the segments still alive."""
    xs = emu.ram(0x70, 8)
    ys = emu.ram(0x84, 8)
    hp = emu.ram(0x485, 8)
    return [(i, GLEEOK_BODY, xs[i], ys[i], hp[i]) for i in GLEEOK_SLOTS if hp[i] >> 4]


def gleeok_head_tracker(emu: BizHawk):
    """Aim at one head for the whole fight. The head is the neck's far end; picking it fresh every
    frame makes the target flicker between segments and the planner loses its sense of progress,
    so lock on and only re-pick when that head dies."""
    state = {"slot": None}

    def targets(emu):
        # Read each array ONCE. Every emu.ram() is a round trip over the Lua bridge and the planner
        # calls this on every rollout branch; a first draft of this function did a read per slot
        # inside a loop, fourteen round trips a call, which would have slowed every search after it.
        ts = emu.ram(0x34F, 12)
        xs = emu.ram(0x70, 12)
        ys = emu.ram(0x84, 12)
        hp = emu.ram(0x485, 12)
        alive = [i for i in GLEEOK_SLOTS if hp[i] >> 4]
        # A head cut loose from its neck becomes its own object (type 0x46, UpdateGleeokHead) and can
        # sit in a slot outside the body's, where this tracker could not see it. It still has to die:
        # the room-cleared flag never latches while one is alive, whatever the frame budget.
        loose = [i for i in range(1, 12) if ts[i] == GLEEOK_HEAD and hp[i] >> 4 and i not in alive]
        pool = alive + loose
        if not pool:
            return []
        slot = state["slot"]
        if slot is None or slot not in pool:
            if alive:
                bx, by = xs[1], ys[1]
                slot = max(alive, key=lambda i: abs(xs[i] - bx) + abs(ys[i] - by))
            else:
                s = emu.state()                      # only loose heads left: chase the nearest
                slot = min(pool, key=lambda i: abs(xs[i] - s.x) + abs(ys[i] - s.y))
            state["slot"] = slot
        return [(slot, GLEEOK_BODY, xs[slot], ys[slot], hp[slot])]

    return targets


# The disassembly's object jump table (Z_07) settles what these are: entries 42, 43, 44 and 45 are
# all UpdateGleeok - one per head count - and entry 46 is UpdateGleeokHead, the head that comes loose
# when its neck is cut and goes on flying and spitting. Knowing only (0x43, 0x44) meant a loose head
# was neither aimed at nor counted, and the room can never clear while one is alive: every timed-out
# attempt in the diagnostic ended with a 0x46 sitting at FULL health beside a half-dead body.
GLEEOK_HEAD = 0x46
GLEEOK_TYPES = (0x42, 0x43, 0x44, 0x45, GLEEOK_HEAD)


def gleeok_dead(emu: BizHawk) -> bool:
    """Beware the health slots: the game leaves stale values in them after the boss dies, so
    "all its hp is zero" is never true and the bot keeps swinging at an empty room. The game's
    own answer is $034D, the flag it sets when a room is finished and its shutters open."""
    if emu.byte(0x34D):
        return True
    hp = emu.ram(0x485, 8)
    if any(hp[i] >> 4 for i in range(1, 8)):
        return False
    return not [e for e in read_enemies(emu) if e[1] in GLEEOK_TYPES and e[0] < 8]


def fireball_threat(emu: BizHawk, s, prev: dict, horizon: int = 26):
    """Direction to sidestep if a fireball's straight line will cross Link soon, else None."""
    ts = emu.ram(0x34F, 20)
    xs = emu.ram(0x70, 20)
    ys = emu.ram(0x84, 20)
    cur = {i: (xs[i], ys[i]) for i in range(20) if 0x50 <= ts[i] < 0x60}
    out = None
    for i, (x, y) in cur.items():
        if i in prev:
            vx, vy = x - prev[i][0], y - prev[i][1]
            if vx or vy:
                for t in range(0, horizon, 3):
                    if abs(x + vx * t - s.x) < 13 and abs(y + vy * t - s.y) < 13:
                        out = ("Up" if s.y > 120 else "Down") if abs(vx) >= abs(vy) else                               ("Left" if s.x > 120 else "Right")
                        break
        if out:
            break
    prev.clear()
    prev.update(cur)
    return out


def try_moves(emu: BizHawk, rec, moves, rollout: int = 44):
    """Verify-then-act: branch on each candidate move, take the first that costs no health.
    Far cheaper than weighing every possible move, and it is the part that actually keeps Link
    alive. `moves` are (kind, dir) pairs; returns the one played."""
    s0 = emu.state()
    root = emu.msave()
    best, best_loss = None, None
    for m in moves:
        emu.mload(root)
        _play(emu, emu.step, m)
        s2 = emu.step((), rollout)
        loss = (s0.hearts - s2.hearts) + (100 if s2.hearts <= 0 else 0)
        if loss <= 0:
            best, best_loss = m, 0
            break
        if best_loss is None or loss < best_loss:
            best, best_loss = m, loss
    emu.mload(root)
    emu.mfree(root)
    _play(emu, rec.step, best)
    return best


def _play(emu, step, m):
    kind, d = m
    from .lookahead import face
    if kind == "swing":
        face(step, d); step("A", 2); step((), 11)
    elif kind == "bomb":
        face(step, d); step("B", 2); step((), 4)
    elif kind == "step":
        step(d, 4)
    elif kind == "wait":
        step((), 4)


def _cost(m):
    return {"swing": 14, "bomb": 6, "step": 4, "wait": 4}[m[0]]


def bomb_head(emu: BizHawk, rec, slot: int, face: str, rng=None) -> bool:
    """Drop a bomb beside the head and retreat out of the blast. Branch first: only commit if the
    bomb actually hurts the head and Link comes out of it alive."""
    away = {"Right": "Left", "Left": "Right", "Up": "Down", "Down": "Up"}[face]
    hp0 = emu.ram(0x485, 8)[slot] >> 4
    s0 = emu.state()
    root = emu.msave()

    def run(step):
        from .lookahead import face as _face_to
        _face_to(step, face)
        step("B", 2)
        step(away, 10)
        step((), 100)

    run(emu.step)
    hp1 = emu.ram(0x485, 8)[slot] >> 4
    s1 = emu.state()
    ok = s1.hearts > 0 and (hp1 < hp0 or hp1 > hp0)      # a kill swaps in a fresh head (hp goes up)
    emu.mload(root)
    emu.mfree(root)
    if not ok:
        return False
    emu.note(f"Bombing Gleeok's head (hp {hp0} -> {hp1})")
    run(rec.step)
    return True


def fight_gleeok(emu: BizHawk, rec, rng=None, max_frames: int = 20000, log=None) -> str:
    """Gleeok: stalk the one vulnerable head and strike when it is in reach, checking every move
    against a savestate first so Link does not walk into a fireball or the neck.

    The head is the far end of the neck; the body and inner segments cannot be hurt. Killing a head
    puts a fresh one (6 hp) in its place, so a two-headed Gleeok takes 16 sword hits.
    """
    reach = rng.choice([9, 10, 11]) if rng else 10
    align = rng.choice([3, 4, 5]) if rng else 4
    standoff = rng.choice([24, 28, 32]) if rng else 28
    bomb_range = rng.choice([20, 26, 32]) if rng else 26
    rollout_frames = rng.choice([36, 48, 60]) if rng else 44
    retreat = rng.choice([44, 60, 76]) if rng else 60
    frames = 0
    hits = 0
    slot = None
    while frames < max_frames:
        s = emu.state()
        if s.hearts <= 0:
            return "died"
        if gleeok_dead(emu):
            emu.note(f"GLEEOK IS DEAD ({hits} hits landed)")
            return "clear"
        xs = emu.ram(0x70, 8)
        ys = emu.ram(0x84, 8)
        hp = emu.ram(0x485, 8)
        alive = [i for i in GLEEOK_SLOTS if hp[i] >> 4]
        if not alive:
            return "clear"
        if slot is None or slot not in alive:
            slot = max(alive, key=lambda i: abs(xs[i] - xs[1]) + abs(ys[i] - ys[1]))
        hx, hy = xs[slot], ys[slot]
        hp_before = hp[slot] >> 4
        dx, dy = hx - s.x, hy - s.y
        moves = []
        # A bomb is worth four sword hits, so with only four hearts it is the cheapest damage
        # available: place one when the head is close, then get clear of the blast.
        if s.bombs and max(abs(dx), abs(dy)) <= bomb_range:
            face = ("Right" if dx > 0 else "Left") if abs(dx) >= abs(dy) else ("Down" if dy > 0 else "Up")
            if bomb_head(emu, rec, slot, face, rng):
                hits += 4
                frames += 120
                continue
        if abs(dy) <= align and 0 <= abs(dx) - 16 <= reach:
            moves.append(("swing", "Right" if dx > 0 else "Left"))
        if abs(dx) <= align and 0 <= abs(dy) - 16 <= reach:
            moves.append(("swing", "Down" if dy > 0 else "Up"))
        if s.bombs and max(abs(dx), abs(dy)) <= 28:
            moves.append(("bomb", "Right" if dx > 0 else "Left"))
        # when the head is not strikeable, keep a real distance rather than hovering next to it
        gap = standoff if max(abs(dx), abs(dy)) <= standoff + 16 else retreat
        tx, ty = (hx, hy + gap) if hy + gap <= 197 else (hx - gap, hy)
        ddx, ddy = tx - s.x, ty - s.y
        toward = ("Right" if ddx > 0 else "Left") if abs(ddx) > abs(ddy) else ("Down" if ddy > 0 else "Up")
        moves.append(("step", toward))
        for d in ("Up", "Down", "Left", "Right"):
            if d != toward:
                moves.append(("step", d))
        moves.append(("wait", None))
        m = try_moves(emu, rec, moves, rollout=rollout_frames)
        frames += _cost(m)
        if m[0] in ("swing", "bomb") and (emu.ram(0x485, 8)[slot] >> 4) != hp_before:
            hits += 1
    return "timeout"


# ---------------------------------------------------------------- Dodongo (Level 2)
# Dodongo ignores the sword and ignores explosions. The only thing that hurts it is SWALLOWING a
# live bomb, and it takes two. Three things had to be right before this worked at all:
#   1. B throws whatever is in the B slot. Link carried the boomerang out of Level 1, so every
#      "bomb" was a boomerang toss (see bot.select_b_item).
#   2. The bomb is placed 17 px in FRONT of Link, not at his feet.
#   3. It only eats a bomb sitting exactly on the line it is walking along. Landing it seven
#      pixels off the row does nothing at all.
# So Link stands off the line, at the drop distance, ahead of it in its direction of travel,
# faces onto the line, drops, and backs straight off again.
DODONGO = 0x32
DROP_OFFSET = 17
FACE_VEC = {1: (1, 0), 2: (-1, 0), 4: (0, 1), 8: (0, -1)}
PERP = {"Up": ("Left", "Right"), "Down": ("Left", "Right"),
        "Left": ("Up", "Down"), "Right": ("Up", "Down")}
OPPOSITE_D = {"Up": "Down", "Down": "Up", "Left": "Right", "Right": "Left"}


def dodongos(emu):
    return [e for e in read_enemies(emu) if e[1] == DODONGO and e[0] < 8]


def fight_dodongo(emu, step, max_steps: int = 400) -> bool:
    """Feed Dodongo bombs until it dies. Two swallowed bombs kill it."""
    emu.note("DODONGO: the sword does nothing and a blast does nothing - it has to swallow a bomb, "
             "and it takes two. Lining the bomb up on the line it walks along")
    fed = 0
    for _ in range(max_steps):
        ds = dodongos(emu)
        if not ds:
            emu.note(f"Dodongo is dead after swallowing bombs ({fed} dropped)")
            return True
        e = ds[0]
        s = emu.state()
        if s.hearts <= 0:
            return False
        fx, fy = FACE_VEC.get(emu.byte(0x98 + e[0]), (0, -1))
        lead = 32                       # drop it this far ahead of the mouth
        if fx:                          # walking along a row: stand off the row, face onto it
            tx = e[2] + fx * lead
            opts = [(tx, e[3] + DROP_OFFSET, "Up", "Down"), (tx, e[3] - DROP_OFFSET, "Down", "Up")]
        else:                           # walking along a column
            ty = e[3] + fy * lead
            opts = [(e[2] + DROP_OFFSET, ty, "Left", "Right"),
                    (e[2] - DROP_OFFSET, ty, "Right", "Left")]
        opts = [o for o in opts if 24 <= o[0] <= 216 and 85 <= o[1] <= 189] or opts
        tx, ty, face, back = opts[0]
        dx, dy = tx - s.x, ty - s.y
        if abs(dx) <= 4 and abs(dy) <= 4 and s.bombs > 0:
            from .lookahead import face as _face_to
            _face_to(step, face)
            step("B", 2)
            step(back, 22)              # straight back off the line so it walks onto the bomb
            fed += 1
            for _ in range(12):
                step((), 8)
                if not dodongos(emu):
                    emu.note(f"Dodongo is dead ({fed} bombs dropped)")
                    return True
            continue
        d = ("Right" if dx > 0 else "Left") if abs(dx) >= abs(dy) else ("Down" if dy > 0 else "Up")
        step(d, 3)
    return not dodongos(emu)


# ---------------------------------------------------------------- Gohma
GOHMA_TYPES = (0x33, 0x34)      # 34 = blue (Level 6), 33 = red (Level 9)


def gohma_slot(emu: BizHawk) -> int | None:
    ts = emu.ram(0x34F, 12)
    for i in range(12):
        if ts[i] in GOHMA_TYPES:
            return i
    return None


def fight_gohma(emu: BizHawk, step, rng=None, max_steps: int = 400) -> bool:
    """Shoot Gohma's eye from directly underneath it.

    Measured with tactics.survey against the real boss, not taken from a guide: the sword, bombs,
    the boomerang and the recorder all do exactly zero from every angle, and an arrow does nothing
    either unless Link is below Gohma facing up. Two hits kill it.

    Staying on the bottom row is also the safe lane - Gohma's fireballs fan out downward and
    spread apart as they fall, so the row it is standing over is the emptiest part of the room.
    """
    import random
    rng = rng or random.Random()
    for _ in range(max_steps):
        if emu.byte(0x34D):
            return True
        s = emu.state()
        if s.hearts <= 0 or s.mode not in (5, 9):
            return False
        sl = gohma_slot(emu)
        if sl is None:
            return bool(emu.byte(0x34D))
        bx = emu.byte(0x70 + sl)
        if s.y < 180:                       # get back down to the bottom row
            step("Down", 4)
            continue
        # sidestep anything falling on this column
        ts = emu.ram(0x34F, 12); xs = emu.ram(0x70, 12); ys = emu.ram(0x84, 12)
        incoming = [i for i in range(12) if 0x50 <= ts[i] < 0x60
                    and abs(xs[i] - s.x) < 12 and 0 < s.y - ys[i] < 64]
        if incoming:
            step("Left" if s.x > bx else "Right", 3)
            continue
        if abs(s.x - bx) > 5:
            step("Right" if s.x < bx else "Left", 2 + rng.randint(0, 2))
            continue
        if s.rupees < 2:                    # every arrow costs a rupee; do not dry-fire
            step((), 8)
            continue
        from .lookahead import face as _face_to
        _face_to(step, "Up")
        step("B", 2)
        step((), 12 + rng.randint(0, 8))
    return bool(emu.byte(0x34D))
