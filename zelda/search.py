"""Savestate-based search: the primitive behind the optimizer.

From a bookmarked state, run many randomized attempts of a short policy and keep the best one
that meets a success test. Attempts are just input lists, so a winner can be replayed exactly
from the same state, and later spliced into the master power-on log.
"""
from __future__ import annotations

import random
import time
from dataclasses import dataclass, field

from .emulator import BizHawk, State
from .overworld import read_enemies, LinkDied
from .combat import Fighter, REACH, ALIGN, enemy_hp, find_enemy


@dataclass
class Attempt:
    seed: int
    inputs: list = field(default_factory=list)
    frames: int = 0
    success: bool = False
    hearts: float = 0.0
    note: str = ""
    bombs: int = 0
    bonus: float = 0.0          # extra frames-equivalent worth of the end state (staged fights: EXTRA_VALUE)


class OverBudget(BaseException):
    """This attempt cannot beat the best any more. BaseException on purpose: no policy's `except Exception`
    may swallow it, while every `finally` (the emu.step restores) still runs."""


class Recorder:
    """Wraps an emulator so a policy's steps are captured as an input list."""

    def __init__(self, emu: BizHawk):
        self.emu = emu
        self._raw_step = emu.step          # bound now, so patching emu.step later can't recurse
        self.inputs: list = []
        self.cap = None                    # callable -> frame count past which this attempt has already lost

    def step(self, buttons=(), frames: int = 1) -> State:
        if isinstance(buttons, str):
            buttons = tuple(b for b in buttons.split(",") if b)
        if self.cap is not None:
            limit = self.cap()
            if limit is not None and len(self.inputs) + frames > limit:
                raise OverBudget()
        self.inputs.extend([tuple(buttons)] * frames)
        return self._raw_step(buttons, frames)


def noisy_ambush(emu: BizHawk, rec: Recorder, rng: random.Random, max_frames: int) -> str:
    """Ambush fliers with randomized nudges, waits, and swing timing. Returns a short outcome note."""
    fighter = Fighter.__new__(Fighter)
    swing_window = rng.choice([8, 10, 12, 14])
    align = rng.choice([4, 6, 8])
    aggression = rng.random()          # how readily we step toward a nearby flier
    frames = 0
    while frames < max_frames:
        s = emu.state()
        if s.hearts <= 0:
            return "died"
        ens = read_enemies(emu)
        if not ens:
            return "clear"
        target = None
        for e in ens:
            dx, dy = e[2] - s.x, e[3] - s.y
            if abs(dy) <= align and -6 <= abs(dx) - 16 <= swing_window:
                target = "Right" if dx > 0 else "Left"; break
            if abs(dx) <= align and -6 <= abs(dy) - 16 <= swing_window:
                target = "Down" if dy > 0 else "Up"; break
        if target:
            from .lookahead import face
            face(rec.step, target); rec.step("A", 2); rec.step((), rng.choice([9, 11, 13]))
            frames += 14
            continue
        e = min(ens, key=lambda e: abs(e[2] - s.x) + abs(e[3] - s.y))
        dx, dy = e[2] - s.x, e[3] - s.y
        r = rng.random()
        if max(abs(dx), abs(dy)) <= 48 and r < aggression:
            if abs(dy) < abs(dx):
                rec.step("Down" if dy > 0 else "Up", 1) if abs(dy) > align else rec.step(("Right" if dx > 0 else "Left"), 1)
            else:
                rec.step("Right" if dx > 0 else "Left", 1) if abs(dx) > align else rec.step(("Down" if dy > 0 else "Up"), 1)
        elif r < aggression + 0.2:
            rec.step(rng.choice(["Up", "Down", "Left", "Right"]), rng.choice([1, 2, 3]))
        else:
            rec.step((), rng.choice([1, 2, 4]))
        frames += 2
    return "timeout"


