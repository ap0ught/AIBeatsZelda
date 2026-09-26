"""Sword combat from RAM.

Measured (probes/reach_trials.py, 40 swings at Zols): the wooden sword connects when the gap
between Link's box and the enemy's box is <= 10 px on the facing axis and the boxes overlap on the
other axis (we require |offset| <= 4). It misses at 13+ px. So fighting means getting nearly
touching-close, lining up, and swinging. Attacking is disabled while Link stands in a doorway.
"""
from __future__ import annotations

from .emulator import BizHawk, State
from .overworld import Navigator, NavError, LinkDied, read_enemies, read_room_item, enemy_name, snap, DIRS
from .lookahead import UNKILLABLE, killable
from . import ram

REACH = 10          # max box gap that still hits (measured)
ALIGN = 4           # max cross-axis offset between Link and the enemy


def enemy_hp(e) -> int:
    return e[4] >> 4


def find_enemy(emu: BizHawk, slot: int):
    for e in read_enemies(emu):
        if e[0] == slot:
            return e
    return None


class Fighter:
    def __init__(self, nav: Navigator):
        self.nav, self.emu = nav, nav.emu
        self.jitter = None       # (rng, probability) random pauses while positioning, used by search

    def _move(self, d: str, target_slot: int | None = None) -> State:
        """One step toward d, unless another enemy is about to be walked into; then step away from it."""
        emu = self.emu
        if self.jitter and self.jitter[0].random() < self.jitter[1]:
            emu.step((), self.jitter[0].choice([1, 2, 4]))
        s = emu.state()
        dx, dy = DIRS[d]
        nx, ny = s.x + dx, s.y + dy
        ens = read_enemies(emu)
        # blade traps: crossing their line is fine (they take ~50 frames to arrive from a corner);
        # what kills is lingering. Only react to a trap that is actually sliding and close.
        for e in ens:
            if e[1] != 0x49:
                continue
            parked = e[2] in (32, 208) and e[3] in (93, 189)
            if not parked and max(abs(e[2] - nx), abs(e[3] - ny)) < 36:
                if abs(e[3] - s.y) < 16:
                    return emu.step("Up" if s.y > e[3] or s.y > 141 else "Down", 1)
                return emu.step("Left" if s.x < e[2] and s.x > 40 else "Right", 1)
        for e in ens:
            if e[0] == target_slot or e[1] == 0x49:
                continue
            if max(abs(e[2] - nx), abs(e[3] - ny)) < 22:
                # something else is right there: step out of its line (perpendicular), not straight away
                ax, ay = s.x - e[2], s.y - e[3]
                if abs(ax) >= abs(ay):
                    away = "Up" if ay <= 0 else "Down"
                else:
                    away = "Left" if ax <= 0 else "Right"
                return emu.step(away, 1)
        return emu.step(d, 1)

    def swing(self, d: str, back_off: bool = False) -> State:
        """Face d and swing. Link is committed for ~12 frames. Optionally step back afterwards."""
        emu = self.emu
        from .lookahead import face
        face(emu.step, d)
        emu.step("A", 2)
        s = emu.step((), 11)
        if back_off:
            opp = {"Left": "Right", "Right": "Left", "Up": "Down", "Down": "Up"}[d]
            s = emu.step(opp, 6)
        return s

    DARKNUTS = (0x0B, 0x0C)
    BEAM_IMMUNE = {0x16, 0x1E, 0x2B, 0x2C, 0x2D}   # Pols Voice, Armos, Bubbles. Darknuts: beam works from side/back

    def _beam_ready(self, s: State) -> bool:
        """At full hearts the sword fires a beam: same damage, straight line, any range."""
        return s.hearts >= s.containers and s.containers > 0

    def _beam_shot(self, s: State, e) -> str | None:
        """Direction to fire a beam at e if aligned on a row/column and we're at full health."""
        if not self._beam_ready(s) or e[1] in self.BEAM_IMMUNE:
            return None
        dx, dy = e[2] - s.x, e[3] - s.y
        if e[1] in self.DARKNUTS:
            f = self._facing(e[0])           # a beam into its shield does nothing: only side/back
            if (f == 1 and dx < 0) or (f == 2 and dx > 0) or (f == 4 and dy < 0) or (f == 8 and dy > 0):
                return None
        if abs(dy) <= ALIGN and abs(dx) >= 24:
            return "Right" if dx > 0 else "Left"
        if abs(dx) <= ALIGN and abs(dy) >= 24:
            return "Down" if dy > 0 else "Up"
        return None
    PERP = {1: ("Up", "Down"), 2: ("Up", "Down"), 4: ("Left", "Right"), 8: ("Left", "Right")}

    def _facing(self, slot: int) -> int:
        return self.emu.byte(0x98 + slot)          # 1 R, 2 L, 4 D, 8 U

    def _in_front_of(self, e, s, facing: int, reach: int = 40) -> bool:
        """Is Link standing in the line this enemy faces along, within `reach`?"""
        dx, dy = s.x - e[2], s.y - e[3]
        if facing in (1, 2):
            return abs(dy) < 16 and 0 < (dx if facing == 1 else -dx) < reach
        return abs(dx) < 16 and 0 < (dy if facing == 4 else -dy) < reach

    def _sidestep(self, e, facing: int) -> State:
        """Leave a Darknut's line by moving perpendicular to its facing, away from room walls."""
        s = self.emu.state()
        a, b = self.PERP[facing]
        # pick the perpendicular direction that increases distance from the enemy's line
        if facing in (1, 2):
            d = "Up" if s.y <= e[3] else "Down"
        else:
            d = "Left" if s.x <= e[2] else "Right"
        return self.emu.step(d, 2)

    def attack_slot(self, slot: int, max_frames: int = 900) -> bool:
        """Kill the enemy in `slot`. Darknuts: approach from the side, strike at 90 degrees."""
        emu = self.emu
        e = find_enemy(emu, slot)
        if e is None:
            return True
        name = enemy_name(e[1])
        darknut = e[1] in self.DARKNUTS
        emu.note(f"FIGHT: {name} at ({e[2]},{e[3]}), hp {enemy_hp(e)}."
                 + (" Shielded in front: side hits only" if darknut else f" Need a gap of {REACH}px or less"))
        hearts0 = emu.state().hearts
        swings = hits = 0
        frames = 0
        while frames < max_frames:
            e = find_enemy(emu, slot)
            if e is None:
                emu.note(f"The {name} is dead ({swings} swings, {hits} hits)")
                return True
            s = emu.state()
            if s.hearts <= 0:
                raise LinkDied("died fighting")
            if s.hearts < hearts0:
                emu.note(f"MISTAKE (unplanned hit): hit by the {name}, {s.hearts} hearts left")
                hearts0 = s.hearts
            ex, ey = e[2], e[3]
            dx, dy = ex - s.x, ey - s.y
            gx, gy = abs(dx) - 16, abs(dy) - 16
            beam = self._beam_shot(s, e)
            if beam:
                if swings == 0:
                    emu.note(f"Full hearts: firing sword beams at the {name} from range instead of closing in")
                hp0 = enemy_hp(e)
                s = self.swing(beam)
                s = emu.step((), 10)                 # let the beam travel
                swings += 1; frames += 24
                e2 = find_enemy(emu, slot); hits += (e2 is None or enemy_hp(e2) < hp0)
                continue
            facing = self._facing(slot) if darknut else 0
            # 1. never stand in a Darknut's line: sidestep out of it first
            if darknut:
                threat = None
                for o in read_enemies(emu):
                    if o[1] in self.DARKNUTS and self._in_front_of(o, s, self._facing(o[0])):
                        threat = o
                        break
                if threat is not None:
                    s = self._sidestep(threat, self._facing(threat[0]))
                    frames += 2
                    continue
            # 2. in position? swing (for Darknuts only from the side/back)
            front_h = darknut and ((facing == 1 and dx < 0) or (facing == 2 and dx > 0))
            front_v = darknut and ((facing == 4 and dy < 0) or (facing == 8 and dy > 0))
            if abs(dy) <= ALIGN and 0 <= gx <= REACH and not front_h:
                hp0 = enemy_hp(e)
                s = self.swing("Right" if dx > 0 else "Left")
                swings += 1; frames += 14
                e2 = find_enemy(emu, slot)
                if e2 is None or enemy_hp(e2) < hp0:
                    hits += 1
                continue
            if abs(dx) <= ALIGN and 0 <= gy <= REACH and not front_v:
                hp0 = enemy_hp(e)
                s = self.swing("Down" if dy > 0 else "Up")
                swings += 1; frames += 14
                e2 = find_enemy(emu, slot)
                if e2 is None or enemy_hp(e2) < hp0:
                    hits += 1
                continue
            # 3. choose where to stand. Darknuts: beside them, relative to their facing.
            if darknut:
                off = 16 + REACH - 4
                if facing in (4, 8):      # faces up/down -> stand left or right of it
                    cands = [(ex - off, ey), (ex + off, ey)]
                else:                     # faces left/right -> stand above or below it
                    cands = [(ex, ey - off), (ex, ey + off)]
                tx, ty = min(cands, key=lambda c: abs(c[0] - s.x) + abs(c[1] - s.y))
                tx, ty = snap(max(16, min(224, tx)), max(69, min(205, ty)))
                ddx, ddy = tx - s.x, ty - s.y
                if ddx == 0 and ddy == 0:
                    s = emu.step((), 1); frames += 1
                    continue
                # move on the axis perpendicular to its facing first (stays out of its line)
                if facing in (4, 8):
                    d = ("Right" if ddx > 0 else "Left") if ddx else ("Down" if ddy > 0 else "Up")
                else:
                    d = ("Down" if ddy > 0 else "Up") if ddy else ("Right" if ddx > 0 else "Left")
            else:
                if abs(dy) <= abs(dx):
                    if abs(dy) > ALIGN:
                        d = "Down" if dy > 0 else "Up"
                    elif gx > REACH - 4:
                        d = "Right" if dx > 0 else "Left"
                    else:
                        d = "Left" if dx > 0 else "Right"
                else:
                    if abs(dx) > ALIGN:
                        d = "Right" if dx > 0 else "Left"
                    elif gy > REACH - 4:
                        d = "Down" if dy > 0 else "Up"
                    else:
                        d = "Up" if dy > 0 else "Down"
            s = self._move(d, slot)
            frames += 1
        emu.note(f"Couldn't finish the {name} in {max_frames} frames ({swings} swings, {hits} hits)")
        return False


    # ---------------------------------------------------------------- Darknut hunting
    def _step8(self, d: str, target_slot: int | None = None, frames: int = 8) -> State:
        """A committed 8 px step: hold one direction until Link has moved a grid step (or stalls)."""
        emu = self.emu
        s0 = emu.state()
        s = s0
        for _ in range(frames):
            s = self._move(d, target_slot)
            if abs(s.x - s0.x) >= 8 or abs(s.y - s0.y) >= 8 or s.hearts < s0.hearts:
                break
        return s

    DKV = {1: (1, 0), 2: (-1, 0), 4: (0, 1), 8: (0, -1)}   # Darknut velocity per facing (~1 px/frame)

    def _predicted_contact(self, s, e, facing: int, horizon: int, margin: int = 4) -> bool:
        """Will this Darknut's box come within `margin` px of Link's box within `horizon` frames,
        assuming it keeps walking its line? (It can't turn before the next tile centre.)"""
        vx, vy = self.DKV.get(facing, (0, 0))
        for t in range(0, horizon + 1, 2):
            ex, ey = e[2] + vx * t, e[3] + vy * t
            if abs(ex - s.x) < 16 + margin and abs(ey - s.y) < 16 + margin:
                return True
        return False

    def _escape(self, s, e, facing: int) -> str:
        """Direction that leaves this Darknut's path: perpendicular to its movement, away from it.
        If that side is a wall (Link at a room edge), use the other perpendicular; if both are
        blocked, retreat along its line."""
        from .overworld import read_cells, legal
        cells = read_cells(self.emu)
        kb = self.nav.kb
        kb.use(s.level)
        if facing in (1, 2):
            prefs = ["Up", "Down"] if s.y <= e[3] else ["Down", "Up"]
            prefs.append("Right" if facing == 1 else "Left")
        else:
            prefs = ["Left", "Right"] if s.x <= e[2] else ["Right", "Left"]
            prefs.append("Down" if facing == 4 else "Up")
        for d in prefs:
            ddx, ddy = DIRS[d]
            if legal(cells, kb, s.x + ddx, s.y + ddy, optimistic=True):
                return d
        return prefs[0]

    def hunt_darknut(self, slot: int, max_frames: int = 1500) -> bool:
        """Darknuts: contact hurts from any side, so every step and every swing is checked
        against where each Darknut will be over the next frames. Strike only from side/behind
        when it is walking away or across, never when it is coming at us."""
        emu = self.emu
        e = find_enemy(emu, slot)
        if e is None:
            return True
        name = enemy_name(e[1])
        emu.note(f"HUNT: {name} at ({e[2]},{e[3]}), hp {enemy_hp(e)}. Predicting its path; side/back hits only")
        hearts0 = emu.state().hearts
        swings = hits = frames = 0
        hold = None          # (direction, frames left) to avoid dithering
        cool = 0             # frames to hold still after an escape
        while frames < max_frames:
            e = find_enemy(emu, slot)
            if e is None:
                emu.note(f"The {name} is dead ({swings} swings, {hits} hits)")
                return True
            s = emu.state()
            if s.hearts <= 0:
                raise LinkDied("died hunting")
            if s.hearts < hearts0:
                emu.note(f"MISTAKE (unplanned hit): hit by the {name}, {s.hearts} hearts left")
                hearts0 = s.hearts
            dks = [(o, self._facing(o[0])) for o in read_enemies(emu) if o[1] in self.DARKNUTS]
            # 1. escape anything about to touch us: a committed step fully out of its lane, and no
            #    approaching again until it has passed (approach and escape must never fight)
            danger = [(o, f) for o, f in dks if self._predicted_contact(s, o, f, 20)]
            if danger:
                o, f = min(danger, key=lambda of: abs(of[0][2] - s.x) + abs(of[0][3] - s.y))
                d = self._escape(s, o, f)
                s = emu.step(d, 8); frames += 8
                hold = None
                cool = 12
                continue
            if cool:
                cool -= 1
                s = emu.step((), 1); frames += 1
                continue
            ex, ey = e[2], e[3]
            f = self._facing(slot)
            vx, vy = self.DKV.get(f, (0, 0))
            dx, dy = ex - s.x, ey - s.y
            # 2. strike if in reach from side/behind and nothing will touch us during the swing
            coming = (vx and (vx > 0) == (dx < 0) and abs(dy) < 16) or (vy and (vy > 0) == (dy < 0) and abs(dx) < 16)
            safe_swing = not any(self._predicted_contact(s, o, ff, 18, margin=2) for o, ff in dks)
            if not coming and safe_swing:
                if abs(dy) <= ALIGN and 0 <= abs(dx) - 16 <= REACH:
                    hp0 = enemy_hp(e)
                    s = self.swing("Right" if dx > 0 else "Left")
                    swings += 1; frames += 14
                    e2 = find_enemy(emu, slot); hits += (e2 is None or enemy_hp(e2) < hp0)
                    continue
                if abs(dx) <= ALIGN and 0 <= abs(dy) - 16 <= REACH:
                    hp0 = enemy_hp(e)
                    s = self.swing("Down" if dy > 0 else "Up")
                    swings += 1; frames += 14
                    e2 = find_enemy(emu, slot); hits += (e2 is None or enemy_hp(e2) < hp0)
                    continue
            # 3. approach a spot behind it (or beside it if it is standing still)
            back = 16 + REACH - 4
            if vx or vy:
                tx, ty = ex - vx * back, ey - vy * back
            else:
                tx, ty = (ex - back, ey) if s.x <= ex else (ex + back, ey)
            tx, ty = snap(max(16, min(224, tx)), max(69, min(205, ty)))
            ddx, ddy = tx - s.x, ty - s.y
            if abs(ddx) < 3 and abs(ddy) < 3:
                s = emu.step((), 1); frames += 1
                continue
            if hold and hold[1] > 0:
                d = hold[0]; hold = (d, hold[1] - 1)
            else:
                # cross-lane offset first so we never walk down its line toward it
                if vx:
                    d = ("Down" if ddy > 0 else "Up") if abs(ddy) >= 3 else ("Right" if ddx > 0 else "Left")
                else:
                    d = ("Right" if ddx > 0 else "Left") if abs(ddx) >= 3 else ("Down" if ddy > 0 else "Up")
                hold = (d, 3)
            # the step itself must not end inside any Darknut's near-future path
            ndx, ndy = DIRS[d]
            nxt = type("S", (), {"x": s.x + ndx, "y": s.y + ndy})
            if any(self._predicted_contact(nxt, o, ff, 8) for o, ff in dks):
                s = emu.step((), 1); frames += 1; hold = None
                continue
            s = self._move(d, slot); frames += 1
        emu.note(f"Couldn't finish the {name} in {max_frames} frames ({swings} swings, {hits} hits)")
        return False


    def darknut_ambush(self, max_frames: int = 3600, post=None, rng=None) -> bool:
        """Crowded Darknut rooms (walkthrough technique): take a post beside a block so they can only
        come from limited directions, stand still, strike each one as it walks past (side/back only),
        and step out of any predicted contact. Kills everything that is a Darknut."""
        from .overworld import read_cells, box_cells
        emu = self.emu
        self.nav.kb.use(emu.state().level, emu.state().mode)
        cells = read_cells(emu)
        blocks = {(r // 2, k // 2) for r in range(4, 18) for k in range(4, 28) if cells[r][k] in (0xB0, 0xB1, 0xB2, 0xB3)}
        # candidate posts: floor tiles with a block directly left or right and open space on the other side
        cands = []
        for (br, bc) in blocks:
            for side in (-1, 1):
                pr, pc = br, bc + side
                if (pr, pc) in blocks or not (2 <= pc <= 13 and 1 <= pr <= 9):
                    continue
                x, y = pc * 16, 64 + pr * 16 - 3
                if all(self.nav.kb.is_walkable(cells[cy][cx], False) for cy, cx in box_cells(x, y)):
                    cands.append((x, y))
        if not cands:
            return self.clear_room()
        if post is None:
            s = emu.state()
            dks0 = [o for o in read_enemies(emu) if o[1] in self.DARKNUTS]
            def safety(c):   # far from every Darknut, but not absurdly far from us
                return min((max(abs(o[2] - c[0]), abs(o[3] - c[1])) for o in dks0), default=999) - 0.1 * (abs(c[0] - s.x) + abs(c[1] - s.y))
            cands.sort(key=safety, reverse=True)
            post = cands[rng.randrange(min(3, len(cands)))] if rng else cands[0]
        emu.note(f"DARKNUT AMBUSH: taking a post beside a block at {post}, the spot farthest from them; striking as they pass")
        self.nav.no_kill = True
        try:
            self.nav.go(lambda x, y: x == post[0] and y == post[1], "the ambush post", max_replans=80)
        except Exception as e:
            emu.note(f"couldn't reach the post: {str(e)[:50]}")
        finally:
            self.nav.no_kill = False
        hearts0 = emu.state().hearts
        swings = hits = frames = 0
        while frames < max_frames:
            s = emu.state()
            if s.hearts <= 0:
                raise LinkDied("died in ambush")
            if s.hearts < hearts0:
                emu.note(f"MISTAKE (unplanned hit): Darknut got me at the post, {s.hearts} hearts left")
                hearts0 = s.hearts
            dks = [(o, self._facing(o[0])) for o in read_enemies(emu) if o[1] in self.DARKNUTS]
            if not dks:
                emu.note(f"All Darknuts dead from the post ({swings} swings, {hits} hits)")
                self.collect_drop()
                return True
            danger = [(o, f) for o, f in dks if self._predicted_contact(s, o, f, 12)]
            if danger:
                o, f = min(danger, key=lambda of: abs(of[0][2] - s.x) + abs(of[0][3] - s.y))
                s = emu.step(self._escape(s, o, f), 2); frames += 2
                continue
            struck = False
            for o, f in dks:
                vx, vy = self.DKV.get(f, (0, 0))
                dx, dy = o[2] - s.x, o[3] - s.y
                coming = (vx and (vx > 0) == (dx < 0) and abs(dy) < 16) or (vy and (vy > 0) == (dy < 0) and abs(dx) < 16)
                if coming:
                    continue
                if abs(dy) <= ALIGN and 0 <= abs(dx) - 16 <= REACH:
                    hp0 = enemy_hp(o); s = self.swing("Right" if dx > 0 else "Left"); swings += 1; frames += 14
                    o2 = find_enemy(emu, o[0]); hits += (o2 is None or enemy_hp(o2) < hp0); struck = True; break
                if abs(dx) <= ALIGN and 0 <= abs(dy) - 16 <= REACH:
                    hp0 = enemy_hp(o); s = self.swing("Down" if dy > 0 else "Up"); swings += 1; frames += 14
                    o2 = find_enemy(emu, o[0]); hits += (o2 is None or enemy_hp(o2) < hp0); struck = True; break
            if struck:
                continue
            # drift back to the post if we were pushed off it; otherwise hold
            if abs(s.x - post[0]) > 4 or abs(s.y - post[1]) > 4:
                d = ("Right" if post[0] > s.x else "Left") if abs(post[0] - s.x) > abs(post[1] - s.y) else ("Down" if post[1] > s.y else "Up")
                s = self._move(d); frames += 1
            else:
                s = emu.step((), 1); frames += 1
        emu.note(f"Ambush timed out with Darknuts alive ({swings} swings, {hits} hits)")
        return False


    def bomb_darknuts(self, keep: int = 2, max_frames: int = 3000, rng=None) -> bool:
        """Crowded Darknut rooms with bombs to spare: when one walks toward Link along his row or
        column from far enough away, drop a bomb in its lane and step out of the line. The fuse
        (~76 frames) meets it as it arrives. Sword-finish whatever survives."""
        emu = self.emu
        self.nav.kb.use(emu.state().level, emu.state().mode)
        emu.note(f"BOMBING DARKNUTS: {emu.state().bombs} bombs, keeping {keep}. Drop in their lane, sidestep, let the fuse work")
        hearts0 = emu.state().hearts
        frames = last_bomb = 0
        min_dist = rng.choice([48, 56, 64, 72]) if rng else 60
        while frames < max_frames:
            s = emu.state()
            if s.hearts <= 0:
                raise LinkDied("died bombing")
            if s.hearts < hearts0:
                emu.note(f"MISTAKE (unplanned hit): hit while bombing, {s.hearts} hearts left")
                hearts0 = s.hearts
            dks = [(o, self._facing(o[0])) for o in read_enemies(emu) if o[1] in self.DARKNUTS]
            if not dks:
                emu.note("Darknuts gone")
                self.collect_drop()
                return True
            if s.bombs <= keep:
                emu.note(f"Down to {s.bombs} bombs (keeping {keep}); finishing with the sword")
                return self.clear_room_sword()
            danger = [(o, f) for o, f in dks if self._predicted_contact(s, o, f, 12)]
            if danger:
                o, f = min(danger, key=lambda of: abs(of[0][2] - s.x) + abs(of[0][3] - s.y))
                s = emu.step(self._escape(s, o, f), 2); frames += 2
                continue
            # a Darknut coming straight at us along our row/column from far enough: bomb its lane
            placed = False
            if frames - last_bomb > 90:
                for o, f in dks:
                    vx, vy = self.DKV.get(f, (0, 0))
                    dx, dy = o[2] - s.x, o[3] - s.y
                    if vx and abs(dy) <= 6 and (vx > 0) == (dx < 0) and min_dist <= abs(dx) <= 120:
                        face = "Left" if dx < 0 else "Right"
                    elif vy and abs(dx) <= 6 and (vy > 0) == (dy < 0) and min_dist <= abs(dy) <= 120:
                        face = "Up" if dy < 0 else "Down"
                    else:
                        continue
                    emu.step(face, 1); emu.step("B", 2); frames += 3
                    last_bomb = frames
                    emu.note(f"Bomb dropped in the lane of a Darknut {abs(dx) if vx else abs(dy)} px away; stepping out of its line")
                    s = emu.step(self._escape(s, o, f), 8); frames += 8
                    placed = True
                    break
            if placed:
                continue
            # otherwise line up on a lane: move so that some Darknut's row or column passes through us at a distance
            o, f = min(dks, key=lambda of: abs(of[0][2] - s.x) + abs(of[0][3] - s.y))
            vx, vy = self.DKV.get(f, (0, 0))
            if vx:
                d = "Down" if o[3] > s.y + 6 else "Up" if o[3] < s.y - 6 else None
            elif vy:
                d = "Right" if o[2] > s.x + 6 else "Left" if o[2] < s.x - 6 else None
            else:
                d = None
            if d:
                s = self._move(d, o[0]); frames += 1
            else:
                s = emu.step((), 2); frames += 2
        emu.note("Bombing timed out")
        return False

    def clear_room_sword(self, max_enemies: int = 12) -> bool:
        """Kill everything with the sword only (no bomb/ambush dispatch)."""
        emu = self.emu
        for _ in range(max_enemies * 3):
            s = emu.state()
            ens = [e for e in read_enemies(emu) if e[1] != 0x49 and e[1] < 0x50]
            if not ens:
                self.collect_drop(); return True
            walkers = [e for e in ens if e[1] not in self.FLIERS]
            if walkers:
                walkers.sort(key=lambda e: abs(e[2] - s.x) + abs(e[3] - s.y))
                (self.hunt_darknut if walkers[0][1] in self.DARKNUTS else self.attack_slot)(walkers[0][0])
            elif not self.ambush():
                break
            self.collect_drop()
        return not [e for e in read_enemies(emu) if killable(e)]

    FLIERS = {0x1B, 0x1C, 0x1D, 0x1A, 0x22}   # Keese, Peahat, flying Ghini: don't chase, ambush

    def _hittable(self, s: State, e):
        """Direction to swing if the enemy is in reach right now, else None."""
        dx, dy = e[2] - s.x, e[3] - s.y
        if abs(dy) <= ALIGN + 2 and -4 <= abs(dx) - 16 <= REACH:
            return "Right" if dx > 0 else "Left"
        if abs(dx) <= ALIGN + 2 and -4 <= abs(dy) - 16 <= REACH:
            return "Down" if dy > 0 else "Up"
        return None

    def ambush(self, max_frames: int = 1800) -> bool:
        """Stand mostly still and swing at whatever flies into reach. Small steps to line up
        when one hovers nearby. Returns True when no fliers remain."""
        emu = self.emu
        emu.note("AMBUSH: fliers are too erratic to chase. Holding position and swinging when one comes close")
        hearts0 = emu.state().hearts
        swings = hits = 0
        frames = 0
        while frames < max_frames:
            s = emu.state()
            if s.hearts <= 0:
                raise LinkDied("died in ambush")
            if s.hearts < hearts0:
                emu.note(f"MISTAKE (unplanned hit): clipped by a flier, {s.hearts} hearts left")
                hearts0 = s.hearts
            ens = [e for e in read_enemies(emu) if e[1] in self.FLIERS]
            if not ens:
                emu.note(f"No fliers left ({swings} swings, {hits} hits)")
                return True
            target = None
            for e in ens:
                d = self._hittable(s, e) or self._beam_shot(s, e)
                if d:
                    target = (e, d)
                    break
            if target:
                e, d = target
                hp0 = enemy_hp(e)
                self.swing(d)
                swings += 1; frames += 14
                e2 = find_enemy(emu, e[0])
                if e2 is None or enemy_hp(e2) < hp0:
                    hits += 1
                continue
            # nudge toward alignment with the nearest one if it's hovering close; otherwise wait
            e = min(ens, key=lambda e: abs(e[2] - s.x) + abs(e[3] - s.y))
            dx, dy = e[2] - s.x, e[3] - s.y
            if max(abs(dx), abs(dy)) <= 40:
                if abs(dy) < abs(dx) and abs(dy) > ALIGN:
                    emu.step("Down" if dy > 0 else "Up", 1)
                elif abs(dx) <= abs(dy) and abs(dx) > ALIGN:
                    emu.step("Right" if dx > 0 else "Left", 1)
                else:
                    emu.step((), 1)
            else:
                emu.step((), 2)
                frames += 1
            frames += 1
        emu.note(f"Ambush timed out ({swings} swings, {hits} hits)")
        return False

    # item ids that enemies drop (the drop uses the room-item slot $AB/$83/$97/$BF)
    DROPS = {0x00: "bombs", 0x0F: "5 rupees", 0x18: "rupee", 0x19: "key", 0x21: "clock", 0x22: "heart", 0x23: "fairy"}

    # A dead monster's object slot turns into the pickup while its drop lies on the floor.
    DROP_TYPE = 0x60

    def visible_drops(self):
        """Every item lying in the room: the room item AND each monster's drop, as (id, x, y, slot).

        For most of this project the harness looked only at the room item (object slot 0x13), which is
        where keys and dungeon treasure live. A monster's drop lives somewhere else entirely: the game
        converts the dead monster's OWN slot into the pickup - object type $60, item id at $AC+slot
        (disassembly Z_07 UpdateMetaObjectEnd, Z_04 SetUpDroppedItem). So every rupee, heart and bomb
        a fight produced was invisible, and Link only collected the ones he happened to walk over. The
        finished run's farms ran at 600-900 frames per rupee, which is what blindness looks like."""
        emu = self.emu
        out = []
        item = read_room_item(emu)
        if item is not None and item[0] in self.DROPS:
            out.append((item[0], item[1], item[2], None))
        blk = emu.ram(0x70, 0x2EB)          # x $70, y $84, item id $AC, type $34F in one read
        for i in range(1, 12):
            kind = blk[0xAC - 0x70 + i]
            if blk[0x34F - 0x70 + i] == self.DROP_TYPE and kind in self.DROPS:
                out.append((kind, blk[i], blk[0x84 - 0x70 + i], i))
        return out

    def _worth(self, t, s) -> bool:
        """Is this drop worth walking for right now? Only what Link can actually use."""
        if t in (0x22, 0x23):                  # heart, fairy: only while hurt
            return s.hearts < s.containers
        if t == 0x00:                          # bombs: only below capacity (MaxBombs, $67C)
            return s.bombs < max(8, self.emu.byte(0x67C))
        if t == 0x21:                          # clock: not worth a detour
            return False
        if t == 0x19:                          # key: only when there is a door to open
            # This used to fall through to an unconditional True, which is where the
            # disagreement with plan_fight came from: the collector would spend up to
            # max_detour pixels and max_frames of the run on a key the planner had
            # deliberately valued below a bomb, because a key is not a consumable and the
            # heart-deficit `want` had nothing to say about it. The planner now prices a
            # key by scarcity (KEY_WANT_SCARCE / KEY_WANT_HELD in lookahead.py), and this
            # answers the same question the same way: a key is worth the walk when Link has
            # none, and is not when he has some. A key cannot come from a monster drop - the
            # full set a monster produces is bomb / 5 rupees / rupee / clock / heart / fairy
            # - so a key lying here is a room item, and a spare one is just a door that is
            # already open.
            return s.keys <= 0
        return True                            # rupees, five rupees

    def collect_drop(self, max_frames: int = 240, max_detour: int = 120) -> bool:
        """Pick up what the fight left behind, nearest first, as long as it is worth the walk.

        Several drops can land at once, so take up to four, but never chase one more than
        `max_detour` pixels away or spend more than `max_frames` frames in total."""
        from .overworld import snap, NavError
        emu, nav = self.emu, self.nav
        took = False
        f0 = emu.state().frame
        for _ in range(4):
            s = emu.state()
            if s.frame - f0 > max_frames:
                break
            drops = [d for d in self.visible_drops() if self._worth(d[0], s)]
            if not drops:
                break
            t, ix, iy, slot = min(drops, key=lambda d: abs(d[1] - s.x) + abs(d[2] - s.y))
            if abs(ix - s.x) + abs(iy - s.y) > max_detour:
                break
            name = self.DROPS[t]

            def gone():
                if slot is None:
                    return read_room_item(emu) is None
                return emu.ram(0x34F, 12)[slot] != self.DROP_TYPE

            emu.note(f"DROP: a {name} at ({ix},{iy}). Grabbing it")
            tx, ty = snap(ix, iy)
            try:
                nav.go(lambda x, y: abs(x - tx) <= 8 and abs(y - ty) <= 8, f"the {name}", max_replans=30)
                for _ in range(3):
                    if gone():
                        break
                    nav.go(lambda x, y: x == tx and y == ty, f"the {name} exactly", max_replans=10)
                    emu.step((), 4)
            except NavError as e:
                emu.note(f"Couldn't reach the {name}: {str(e)[:50]}")
                break
            if gone():
                s2 = emu.state()
                emu.note(f"Got the {name}: hearts {s2.hearts}, bombs {s2.bombs}, rupees {s2.rupees}")
                took = True
            else:
                emu.note(f"The {name} vanished before I got there")
                break
        return took

    def clear_room(self, max_enemies: int = 12) -> bool:
        """Kill everything in the room: walkers nearest first, fliers by ambush. Collect drops."""
        emu = self.emu
        emu.note("CLEARING THE ROOM: every enemy must die before the doors open")
        s = emu.state()
        self.nav.kb.use(s.level, s.mode)
        self._ambushed = False
        if s.level and (s.x <= 16 or s.x >= 224 or s.y >= 205 or s.y <= 69):
            d = "Right" if s.x <= 16 else "Left" if s.x >= 224 else "Up" if s.y >= 205 else "Down"
            emu.step(d, 20)     # never fight from a doorway (attacks are disabled there)
        for _ in range(max_enemies * 3):
            s = emu.state()
            ens = [e for e in read_enemies(emu) if killable(e)]   # traps, bubbles and projectiles don't count
            if not ens:
                self.collect_drop()
                emu.note("Room clear")
                return True
            walkers = [e for e in ens if e[1] not in self.FLIERS]
            if sum(1 for e in walkers if e[1] in self.DARKNUTS) >= 3 and not getattr(self, "_ambushed", False):
                self._ambushed = True
                rng = self.jitter[0] if self.jitter else None
                if getattr(self, "use_bombs", False) and s.bombs >= 3:
                    if self.bomb_darknuts(rng=rng):
                        continue
            traps = [e for e in read_enemies(emu) if e[1] == 0x49]
            def in_trap_line(e):
                return any(abs(t[2] - e[2]) < 12 or abs(t[3] - e[3]) < 12 for t in traps)
            if walkers:
                # prefer targets that are not sitting in a blade trap's line; wait a little for others to leave it
                safe = [e for e in walkers if not in_trap_line(e)]
                if not safe:
                    waited = 0
                    while waited < 120 and not safe:
                        emu.step((), 4); waited += 4
                        walkers = [e for e in read_enemies(emu) if e[1] not in self.FLIERS and killable(e)]
                        safe = [e for e in walkers if not in_trap_line(e)]
                    if not safe:
                        if walkers:
                            emu.note("Target is parked in a trap line; attacking anyway with care")
                        safe = walkers
                    if not safe:
                        continue
                walkers = safe
                walkers.sort(key=lambda e: abs(e[2] - s.x) + abs(e[3] - s.y))
                if walkers[0][1] in self.DARKNUTS:
                    self.hunt_darknut(walkers[0][0])
                else:
                    self.attack_slot(walkers[0][0])
            else:
                if not self.ambush():
                    break
            self.collect_drop()
        return not [e for e in read_enemies(emu) if killable(e)]

    def grab_key_by_dodging(self, item_type: int = 0x19) -> State | None:
        """Fetch the room's item using avoidance navigation, not combat."""
        emu, nav = self.emu, self.nav
        item = read_room_item(emu)
        if item is None:
            emu.note("No item on the floor to grab")
            return None
        t, ix, iy = item
        emu.note(f"Grabbing the item (type {t:02X}) at ({ix},{iy}) by dodging the enemies, not fighting")
        tx, ty = snap(ix, iy)
        s = nav.go(lambda x, y: abs(x - tx) <= 8 and abs(y - ty) <= 8, "the item", max_replans=120)
        for _ in range(4):
            if read_room_item(emu) is None:
                emu.note(f"Got it. Keys now {emu.state().keys}")
                return emu.state()
            s = nav.go(lambda x, y: x == tx and y == ty, "the item exactly", max_replans=40)
        return emu.state()
