"""Several scouts search a segment at once; hearts priced by what they are worth; atomic knowledge files.

* zelda/search.py: parallel_search() - K emulators, one thread each, attempts handed out by seed; the same
  ranking and early-stop rules as random_search. rank() becomes value_of(): hearts are worth a lot when Link is
  low and little when he has plenty, nothing beyond survival when a refill is coming (HEARTS_FREE), and the
  low-health cliff scales with how many containers he has (an absolute "below 4" made every attempt in the
  three-heart early game look nearly dead).
* zelda/runner.py: ZELDA_SCOUTS scouts (default 4); sets the per-segment context (REFILL_SOON).
* zelda/overworld.py: tiles.json / blocks.json written atomically under a lock; pen_scale passed down, not global.
"""
import ast
import pathlib


def load(path):
    raw = pathlib.Path(path).read_bytes()
    return raw.decode("utf-8").replace("\r\n", "\n"), b"\r\n" in raw


def save(path, t, crlf):
    ast.parse(t)
    pathlib.Path(path).write_bytes((t.replace("\n", "\r\n") if crlf else t).encode("utf-8"))


def sub(t, old, new, what, count=1):
    n = t.count(old)
    assert n == count, f"{what}: {n} matches"
    print("  applied:", what)
    return t.replace(old, new)


# ------------------------------------------------------------------ search.py
t, crlf = load("zelda/search.py")
t = sub(t, '''def random_search(emu: BizHawk, state_name: str, policy, success, *, tries: int = 60,''', '''# Segments after which every heart is refilled (a boss's Triforce piece), or after which hearts no longer
# matter at all (Ganon onward): there an attempt's health is worth nothing beyond staying alive.
HEARTS_FREE = [False]


def value_of(a, containers: float) -> float:
    """Frames-equivalent worth of an attempt: faster is better, and health is worth frames - a lot when Link
    is low, little when he has plenty. (Owner: "be more aggressive"; "our main goal is to win quickly".)"""
    h = a.hearts
    if HEARTS_FREE[0]:
        return -a.frames + (200 if h >= 2 else 0)
    v = 600 * min(h, 4) + 300 * max(0.0, min(h, 7) - 4) + 120 * max(0.0, h - 7)
    cliff = min(4.0, max(1.5, 0.5 * containers))
    if h < cliff:
        v -= (cliff - h) * 4000
    return v - a.frames


def parallel_search(scouts, navs, state_name: str, factory, success, *, tries: int = 60, max_frames: int = 900,
                    setup=None, log=print, label: str = "", patience: int = 8):
    """random_search across several emulators at once: one thread per scout, attempts handed out by seed.
    Same ranking, same early stop. Emulation releases the GIL (it is socket I/O), so K scouts run K attempts
    in nearly the time of one. The winner is an input list from the shared start state, exactly as before."""
    import threading
    lock = threading.Lock()
    st = {"next": 0, "best": None, "since": 0, "stop": False, "done": 0, "containers": 3.0, "h0": None}
    fails: dict = {}
    t0 = time.time()
    scouts[0].note(f"SEARCH{': ' + label if label else ''}: up to {tries} attempts on {len(scouts)} scouts")

    def work(k):
        emu, nav = scouts[k], navs[k]
        policy = factory(nav)
        while True:
            with lock:
                if st["stop"] or st["next"] >= tries:
                    return
                i = st["next"]
                st["next"] += 1
            rng = random.Random(1000 + i)
            s_start = emu.load(state_name)
            rec = Recorder(emu)
            rec.step((), 2)
            if setup:
                setup(rec, nav)
            try:
                outcome = policy(emu, rec, rng, max_frames)
            except LinkDied:
                outcome = "died"
            except TimeoutError as e:
                outcome = "timeout: " + str(e)[:40]
            s = emu.state()
            try:
                ok = outcome != "died" and success(emu, s)
            except Exception:
                ok = False
            a = Attempt(1000 + i, rec.inputs, len(rec.inputs), ok, s.hearts, outcome)
            with lock:
                st["done"] += 1
                st["containers"] = max(st["containers"], s.containers)
                if st["h0"] is None:
                    st["h0"] = s_start.hearts
                if not ok:
                    key = f"{str(outcome)[:50]} @ room {s.room:02X} L{s.level}"
                    fails[key] = fails.get(key, 0) + 1
                best = st["best"]
                c = st["containers"]
                if ok and (best is None or value_of(a, c) > value_of(best, c)):
                    st["best"] = best = a
                    st["since"] = 0
                    log(f"  attempt {i+1}: success {a.frames} frames, hearts {a.hearts}")
                else:
                    st["since"] += 1
                if best is None:
                    limit = patience * 2
                elif HEARTS_FREE[0] or best.hearts >= min(c, st["h0"]):
                    limit = max(4, patience - 2)     # unhurt (or hearts are free): little left to find
                elif best.hearts <= max(1.0, 0.35 * c):
                    limit = tries
                else:
                    limit = patience * 2
                if best is not None and st["since"] >= limit:
                    if not st["stop"]:
                        log(f"  (early stop after {st['done']} attempts)")
                    st["stop"] = True

    threads = [threading.Thread(target=work, args=(k,), daemon=True) for k in range(len(scouts))]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    best = st["best"]
    if best is None and fails:
        top = sorted(fails.items(), key=lambda kv: -kv[1])[:4]
        log("  no success; most common: " + " | ".join(f"{n}x {k}" for k, n in top))
    scouts[0].note(f"SEARCH done in {time.time() - t0:.0f}s: " + (f"best {best.frames} frames" if best else "no success"))
    return best


def random_search(emu: BizHawk, state_name: str, policy, success, *, tries: int = 60,''', "parallel_search + value_of")
save("zelda/search.py", t, crlf)