def nudge_into_room(emu, step) -> None:
    """If Link is standing in a doorway, walk him into the room before planning anything.

    The planner cannot move him out of a doorway (the only way out is the door tunnel itself),
    and on top of that an old man's text can freeze him for well over a hundred frames. So hold
    the inward direction until he actually moves rather than for a fixed count.
    """
    s = emu.state()
    if not s.level:
        return
    d = ("Right" if s.x <= 16 else "Left" if s.x >= 224 else
         "Up" if s.y >= 205 else "Down" if s.y <= 69 else None)
    if d is None:
        return
    start = (s.x, s.y)
    for _ in range(40):
        s = step(d, 8)
        if (s.x, s.y) != start:
            step(d, 8)
            return


DASH_CROSS = [0.25]           # share of dungeon crossings (with monsters about) tried as a lookahead dash
# Idle frames at the head of every attempt. They were 2 from the first day - 341 segments x 2 = eleven seconds of
# the run standing still for no reason the emulator needs. ZELDA_SETTLE=2 puts them back.
import os as _os
SETTLE = [int(_os.environ.get("ZELDA_SETTLE", "0"))]
FIGHT_PATIENCE = [float(_os.environ.get("ZELDA_FIGHT_PATIENCE", "1.0"))]   # x the long-room patience tiers
_DOOR_SPOT = {"Up": (120, 85), "Down": (120, 189), "Left": (32, 141), "Right": (208, 141)}


def dash_cross(emu, rec, rng, direction: str, budget: int = 700) -> str:
    """Cross a dungeon room THROUGH the monsters. The navigator plans against where they stand now and re-plans
    every two steps, so a room of Gibdos reads as a wall of danger and Link walks the long way round the edge
    (Level 5's 65: 480 frames for a 130-frame walk, and two hearts lost waiting for an opening). plan_reach plays
    every candidate step forward in the emulator, so it sees the real gap between them and takes it, and cuts
    down whatever steps into the lane."""
    from .lookahead import plan_reach, Goal
    tx, ty = _DOOR_SPOT[direction]
    room0 = emu.state().room
    res = plan_reach(emu, rec, Goal(tx, ty, 6), max_frames=budget, rng=rng)
    st = emu.state()
    if res != "arrived" and st.room == room0 and st.mode == 5:
        return "dash: " + res
    for _ in range(200):                      # square up on the doorway, then push through it
        if st.room != room0 or st.mode != 5 or (abs(st.x - tx) <= 2 and abs(st.y - ty) <= 2):
            break
        st = rec.step(("Right" if st.x < tx else "Left") if (abs(st.x - tx) > 2 and direction in ("Up", "Down"))
                      else ("Down" if st.y < ty else "Up") if abs(st.y - ty) > 2
                      else ("Right" if st.x < tx else "Left"), 1)
    for _ in range(400):
        if st.room != room0 and st.mode == 5:
            break
        st = rec.step(direction, 1)
    return "crossed" if (st.room != room0 and st.mode == 5) else "dash: stuck at the door"


def make_cross_policy(nav, direction: str):
    """Policy: leave the room through `direction` using the navigator with randomized pauses."""
    from .overworld import NavError

    def policy(emu, rec, rng, max_frames):
        # Recorder must see every frame: temporarily route the navigator's stepping through it
        orig_step = emu.step
        emu.step = rec.step
        from .overworld import OLD_AVOIDANCE
        nav.jitter = (rng, rng.choice([0.05, 0.12, 0.25] if OLD_AVOIDANCE[0] else [0.0, 0.0, 0.04, 0.10, 0.18]))
        nav.avoid_bias = rng.choice([0.3, 1.0, 1.0, 1.0, 2.5])      # some attempts bold, some careful
        try:
            # The lead-in only has to shift the game's frame-driven randomness, and one frame does
            # that. It used to be 0-40 frames of Link standing still at the start of every crossing.
            rec.step((), rng.randint(0, 40) if OLD_AVOIDANCE[0] else rng.choice([0, 1, 2, 3, 4, 6, 9, 13, 18, 24]))
            # Link often starts standing in the doorway he just walked out of. The planner cannot
            # move him from there (the only step out is through the door tunnel), so walk him a
            # little way into the room first.
            nudge_into_room(emu, rec.step)
            s0 = emu.state()
            if (s0.level and s0.mode == 5 and direction in _DOOR_SPOT and not OLD_AVOIDANCE[0]
                    and rng.random() < DASH_CROSS[0] and nav.threats()):
                emu.step = orig_step               # plan_reach branches on the bare emulator and records itself
                return dash_cross(emu, rec, rng, direction)
            s = nav.exit_screen(direction)
            return "crossed" if s.mode in (5, 9) else "odd"
        except NavError as e:
            return "nav: " + str(e)[:40]
        finally:
            emu.step = orig_step
            nav.jitter = None
            nav.avoid_bias = 1.0
    return policy


