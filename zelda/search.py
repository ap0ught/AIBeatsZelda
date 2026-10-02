"""Savestate-based search: the primitive behind the optimizer.

From a bookmarked state, run many randomized attempts of a short policy and keep the best one
that meets a success test. Attempts are just input lists, so a winner can be replayed exactly
from the same state, and later spliced into the master power-on log.
"""
from __future__ import annotations

import os
import random
import time
from dataclasses import dataclass, field

from .emulator import BadReply, BizHawk, State
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
    accepted: str = ""          # why the search stopped on this line (accept-after); "" = it ran its limit


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

    The map is asked before the hold starts, because the one case where this burns its whole
    40 frames is Link in a doorway with a wall on the inward side: he leans on it, moves nothing,
    and the segment pays 40 frames to learn what the tile map already says. A room's tile pattern
    is one 960-byte read, which is cheaper than the frames and is not paid when he can move.
    """
    s = emu.state()
    if not s.level:
        return
    d = ("Right" if s.x <= 16 else "Left" if s.x >= 224 else
         "Up" if s.y >= 205 else "Down" if s.y <= 69 else None)
    if d is None:
        return
    from .overworld import Screen
    dx, dy = {"Right": (1, 0), "Left": (-1, 0), "Up": (0, -1), "Down": (0, 1)}[d]
    if Screen(emu).blocked(s, s.x + dx * 8, s.y + dy * 8) is not None:
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
# Attempts without improvement before the search takes what it has. A NAME rather than a literal,
# because it is the knob a per-segment budget multiplies (runner.MORE_SEARCH) and a literal in a
# signature is not something another module can reach.
PATIENCE = 14
# Attempts without improvement after the search already HAS a line, before it stops and plays that
# line instead of hunting for a faster one. This is the "take what we have" the owner asked for, and
# it is a cap on patience rather than a different stop rule, so a segment whose line keeps improving
# is never cut off - only the fruitless tail is.
#
# Why it exists, measured on 59_fight (Level 3 room $59 -> $69) at 2026-10-01 10:49. The search found
# the room at attempt 3 in 509 frames and again at attempt 4 in 503. The stop rule then said "35 more
# attempts without improvement", because the >= 500-frame tier is `patience * FIGHT_PATIENCE * 2.5`
# and patience is 14. Attempts 5-8 came back at 502-509 frames - none of them beat 503 - and the run
# was STILL on this segment 30 minutes later with an 8-attempt log and two successes in hand, heading
# for roughly two hours of search to shave a percent off a room fight. A segment that is already
# solvable was being treated as a segment that is not.
#
# It is deliberately NOT PATIENCE and not `tries`. Those are about how long a segment may search
# BEFORE it has anything; this is about how long it may keep polishing what it already has, and the
# two answer different questions. 8 is ~30 minutes at the 3.7 minutes an attempt of this segment
# costs, which is one more polish round than the data above justifies skipping. ZELDA_ACCEPT_AFTER=0
# restores the old behaviour exactly, and the owner has that escape hatch on purpose.
ACCEPT_AFTER = [int(_os.environ.get("ZELDA_ACCEPT_AFTER", "8"))]

# How many times one scout's emulator may be replaced during a single search. Bounded because a
# respawn constructs a whole EmuHawk and waits up to 60s for its bridge: if the display has gone,
# four scouts times 60s is four minutes of hanging before anyone notices. Two per scout is enough to
# ride out the ordinary Linux flakiness ("EmuHawk exit code 0" with no traceback) without turning a
# dead display into a slow one.
RESPAWN = [int(_os.environ.get("ZELDA_SCOUT_RESPAWN", "2"))]
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

# Bosses whose pattern runs off the frame counter, so WHICH PHASE an attempt starts in decides the
# fight. Set per-segment by the runner; 0 means "every scout rolls its own entry", which is right for
# an ordinary room and wrong here.
#
# The owner's observation, watching four scouts grind on Gleeok: "I would rather the scouts be more
# experimental. Instead of all 4 of them doing the same thing." They were not doing the same thing
# exactly - gleeok_policy already rolls a 0-90 frame entry per attempt - but they were all sampling
# the SAME 90 frames, and the code's own note records the failure that comes from it:
#
#     four diagnostics with an 8-frame spread came back byte-for-byte identical
#
# A boss keyed to the frame counter has a small number of genuinely distinct fights in it. Four
# independent draws from 0-90 mostly re-roll the same corner of it, because the corners are not
# equally likely to be interesting. So when this is set, scout k enters in its own SLICE of the
# spread and the four of them cover the whole window with no overlap: that is coverage rather than
# sampling, and coverage is what a phase-locked fight needs.
ENTER_SPREAD = [0]


BOMB_VALUE = [220]             # frames one more bomb in hand is worth to the ranking (a wall bombed saves 500+)
BOMB_CAP = [8]                 # ...up to this many

# Frames one heart in hand is worth to the ranking. This was 600, and 600 was wrong by a factor of
# about three, in a way that cost a whole run.
#
# The White Sword screen (0x0A) has a Blue Lynel on it: two hearts a hit, and a sword beam that only
# fires at `hearts >= containers`, i.e. at FULL health. Route 5 arrived there at 3.5/5 and found no
# winning line at all - 0 of 40, measured by testing/probe_white_sword_effort.py. The same approach from
# 4.5/5 succeeds about one time in sixty. The single heart that made the difference was sold by
# segment `c0f_0f`, a plain walk across the overworld, which gave it up to save at most 600 frames.
#
# Ten seconds of game time is a real cost and it is not nothing - but it is a *linear* cost, and the
# thing being bought with it is binary. One heart short of full and the next segment cannot be solved at
# any patience, because the beam that would make it safe is gated on exactly the health just spent.
HEART_VALUE = [1800]            # frames per heart, for the first four
HEART_VALUE_MID = [900]         # ...and for hearts five through seven
HEART_VALUE_TOP = [360]         # ...and above that, where a heart is genuinely just margin


def _bomb_worth(a) -> float:
    return BOMB_VALUE[0] * min(getattr(a, "bombs", 0) or 0, BOMB_CAP[0])


def value_of(a, containers: float) -> float:
    """Frames-equivalent worth of an attempt: faster is better, and health is worth frames - a lot when Link
    is low, little when he has plenty. (Owner: "be more aggressive"; "our main goal is to win quickly".)"""
    h = a.hearts
    if HEARTS_FREE[0]:
        return -a.frames + (200 if h >= 2 else 0) + _bomb_worth(a) + a.bonus
    v = (HEART_VALUE[0] * min(h, 4) + HEART_VALUE_MID[0] * max(0.0, min(h, 7) - 4)
         + HEART_VALUE_TOP[0] * max(0.0, h - 7))
    cliff = min(4.0, max(1.5, 0.5 * containers))
    if h < cliff:
        v -= (cliff - h) * 4000
    return v - a.frames + _bomb_worth(a) + a.bonus


CONVERGE = [True]
CONVERGE_TOL = [20]            # frames; see the note on parallel_search

# "Just get through the game." ZELDA_JUST_GET_THROUGH=1 makes every segment stop at its first
# success, not only the bosses'. Costs about 6% of frames on the archived run and removes almost all
# of the patience searching, which is where the wall clock went. Off by default, so it is one env var
# to undo rather than an edit to find.
JUST_GET_THROUGH = [bool(int(os.environ.get("ZELDA_JUST_GET_THROUGH", "0")))]


def parallel_search(scouts, navs, state_name: str, factory, success, *, tries: int = 60, max_frames: int = 900,
                    setup=None, log=print, label: str = "", patience: int = PATIENCE,
                    seed_base: int = 1000, accept_after: int | None = None, phase_prefix: str = "",
                    respawn=None):
    """random_search across several emulators at once: one thread per scout, attempts handed out by seed.
    Same ranking, same early stop. Emulation releases the GIL (it is socket I/O), so K scouts run K attempts
    in nearly the time of one. The winner is an input list from the shared start state, exactly as before.

    CONVERGE adds a second early stop: if more than half the SCOUTS have each returned a success within
    CONVERGE_TOL frames of the best so far, take it and move on. Counted per scout, not per attempt -
    attempts are handed out round-robin, so one scout can produce three results in a row and three
    attempts agreeing is not evidence of anything. The owner's phrasing was "if over half of the scouts
    report the same time we continue on without doing the rest of the cycle".

    Measured on the archived run's 428 successes, EXACT agreement never happens - not one segment in
    179 had three identical frame counts - so the tolerance is not a nicety, it is the whole rule. What
    the data does show: 41 of the 65 segments with three or more successes have three of them within
    +20 frames of the best. At +5 it is 12 of 65.

    What this costs, stated plainly because the last wall-clock idea here was refuted for exactly this
    reason: patience scaling buys wall time with an unbounded frame loss, and knowledge/rerun_findings
    shows it losing 2,000-5,000 frames. This one is bounded BY CONSTRUCTION - stopping early can only
    forfeit the difference between the best found and whatever a later attempt would have found, and
    the rule only fires once that difference is already under CONVERGE_TOL. So the worst case is
    CONVERGE_TOL frames per segment, and less than that whenever the best arrived first. 20 frames is
    1.1% of the 1,800 a heart is priced at.

    `seed_base` moves the whole attempt sequence. Attempts are `random.Random(seed_base + i)`, so the
    default draws seeds 1000, 1001, ... and a caller retrying a segment that just failed passes 2000,
    3000, ... instead. That is the difference between a retry and a repeat: same policy, same state,
    same budget, a different sample of the plans - which is all a stuck segment can be given from
    outside, and the only thing that changes when nothing about the segment itself has changed.
    """
    import threading
    lock = threading.Lock()
    st = {"next": 0, "best": None, "since": 0, "stop": False, "done": 0, "containers": 3.0, "h0": None,
          "scout_best": {}}         # scout index -> best frames IT has achieved
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

    def phase_now(i: int) -> str:
        """Which of the search's phases this window is in, in the window's own words, numbered.

        Four scout windows showing the same room look identical, and the room is not the interesting
        part: a search that has never found a line and a search that has one and is trying to beat it
        are the same picture and want opposite things from the person watching. The attempt counter
        used to carry that and was removed as clutter; here it rides with the phase, which is what
        makes it mean something - "#7" alone is a number, "POLISH #7" says what that number is FOR.

        The vocabulary is the search's own stop rules, not a mood: why a search stopped is the single
        most useful thing to know about it, and `converged`, `capped` and `searched` are three
        different decisions that all used to print the same "(early stop after N attempts)".
        """
        if st["best"] is None:
            return f"{phase_prefix}BASELINE #{i + 1}"     # nothing found yet: still looking for a line
        if st["stop"]:
            return f"{phase_prefix}{st.get('why', 'DONE')}"   # decided; in-flight attempts land first
        return f"{phase_prefix}POLISH #{i + 1}"         # we have a line and are trying to beat it

    def announce(why: str) -> None:
        """Tell every scout why the search stopped, while they are still stepping.

        A scout's window paints on the next frame it renders, and a search that has just decided to
        stop still has attempts in flight - so this is the one moment a stop reason can actually be
        seen on screen. Sent after the threads join it would be correct in the bridge and invisible.
        """
        for emu in scouts:
            try:
                emu.cmd(f"phase {why}")
            except Exception:
                pass                            # cosmetic; an older bridge must not break a search

    def work(k):
        emu, nav = scouts[k], navs[k]
        policy = factory(nav)

        def lost_channel(why: Exception) -> bool:
            """This scout's emulator can no longer be trusted. True if the worker carries on.

            A closure rather than inline code because there are now two places that can reach it: the
            attempt itself, and the state read after it. `emu` and `nav` and `policy` are rebound
            here, and Python's `nonlocal` reaches the worker's own frame - which is the point, since
            the caller's loop keeps using those names.

            The emulator underneath is gone, so this worker used to stop - which meant a scout that
            died was dead for the REST OF THE SEARCH, and only came back when the whole run process
            restarted. Eight deaths in one session, and the run spent its last hours searching
            three-wide while the log said four scouts. So the worker asks the runner - which owns the
            emulators - to put a fresh one in its slot and carries on. Without a respawn callback, or
            once RESPAWN replacements have been spent, this is the old behaviour: the worker stops,
            and st["dead"] lets the caller see that the search is running short-handed instead of
            quietly searching with fewer quarters than it thinks it has.
            """
            nonlocal emu, nav, policy
            with lock:
                st["dead"] = st.get("dead", 0) + 1
            log(f"  scout {k} lost its emulator ({str(why)[:80]})")
            if respawn is None or st["dead"] > len(scouts) * RESPAWN[0] or not respawn(k):
                log(f"  scout {k} is not coming back this search; it is done")
                return False
            # The runner swapped scouts[k]/navs[k] in place. Re-bind the LOCALS too - they were
            # bound once at the top of this thread - and rebuild the policy, which closed over
            # the old Navigator and would otherwise keep planning against a dead emulator's state.
            emu, nav = scouts[k], navs[k]
            policy = factory(nav)
            with lock:
                st["respawned"] = st.get("respawned", 0) + 1
                alive = len(scouts)
            log(f"  scout {k} replaced with a fresh emulator; the search continues on "
                f"{alive} scout(s), {st['respawned']} replacement(s) so far")
            return True

        def unreadable(e: Exception) -> bool:
            """A reply the parser cannot read. The attempt is lost; the scout is not.

            Not the same thing as `lost_channel`, and deliberately not routed to it. A garbled reply
            MIGHT mean the request/reply stream is out of step - in which case the scout is finished
            - or it might be one truncated line, which 65,149 clean commands say is the commoner case
            (testing/probe_bridge_replies.py). Replacing an emulator costs a process launch and up to
            60s waiting for its bridge, and the measured rate of this is 2% of attempts, so rebuilding
            on every one of them would buy a scout that usually did not need it. It is counted instead
            and reported in the search's summary line, so the rate is visible in an overnight log and
            a rise in it is a fact rather than a rumour.
            """
            with lock:
                st["unreadable"] = st.get("unreadable", 0) + 1
                n = st["unreadable"]
            log(f"  scout {k}: unreadable bridge reply ({str(e)[:70]}); the attempt is lost, "
                f"the scout is not  [{n} so far this search]")
            return True

        while True:
            with lock:
                if st["stop"] or st["next"] >= tries:
                    return
                i = st["next"]
                st["next"] += 1
            rng = random.Random(seed_base + i)
            step0 = emu.step
            # The whole attempt is inside the error handling - loading the state, the settle steps,
            # the policy call - not just the policy call. A bridge that dies during `load` used to
            # kill the worker thread outright, uncaught and uncounted: no "lost its emulator" line,
            # no replacement, one fewer scout and nothing in the log to say why. Same failure as
            # dying mid-policy, so it gets the same handling.
            try:
                s_start = emu.load(state_name)
                st.setdefault("b0", s_start.bombs)
                rec = Recorder(emu)
                # Boss phase coverage: scout k gets slice k of the entry window rather than a free
                # draw from all of it, so K scouts cover K distinct quarters of the cycle with no
                # overlap. Outside a boss this is the old behaviour, one settle value for everybody.
                spread = ENTER_SPREAD[0]
                if spread:
                    lo = spread * (k % max(1, len(scouts))) // max(1, len(scouts))
                    hi = spread * (k % max(1, len(scouts)) + 1) // max(1, len(scouts))
                    rec.step((), lo + rng.randint(0, max(0, hi - lo - 1)))
                elif SETTLE[0]:
                    rec.step((), SETTLE[0])
                if setup:
                    setup(rec, nav)
                rec.cap = cutoff
                # Tell the emulator window which attempt this is, and which of the search's phases it
                # is in, so the window says so rather than only the log. Both cosmetic, both wrapped:
                # an emulator on an older bridge must still be able to search.
                for line in (f"attempt {i + 1}", f"phase {phase_now(i)}"):
                    try:
                        emu.cmd(line)
                    except Exception:
                        pass
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
            except BadReply as e:
                if not unreadable(e):                      # kept separate from RuntimeError below
                    return
                continue
            except RuntimeError as e:
                # The bridge died mid-attempt - "bridge connection lost ... EmuHawk exit code 0" is
                # the common one on Linux, where a scout emulator occasionally just goes. This is the
                # emulator, not the policy, so the attempt is a loss and the thread must live on:
                # letting it out of here killed the whole worker, and a dead worker does not just lose
                # its own share, it takes its slice of the phase window with it (search.ENTER_SPREAD
                # divides 0-90 by the CONFIGURED scout count, so a thread that dies leaves its quarter
                # permanently unsampled and the coverage - the entire point of the split - silently
                # degrades). Three scouts died this way in one afternoon before this was caught by
                # watching the process list rather than the log.
                if not lost_channel(e):
                    return
                continue
            # The state AFTER the attempt, read outside the handling above. A reply the parser cannot
            # read raises here, and this was the last place in the worker where an exception still
            # escaped: the archived four-hour log has one, at exactly this line, with no "lost its
            # emulator" line, no counter and no replacement - the same class of bug one line above,
            # in the one place section 13's widening did not reach. Read it through the same handling,
            # because a garbled reply means the socket is out of step and nothing after it is
            # trustworthy; and note the attempt index is already spent (st["next"] was incremented
            # above), so continuing costs one attempt and not one scout.
            try:
                s = emu.state()
            except (BadReply, OSError, ValueError, KeyError, IndexError) as e:
                if not unreadable(e):
                    return
                continue
            except RuntimeError as e:
                if not lost_channel(e):
                    return
                continue
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
                # Convergence: more than half the SCOUTS inside CONVERGE_TOL of the best. Checked after
                # the best is updated, and against the best's frames rather than the whole ranking -
                # value_of mixes in hearts and bombs, and two lines of equal length are the thing
                # being counted, not two lines of equal worth.
                if ok and CONVERGE[0]:
                    prev = st["scout_best"].get(k)
                    if prev is None or a.frames < prev:
                        st["scout_best"][k] = a.frames
                    # Window on the BEST, not on this attempt: an attempt that is worse than the best
                    # would otherwise widen the window to include results 40 frames adrift.
                    bst = st["best"].frames
                    near = sum(1 for v in st["scout_best"].values() if v <= bst + CONVERGE_TOL[0])
                    # More than half - 3 of 4. I read "if they all finish within the tolerance" as a
                    # unanimous rule and changed it; the owner corrected that back to a majority.
                    if near > len(scouts) / 2 and not st["stop"]:
                        st["stop"] = True
                        st["why"] = "CONVERGED"
                        log(f"  converged: {near} of {len(scouts)} scouts within "
                            f"{CONVERGE_TOL[0]} frames of {bst} - taking it")
                        announce("CONVERGED")
                # Say something about every attempt, not only the successful ones. Eleven minutes of
                # Gleeok search produced 223 bytes of log because failures are silent, which makes a
                # search that is working look exactly like one that is hung - the owner could not tell
                # which was happening. One line per attempt is the difference between watching a fight
                # and watching a machine.
                #
                # The fails counter above already exists and already summarises outcomes; this only
                # prints. A second counter with a different key width would split every failure
                # bucket in two and make that summary worse, which is the thing this is meant to help.
                if not ok:
                    log(f"  attempt {i+1}: {str(outcome)[:52]} ({len(rec.inputs)} frames)")
                if best is None:
                    limit = patience * 2
                elif HEARTS_FREE[0] or JUST_GET_THROUGH[0]:
                    # A boss: the FIRST success is the win. Stop there. With JUST_GET_THROUGH set, every
                    # segment behaves this way.
                    #
                    # This used to be `patience * 3` - keep going, 42 more attempts, hoping for a
                    # faster line. On Gleeok that threw away the best result the project has ever
                    # produced: attempt 43 killed it in 490 frames, 319 faster than anything in
                    # history, and the search then spent hours looking for something better than
                    # "the boss is dead". The owner asked the question that exposed it: "why can't
                    # we just take the first time we kill the boss?" Because for a boss the success
                    # test is the kill - $034D, the room-finished flag - so there is nothing above a
                    # success to find. A room is different: clearing it faster is a real second goal,
                    # and that is what patience is for.
                    #
                    # The owner's new theory - "just get through the game" - is the generalisation of
                    # that question, and the archived log says it is cheap. Taking each segment's
                    # first success rather than its best, over 192 comparable segments: 74,325 frames
                    # against the 70,099 actually kept. 4,226 frames, +6%, for stopping the patience
                    # search almost everywhere. knowledge/rerun_findings.json already said the same
                    # thing segment by segment - farm43 and farm53 ran all 40 attempts for a gain of
                    # exactly 0 frames.
                    #
                    # Indicative, not exact: attempt seeds are 1000 + i, so the sequence a segment sees
                    # is not quite the one it saw while searching hard. The shape is not in doubt.
                    st["stop"] = True
                    log("  first success in hand - taking it ("
                        + ("a boss success IS the win; see HEARTS_FREE)" if HEARTS_FREE[0]
                           else "JUST_GET_THROUGH: not searching for a better line)"))
                    return
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
                # ...and then the cap. `limit` above can reach 35 non-improving attempts on a room this
                # long (patience 14 x the >= 500 tier's 2.5), which is an hour of search spent on a
                # segment that was already solved. ACCEPT_AFTER bounds the polishing tail: it counts
                # attempts since the best last IMPROVED, so a segment still getting better lines is
                # never cut off, and a segment whose attempts have all come back equal stops at 8.
                # 59_fight on 2026-10-01 is the case this was written for - see ACCEPT_AFTER's note.
                cap = ACCEPT_AFTER[0] if accept_after is None else accept_after
                if best is not None and cap > 0 and st["since"] >= cap and not st["stop"]:
                    st["stop"] = True
                    st["why"] = "CAPPED"
                    st["accepted"] = (f"took the {best.frames}-frame line after {st['done']} attempts "
                                      f"({st['since']} without improvement)")
                    log(f"  (accept-after {cap}: {st['accepted']} - flagged for a later pass)")
                    announce("CAPPED")
                if best is not None and st["since"] >= limit:
                    if not st["stop"]:
                        st["why"] = "SEARCHED"
                        log(f"  (early stop after {st['done']} attempts)")
                        announce("SEARCHED")
                    st["stop"] = True

    threads = [threading.Thread(target=work, args=(k,), daemon=True) for k in range(len(scouts))]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    # Tell every scout the search is over. Measured, with a real state in a parked window: setting the
    # label does NOT repaint it, and neither does `step 0` - a window composites the overlay only when
    # it renders an actual frame, and a scout between searches renders nothing. So this is correct in
    # the bridge and usually invisible on screen; the window keeps showing the last phase it drew, and
    # the log is where "the search is over" is actually readable. Kept because it costs one line each
    # and any future step of a parked scout paints it.
    announce("DONE")
    best = st["best"]
    if best is not None and st.get("accepted"):
        # Hand the reason to the runner, which is what writes the flagged-for-improvement entry: the
        # search knows WHY it stopped early, and only the runner knows the run it belongs to.
        best.accepted = st["accepted"]
    dead = st.get("dead", 0)
    if dead:
        # Say so on the same line as the result, because this is the failure that does not announce
        # itself: a search that lost two of four workers still reports a time and a result, and the
        # coverage it actually had is smaller than the one it planned for. Deaths and replacements
        # are reported apart, because "a scout died" and "a scout died and was replaced" are
        # different things to read in an overnight log.
        back = st.get("respawned", 0)
        log(f"  {dead} scout emulator(s) died mid-search, {back} replaced; "
            f"the search ran on {len(scouts) - (dead - back)} of {len(scouts)}"
            + ("" if back == dead else " for at least part of it")
            + ", so the phase window was covered unevenly")
    # Replies the parser could not read. Its own line because it is the failure that does not announce
    # itself anywhere else: the attempts it cost are counted as ordinary losses and the emulators
    # survive, so a search can sit at 98% of its attempts for hours with nothing in the log but this.
    garbled = st.get("unreadable", 0)
    if garbled:
        log(f"  {garbled} attempt(s) lost to a bridge reply that could not be read "
            f"({garbled / max(1, st['done']):.1%} of them); the emulators were kept")
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