# ------------------------------------------------------------------ runner.py
t, crlf = load("zelda/runner.py")
t = sub(t, "from .search import random_search", "from .search import random_search, parallel_search", "runner import")
t = sub(t, '''        self.scout = BizHawk(log_name=f"{self.name}_scout.log", clean_sram=False)
        self.nav = Navigator(self.main)
        self.snav = Navigator(self.scout)
''', '''        import os
        k = max(1, int(os.environ.get("ZELDA_SCOUTS", "4")))
        self.scouts = [BizHawk(log_name=f"{self.name}_scout{i if i else ''}.log", clean_sram=False)
                       for i in range(k)]
        self.scout = self.scouts[0]
        self.nav = Navigator(self.main)
        self.snavs = [Navigator(e) for e in self.scouts]
        self.snav = self.snavs[0]
''', "several scouts")
t = sub(t, '''        for e in (self.scout, self.main):
            if e is not None:''', '''        for e in list(getattr(self, "scouts", []) or [self.scout]) + [self.main]:
            if e is not None:''', "close all scouts")
t = sub(t, '''        import copy
        blocked0 = copy.deepcopy(self.snav.blocked)

        def reset_beliefs(rec, nav=self.snav):
            nav.blocked = copy.deepcopy(blocked0)

        best = random_search(scout, start, factory(self.snav), success, tries=tries,
                             max_frames=max_frames, label=name, log=self.log, prefer_hearts=True,
                             setup=reset_beliefs)
        self.snav.blocked = copy.deepcopy(blocked0)''', '''        import copy
        from . import search as _search, lookahead as _look
        blocked0 = copy.deepcopy(self.snav.blocked)

        def reset_beliefs(rec, nav=None):
            (nav or self.snav).blocked = copy.deepcopy(blocked0)

        # Per-segment context: is every heart about to be refilled (a boss, the Triforce behind it)?
        free = name in REFILL_SOON
        _search.HEARTS_FREE[0] = free
        _look.CAUTION_OVERRIDE[0] = 0.12 if free else None
        best = parallel_search(self.scouts, self.snavs, start, factory, success, tries=tries,
                               max_frames=max_frames, label=name, log=self.log, setup=reset_beliefs)
        for nav in self.snavs:
            nav.blocked = copy.deepcopy(blocked0)''', "segment(): parallel search + context")
t = sub(t, '''SEG_START: State | None = None
''', '''SEG_START: State | None = None

# Segments whose damage is about to be refilled: each boss (the Triforce piece behind it restores every
# heart) and everything from the Patra under Ganon to the end. The owner: "he can be more aggressive as you
# fill up on life once you beat the boss."
REFILL_SOON = {"manhandla", "aquamentus", "gleeok", "dodongo", "digdogger", "gohma", "l7_aqua", "l8_gleeok",
               "l4_heart", "l5_heart", "l6_heart", "l7_heart", "l8_heart",
               "g9_52_patra", "g9_42", "g9_ganon", "g9_power", "g9_32", "g9_zelda", "g9_credits"}
''', "REFILL_SOON")
save("zelda/runner.py", t, crlf)