# Segments after which every heart is refilled (a boss's Triforce piece), or after which hearts no longer
# matter at all (Ganon onward): there an attempt's health is worth nothing beyond staying alive.
HEARTS_FREE = [False]
# Staged fights: a function(emu) -> frames-equivalent worth of where an attempt ENDS (damage already dealt to
# what is left, how close Link stands to it), so a greedy per-kill search does not pick a fast kill that leaves the
# rest of the room in a bad place.
EXTRA_VALUE = [None]


BOMB_VALUE = [220]             # frames one more bomb in hand is worth to the ranking (a wall bombed saves 500+)
BOMB_CAP = [8]                 # ...up to this many


def _bomb_worth(a) -> float:
    return BOMB_VALUE[0] * min(getattr(a, "bombs", 0) or 0, BOMB_CAP[0])


def value_of(a, containers: float) -> float:
    """Frames-equivalent worth of an attempt: faster is better, and health is worth frames - a lot when Link
    is low, little when he has plenty. (Owner: "be more aggressive"; "our main goal is to win quickly".)"""
    h = a.hearts
    if HEARTS_FREE[0]:
        return -a.frames + (200 if h >= 2 else 0) + _bomb_worth(a) + a.bonus
    v = 600 * min(h, 4) + 300 * max(0.0, min(h, 7) - 4) + 120 * max(0.0, h - 7)
    cliff = min(4.0, max(1.5, 0.5 * containers))
    if h < cliff:
        v -= (cliff - h) * 4000
    return v - a.frames + _bomb_worth(a) + a.bonus


