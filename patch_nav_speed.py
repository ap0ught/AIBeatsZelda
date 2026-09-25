"""Navigator: go THROUGH enemies. No waiting, light avoidance weighted by real contact damage, swing at
what is directly in the way, ignore what cannot hurt (old men, burrowed Leevers, submerged Zoras).

Owner, after watching the 58-minute run: "you should generally just go through them and kill them if
they get in the way rather than avoid them. your pathing takes longer than just killing them."
Trace evidence: l4w04_18 swung ~60 times at a burrowed Leever (840 frames); l8_3c and s9_05 each stood
600 frames waiting for an old man's flame to move; 24% of the whole run was Link standing still.
OLD_AVOIDANCE[0] = True restores the previous behaviour for A/B probes."""
import ast
import pathlib


def load(path):
    raw = pathlib.Path(path).read_bytes()
    return raw.decode("utf-8").replace("\r\n", "\n"), b"\r\n" in raw


def save(path, t, crlf):
    ast.parse(t)
    pathlib.Path(path).write_bytes((t.replace("\n", "\r\n") if crlf else t).encode("utf-8"))


def sub(t, old, new, what):
    n = t.count(old)
    assert n == 1, f"{what}: {n} matches"
    print("  applied:", what)
    return t.replace(old, new)


t, crlf = load("zelda/overworld.py")

t = sub(t, '''def enemy_penalty(enemies, x: int, y: int) -> int:
    """Extra path cost for standing at (x, y) near enemies. Contact range is ~16 px.
    Blade traps can't be killed; their whole row and column are a danger band instead."""
    pen = 0
    for _, t, ex, ey, _ in enemies:''', '''_HARM: list | None = None


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
OLD_AVOIDANCE = [False]      # True restores the pre-2026-09-18 wide berth and waiting (A/B probes)


def enemy_penalty(enemies, x: int, y: int) -> int:
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
            if d < 16:
                pen += 5 * hh
            elif d < 28:
                pen += 1.5 * hh
            elif d < 44 and hh >= 3:
                pen += 1.0 * hh
        return int(pen * AVOID[0])
    pen = 0
    for _, t, ex, ey, _ in enemies:''', "harm table and light enemy penalty")

t = sub(t, '''    def live_enemies(self):
        static = self.static_items()
        return [e for e in read_enemies(self.emu) if e[0] not in static]
''', '''    def live_enemies(self):
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
            if t >= 0x40 or t in NEVER_CHASE or t in (0x0B, 0x0C):
                continue                      # bosses/flames, the unkillable, and Darknuts' shields
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
''', "threats() and _in_the_way()")

t = sub(t, '''        while attempt < max_replans and s.frame - f_start < frames_budget:
            enemies = self.live_enemies()
''', '''        swung: dict = {}
        while attempt < max_replans and s.frame - f_start < frames_budget:
            enemies = self.live_enemies() if OLD_AVOIDANCE[0] else self.threats()
            AVOID[0] = 1.0 if OLD_AVOIDANCE[0] else (4.0 if s.hearts <= 2.0 else 2.0 if s.hearts <= 3.0 else 1.0)
''', "go(): threats + avoidance scale")

t = sub(t, '''            for d in path[:horizon]:
                dx, dy = DIRS[d]
                target = (pos[0] + dx, pos[1] + dy)
                threat = self._danger(enemies, *target) if enemies else None
''', '''            for d in path[:horizon]:
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
''', "go(): cut through instead of waiting")

t = sub(t, '''                if self.jitter and self.jitter[0].random() < self.jitter[1]:
                    s = emu.step((), self.jitter[0].choice([1, 2, 3, 5, 8]))
                    self._check_alive(s)
                door = extra and any(''', '''                if self.jitter and self.jitter[0].random() < self.jitter[1]:
                    s = emu.step((), self.jitter[0].choice([1, 2, 3, 5, 8] if OLD_AVOIDANCE[0] else [1, 1, 2, 3]))
                    self._check_alive(s)
                door = extra and any(''', "smaller jitter pauses")
save("zelda/overworld.py", t, crlf)

t, crlf = load("zelda/search.py")
t = sub(t, '''        nav.jitter = (rng, rng.choice([0.05, 0.12, 0.25]))
        try:
            rec.step((), rng.randint(0, 40))''', '''        from .overworld import OLD_AVOIDANCE
        nav.jitter = (rng, rng.choice([0.05, 0.12, 0.25] if OLD_AVOIDANCE[0] else [0.0, 0.03, 0.08]))
        try:
            # The lead-in only has to shift the game's frame-driven randomness, and one frame does
            # that. It used to be 0-40 frames of Link standing still at the start of every crossing.
            rec.step((), rng.randint(0, 40) if OLD_AVOIDANCE[0] else rng.randint(0, 6))''', "cross policy lead-in")
save("zelda/search.py", t, crlf)

t, crlf = load("zelda/segments.py")
t = sub(t, '''        nav.jitter = (rng, rng.choice([0.05, 0.12, 0.25]))
        try:
            rec.step((), rng.randint(0, 40))''', '''        from .overworld import OLD_AVOIDANCE
        nav.jitter = (rng, rng.choice([0.05, 0.12, 0.25] if OLD_AVOIDANCE[0] else [0.0, 0.03, 0.08]))
        try:
            rec.step((), rng.randint(0, 40) if OLD_AVOIDANCE[0] else rng.randint(0, 6))''', "cross_at policy lead-in")
save("zelda/segments.py", t, crlf)
print("navigator patched")