# ------------------------------------------------------------------ overworld.py: atomic knowledge files
t, crlf = load("zelda/overworld.py")
t = sub(t, '''    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({c: {"walkable": sorted(v["walkable"]), "solid": sorted(v["solid"]),
                                             "evidence": v["evidence"]} for c, v in self.ctx.items()}, indent=1))
''', '''    def save(self) -> None:
        # Several scouts learn at once now: merge with what is on disk, write to a temp file, swap it in.
        import os
        with _KB_LOCK:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            try:
                disk = json.loads(self.path.read_text())
            except (OSError, ValueError):
                disk = {}
            for c, v in disk.items():
                if c in self.ctx and isinstance(v, dict):
                    mine = self.ctx[c]
                    mine["walkable"] |= {x for x in v.get("walkable", []) if x not in mine["solid"]}
                    mine["solid"] |= {x for x in v.get("solid", []) if x not in mine["walkable"]}
            tmp = self.path.with_suffix(".tmp%d" % os.getpid())
            tmp.write_text(json.dumps({c: {"walkable": sorted(v["walkable"]), "solid": sorted(v["solid"]),
                                           "evidence": v["evidence"]} for c, v in self.ctx.items()}, indent=1))
            os.replace(tmp, self.path)
''', "atomic tiles.json")
t = sub(t, '''class TileKB:
    """Which 8x8 pattern ids Link can stand on, per context. Persisted so learning carries over."""
''', '''import threading as _threading
_KB_LOCK = _threading.Lock()


class TileKB:
    """Which 8x8 pattern ids Link can stand on, per context. Persisted so learning carries over."""
''', "kb lock")
t = sub(t, '''        d[f"L{level}_{room:02x}"] = [br, bc, push]
        self.BLOCKS_PATH.write_text(json.dumps(d, indent=1))''', '''        d[f"L{level}_{room:02x}"] = [br, bc, push]
        import os
        with _KB_LOCK:
            tmp = self.BLOCKS_PATH.with_suffix(".tmp%d" % os.getpid())
            tmp.write_text(json.dumps(d, indent=1))
            os.replace(tmp, self.BLOCKS_PATH)''', "atomic blocks.json")
# pen scale: thread-safe (per call, not a module global)
t = sub(t, '''def enemy_penalty(enemies, x: int, y: int) -> int:''', '''def enemy_penalty(enemies, x: int, y: int, scale: float = 1.0) -> int:''', "penalty scale param")
t = sub(t, '''        return int(pen * AVOID[0])''', '''        return int(pen * scale)''', "penalty uses param")
t = sub(t, '''def plan(cells, kb: TileKB, start: tuple[int, int], goal, optimistic: bool = False,
         blocked: set | None = None, enemies=(), extra: set | None = None, forbid=None,
         cells_ok: set | None = None) -> list[str] | None:''', '''def plan(cells, kb: TileKB, start: tuple[int, int], goal, optimistic: bool = False,
         blocked: set | None = None, enemies=(), extra: set | None = None, forbid=None,
         cells_ok: set | None = None, pen_scale: float = 1.0) -> list[str] | None:''', "plan pen_scale")
t = sub(t, '''            nc = cost + 1 + (enemy_penalty(enemies, *nxt) if enemies else 0)''',
        '''            nc = cost + 1 + (enemy_penalty(enemies, nxt[0], nxt[1], pen_scale) if enemies else 0)''', "plan uses pen_scale")
t = sub(t, '''            AVOID[0] = 1.0 if OLD_AVOIDANCE[0] else (4.0 if s.hearts <= 2.0 else 2.0 if s.hearts <= 3.0 else 1.0)
''', '''            pen_scale = 1.0 if OLD_AVOIDANCE[0] else (4.0 if s.hearts <= 2.0 else 2.0 if s.hearts <= 3.0 else 1.0)
''', "go(): local pen_scale")
t = sub(t, '''            path = plan(cells, self.kb, (s.x, s.y), goal, optimistic, self.blocked.get(key), enemies, extra,
                        cells_ok=cells_ok, forbid=ent_forbid)''', '''            path = plan(cells, self.kb, (s.x, s.y), goal, optimistic, self.blocked.get(key), enemies, extra,
                        cells_ok=cells_ok, forbid=ent_forbid, pen_scale=pen_scale)''', "go(): pass pen_scale")
save("zelda/overworld.py", t, crlf)
print("parallel search installed")