def parallel_search(scouts, navs, state_name: str, factory, success, *, tries: int = 60, max_frames: int = 900,
                    setup=None, log=print, label: str = "", patience: int = 14):
    """random_search across several emulators at once: one thread per scout, attempts handed out by seed.
    Same ranking, same early stop. Emulation releases the GIL (it is socket I/O), so K scouts run K attempts
    in nearly the time of one. The winner is an input list from the shared start state, exactly as before."""
    import threading
    lock = threading.Lock()
    st = {"next": 0, "best": None, "since": 0, "stop": False, "done": 0, "containers": 3.0, "h0": None}
    fails: dict = {}
    t0 = time.time()
    scouts[0].note(f"SEARCH{': ' + label if label else ''}: up to {tries} attempts on {len(scouts)} scouts")

    class _Full:                       # the best any attempt could still do: full health, no frames
        frames = 0
        bonus = 0.0

    def cutoff():
        b = st["best"]
        if b is None:
            return None
        c = st["containers"]
        _Full.hearts = c
        _Full.bombs = min(BOMB_CAP[0], st.get("b0", 0) + 4)     # ...and one drop of bombs it might still pick up
        return int(value_of(_Full, c) - value_of(b, c))

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
            st.setdefault("b0", s_start.bombs)
            rec = Recorder(emu)
            if SETTLE[0]:
                rec.step((), SETTLE[0])
            if setup:
                setup(rec, nav)
            rec.cap = cutoff
            step0 = emu.step
            try:
                outcome = policy(emu, rec, rng, max_frames)
            except OverBudget:
                outcome = "over budget"
                emu.step = step0               # belt and braces: a policy without a finally
            except LinkDied:
                outcome = "died"
            except TimeoutError as e:
                outcome = "timeout: " + str(e)[:40]
            except (OSError, ValueError, KeyError, IndexError) as e:
                outcome = f"error: {type(e).__name__}: {str(e)[:40]}"     # one bad attempt, not a dead scout
            s = emu.state()
            try:
                ok = outcome != "died" and not str(outcome).startswith("error:") and success(emu, s)
            except Exception:
                ok = False
            if outcome == "over budget":
                ok = False
            a = Attempt(1000 + i, rec.inputs, len(rec.inputs), ok, s.hearts, outcome, s.bombs)
            if ok and EXTRA_VALUE[0] is not None:
                try:
                    a.bonus = float(EXTRA_VALUE[0](emu))
                except Exception:
                    a.bonus = 0.0
            if _os.environ.get("ZELDA_SEARCH_DEBUG"):
                log(f"    [attempt {i + 1}] {'ok' if ok else 'NO'} {len(rec.inputs)} frames, hearts {s.hearts}, bombs {s.bombs}: {str(outcome)[:60]}")
            if _os.environ.get("ZELDA_SEARCH_DUMP"):          # every attempt's inputs, for the documentary's search wall
                import json as _json, pathlib as _pl
                d = _pl.Path(_os.environ["ZELDA_SEARCH_DUMP"]); d.mkdir(parents=True, exist_ok=True)
                (d / f"attempt_{i + 1:03d}.json").write_text(_json.dumps({
                    "seed": 1000 + i, "ok": ok, "frames": len(rec.inputs), "hearts": s.hearts, "bombs": s.bombs,
                    "outcome": str(outcome)[:80], "inputs": [",".join(b) for b in rec.inputs]}))
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
                elif HEARTS_FREE[0]:
                    # a boss: attempts differ by a factor of two or more (Gleeok: 964 one run, 2,346 the next
                    # after stopping at six), and with four scouts the extra attempts are cheap
                    limit = patience * 3
                elif best.hearts >= min(c, st["h0"]):
                    limit = patience                 # unhurt: search on a while for a faster line
                elif best.hearts <= max(1.0, 0.35 * c):
                    limit = tries
                else:
                    limit = patience * 2
                if best is not None and best.frames >= 700 and limit < tries:
                    limit = min(tries, int(limit * 1.6))      # long rooms vary most between attempts
                # A fight's attempts are spread wide (the first Darknut room: 642 to 900+ from one bookmark, the
                # best found on try 19 after ten tries that beat nothing) and every try that cannot win is cut off
                # at the best one's length, so looking longer is cheap next to what the long tail is worth.
                if best is not None and best.frames >= 500 and limit < tries:
                    limit = min(tries, max(limit, int(patience * FIGHT_PATIENCE[0] * (3.2 if best.frames >= 900 else 2.5))))
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


def random_search(emu: BizHawk, state_name: str, policy, success, *, tries: int = 60,
                  max_frames: int = 900, setup=None, log=print, label: str = "",
                  prefer_hearts: bool = True, patience: int = 8) -> Attempt | None:
    """Run `policy(emu, rng, ...)` from the savestate up to `tries` times with different seeds.
    `success(emu, state)` decides. Returns the shortest successful Attempt (or None).

    Searching all `tries` every time is a waste: a clean full-health win in 600 frames is not going
    to be beaten by much, and the run still has three dungeons to play. So once there is a
    full-health success, stop after `patience` further attempts fail to improve on it."""
    best = None
    since = 0
    # Why attempts fail. A segment that fails all its tries used to die with nothing but
    # "segment failed" - the whirlwind warp lost a whole run that way before a probe showed it.
    fails: dict[str, int] = {}
    t0 = time.time()
    emu.note(f"SEARCH{': ' + label if label else ''}: up to {tries} randomized attempts from a bookmark, keeping the shortest success")
    for i in range(tries):
        seed = 1000 + i
        rng = random.Random(seed)
        emu.load(state_name)
        rec = Recorder(emu)
        rec.step((), 2)            # settle frames are part of the recorded inputs (else main/scout desync)
        if setup:
            setup(rec)
        try:
            outcome = policy(emu, rec, rng, max_frames)
        except LinkDied:
            outcome = "died"
        except TimeoutError as e:
            # one attempt getting stuck is just a bad attempt, not a broken run
            outcome = "timeout: " + str(e)[:40]
        s = emu.state()
        ok = outcome != "died" and success(emu, s)
        if not ok:
            key = f"{str(outcome)[:50]} @ room {s.room:02X} L{s.level}"
            fails[key] = fails.get(key, 0) + 1
        a = Attempt(seed, rec.inputs, len(rec.inputs), ok, s.hearts, outcome, s.bombs)
        # Health first, but not at any price. Ranking strictly by hearts and only then by length
        # means a 6000-frame attempt beats a 1500-frame one for half a heart, which is exactly the
        # dawdling that looks so bad on screen. Half a heart is worth about 300 frames here.
        def rank(x):
            if not prefer_hearts:
                return -x.frames
            # Half a heart is worth about 300 frames - enough to stop Link dawdling for a drop,
            # but not enough to stop him finishing a segment on two hearts, which is how he ends
            # up walking into the next dungeon nearly dead. Below four hearts the price rises
            # steeply: a quicker attempt never justifies arriving at death's door.
            # A cap on this bonus was tried and REVERTED, 2026-09-16. The idea was that health Link
            # does not need is not worth frames, so the reward stopped at 90% of his containers.
            # What it actually did was make 5.0 and 4.5 hearts score identically, so every segment
            # near full health quietly preferred the faster, weaker finish. Over the forty segments
            # between the White Sword and Level 4 that erosion compounded: the run reached Level 4
            # on 2.5 hearts instead of 3.5, hit room 0x40 on one heart, and then died sixty times
            # running in 0x32. It was worth about 1,100 frames and it cost the whole run.
            r = x.hearts * 600 - x.frames
            if x.hearts < 4:
                r -= (4 - x.hearts) * 4000
            return r
        better = best is None or rank(a) > rank(best)
        if ok and better:
            best = a
            emu.note(f"  attempt {i + 1}: SUCCESS in {a.frames} frames with {a.hearts} hearts (new best)")
            log(f"  attempt {i+1}: success {a.frames} frames, hearts {a.hearts}")
        else:
            since += 1
            if i % 10 == 9:
                emu.note(f"  {i + 1} attempts so far, best {'none' if best is None else str(best.frames) + ' frames'}")
        if ok and better:
            since = 0
        # Stop early once the best attempt stops improving. A full-health win is as good as it
        # needs to get, so give up on beating it quickly; anything less than full gets twice the
        # patience before we accept it. Requiring FULL health here (as this first did) meant a
        # segment that ended half a heart down searched all forty attempts every time, which is
        # where most of an afternoon went.
        # A win that leaves Link nearly dead is not a win worth settling for. Level 4 showed why:
        # room 0x32 stopped after nineteen attempts holding a 1-heart success, and the next room
        # then failed 34 times out of 40 with "gave up reaching the Left door" - at one heart of
        # five the damage-aware planner will not walk past anything, so the run simply wedges. The
        # worse the best attempt's health, the longer we keep looking for a better one.
        if best is None:
            limit = patience * 2
        elif best.hearts >= s.containers:
            limit = patience
        elif best.hearts <= max(1.0, 0.35 * s.containers):
            # Dire: spend the whole budget rather than settle. Level 4's room 0x32 is the case that
            # set this - it stopped at 43 of 60 attempts holding a one-heart win, while the previous
            # run had found a two-heart line in the same room (slower, but it scores better here and
            # it is what let Link survive the rest of the dungeon). A near-dead Link wedges every
            # room after him, so the attempts are worth spending.
            limit = tries
        else:
            limit = patience * 2
        if best is not None and since >= limit:
            emu.note(f"  stopping early: {best.frames} frames at {best.hearts} hearts, "
                     f"{since} attempts since without improving")
            log(f"  (early stop after {i+1} attempts)")
            break
    if best is None and fails:
        top = sorted(fails.items(), key=lambda kv: -kv[1])[:4]
        log("  no success; most common: " + " | ".join(f"{n}x {k}" for k, n in top))
    emu.note(f"SEARCH done in {time.time() - t0:.0f}s: " + (f"best {best.frames} frames" if best else "no success"))
    return best
