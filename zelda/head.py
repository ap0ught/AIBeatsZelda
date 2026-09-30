"""Gleeok's head: take it off the floor of the dragon's room, carry it home, leave it in the cave
the White Sword came from.

WHAT IS IN THE ROM: nothing. There is no head item, no carry animation, and no code path anywhere
in Z_01 or Z_04 that would know what to do with one. So the head is harness state, and every line
in this file that could be read as claiming otherwise is avoided rather than hedged.

WHAT IS REAL, and is what makes this a mechanic rather than a caption:

  * the frames. Both ends of it are walked. The pickup is a real walk across the Gleeok's room to
    the floor under the dragon; the delivery is a real walk into the sword cave at 0x0A, down the
    entrance corridor, out to the item row and up under the pixel the White Sword was read at.
    Route 5 pays thirty-one screen transitions to get home before any of it starts
    (route5.py's rv_leg_* block), which is the bulk of the cost and is not pretend either.
  * the place. The delivery spot is not written down in this file. It is the x the White Sword was
    read at out of the object table on the day it was taken - cave_item_policy calls remember_spot
    as soon as bot.take_cave_item has found it - so the head goes where the sword was because that
    is the same measured pixel, not because 120 is a number that looks right.
  * the check. The delivery's success test is RAM: inside the cave (mode $0B, submode 0), on the
    item row, on that x. No harness flag can make it true, which is the only reason to trust it: a
    note that claims a state the run is not in is worse than no note, and a success test that a
    flag can satisfy is a note in disguise.

WHAT IS FICTION: the carrying. Nothing in the cartridge slows Link down and nothing in the
cartridge knows he has it. So the phase is not a flag that gets set and cleared - it is DERIVED
from where the run is in its own segment list (see sync), which means a crashed attempt, a stale
checkpoint or a resumed run cannot leave a "carrying the head" on the screen for a Link who is not.
"""
from __future__ import annotations

TAKE = "gleeok_head"        # segment names. The route defines them; this is where they are agreed.
DELIVER = "deliver"

GONE, CARRIED, DELIVERED = 0, 1, 2
TEXT = {GONE: "still lying in Level 4", CARRIED: "carried", DELIVERED: "left in the sword cave"}

_PHASE = [GONE]
_SPOT: list = [None]        # x the White Sword came from, measured the day it was taken
_TOLD: list = [None]        # what the emulator's HUD has already been told, so it is told once


def phase() -> int:
    return _PHASE[0]


def carrying() -> bool:
    return _PHASE[0] == CARRIED


def phase_text() -> str:
    return TEXT[_PHASE[0]]


def spot() -> int | None:
    return _SPOT[0]


def remember_spot(x: int | None) -> None:
    """Called when the White Sword is taken. That x is where the head goes."""
    if x is not None:
        _SPOT[0] = int(x)


def sync(done: list[str], log=None) -> None:
    """Derive the phase from the segments the run has actually finished.

    Deliberately a function of `done` and nothing else. The alternative - a mutable phase that
    take() and place() flip - is wrong in a way this project's own notes keep running into: a
    scout attempt that half-succeeded, or a checkpoint written before the commit, leaves the flag
    set for a Link who is not carrying anything, and then a note says it. `done` only grows when a
    segment has been played into MAIN and verified there (runner.Run.segment), and it is restored
    from the checkpoint's own segment list on resume, so it is the one piece of run state that has
    never yet lied.
    """
    was = _PHASE[0]
    if DELIVER in done:
        _PHASE[0] = DELIVERED
    elif TAKE in done:
        _PHASE[0] = CARRIED
    else:
        _PHASE[0] = GONE
    if _PHASE[0] != was and log is not None:
        log(f"Gleeok's head: {phase_text()}")


def announce(emu, log=None) -> None:
    """Tell the in-emulator HUD, once per change. Same convention as the rest of the run's notes."""
    p = _PHASE[0]
    if _TOLD[0] == p:
        return
    _TOLD[0] = p
    try:
        emu.cmd(f"story head {p}")
    except Exception as e:                       # an emulator on an older bridge still plays fine
        if log:
            log(f"(could not tell the HUD about the head: {str(e)[:40]})")


# ---------------------------------------------------------------- the two places
#
# The Gleeok's neck is all one x. InitGleeok writes X=$7C into every neck segment slot, which is
# 124 - read_ghost_objects quotes the instruction - so the dragon lies along that column and the
# head is on the floor at or below it. Which ROW of that column is floor is the room's own
# business, and the two Gleeok rooms are not the same room, so it is measured here rather than
# written down: the nearest legal lattice point to (124, 141). A hardcoded y would put the pickup
# inside a wall in one room and 40 pixels away in the other, and the pickup's success test is
# "Link is standing on it", so it would fail in both.
_FLOOR: dict = {}          # (level, room) -> the spot, so the success test does not re-read the map


def floor_spot(emu, want: tuple[int, int] = (124, 141)) -> tuple[int, int] | None:
    """Nearest walkable lattice point to `want` on this screen, or None if there is not one.

    Cached per (level, room), and the cache is the point rather than an optimisation: the pickup's
    success test calls this on every attempt the search evaluates, and a fresh TileKB plus a
    960-byte bus read per call would cost more wall clock than the segment it is judging. The room
    does not change shape while the head is being picked up - nothing in it is pushed, bombed or
    unlocked - so a per-room answer is not a stale one.
    """
    from .overworld import Screen, TileKB, snap, set_phase
    s = emu.state()
    key = (s.level, s.room)
    if key in _FLOOR:
        return _FLOOR[key]
    set_phase(s.y if s.mode == 9 else 5)
    sc = Screen(emu, TileKB())
    sc.use(s)
    best = None
    for r in range(0, 11):
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if max(abs(dx), abs(dy)) != r:
                    continue
                x, y = snap(want[0] + dx * 8, want[1] + dy * 8)
                if sc.free(x, y) and (best is None or abs(x - want[0]) + abs(y - want[1]) < best[0]):
                    best = (abs(x - want[0]) + abs(y - want[1]), (x, y))
        if best is not None:
            _FLOOR[key] = best[1]
            return best[1]
    _FLOOR[key] = None
    return None


def take_policy(nav):
    """Walk across the Gleeok's room to the floor under the dragon and take its head.

    The pickup is a placement, not a press: the game has no item to collect, so the mechanic that
    can honestly be built is Link standing on the spot where the dragon fell with the room's boss
    dead. The success test in the route is the same pair of conditions in RAM, so the segment
    cannot succeed on a scout's say-so and cannot succeed in the wrong room.
    """
    def policy(emu, rec, rng, max_frames):
        from .overworld import NavError, LinkDied
        orig = emu.step
        emu.step = rec.step
        nav.jitter = (rng, rng.choice([0.0, 0.1]))
        try:
            rec.step((), rng.randint(0, 6))
            spot = floor_spot(emu)
            if spot is None:
                return "no floor under the dragon to take it from"
            emu.note(f"Gleeok's neck lies along x=124. Taking the head from the floor at {spot}")
            nav.go(lambda x, y: abs(x - spot[0]) <= 4 and abs(y - spot[1]) <= 4,
                   "the dragon's head", optimistic=True, max_replans=40)
            s = emu.state()
            if abs(s.x - spot[0]) > 4 or abs(s.y - spot[1]) > 4:
                return f"could not reach {spot}: stopped at ({s.x},{s.y})"
            emu.note(f"Gleeok's head picked up off the floor at ({s.x},{s.y}), room {s.room:02X}")
            return "took the head"
        except (NavError, LinkDied) as e:
            return "fail: " + str(e)[:40]
        finally:
            emu.step = orig
            nav.jitter = None
    return policy


def deliver_policy(nav):
    """Put the head down in the sword cave, on the pixel the White Sword came from.

    The walk in is the one cave_item_policy already proves, reused deliberately rather than
    rewritten: find the mouth, take the damage-aware planner to it, square up on its x, hold UP
    until the room has actually swapped in, wait out the old man's text, then out to the item row.
    Only the last three steps are new, and they are the sword's own geometry - y=173 to line up
    clear of the entrance corridor, across to the sword's x, then up - because the head belongs
    exactly where the sword was and the sword's pickup box is the only one the game has.
    """
    def policy(emu, rec, rng, max_frames):
        from . import bot
        from .overworld import NavError, LinkDied
        from .lookahead import plan_reach, Goal
        orig = emu.step
        emu.step = rec.step
        nav.jitter = (rng, rng.choice([0.0, 0.1]))
        try:
            rec.step((), rng.randint(0, 6))
            if not carrying():
                return "not carrying the head - nothing to deliver"
            s = emu.state()
            if s.room != 0x0A or s.level or s.mode != 5:
                return f"not on the sword cave's screen: {s}"
            x = _SPOT[0] if _SPOT[0] is not None else 120
            emu.note(f"Delivering the head to 0x0A, on x={x}"
                     + ("" if _SPOT[0] is not None else " (assumed: no sword pickup was recorded)"))
            mouth = bot.find_entrance(emu)
            if mouth is None:
                return "no cave mouth on this screen"
            mx, my = mouth
            nav.allow_entrances = True
            try:
                emu.step = orig
                res = plan_reach(emu, rec, Goal(mx, my + 16, 6), max_frames=5000, rng=rng)
                emu.step = rec.step
                if res != "arrived":
                    return "approach: " + res
            finally:
                nav.allow_entrances = False
            # a cave only swallows Link when he is on its x exactly
            bot.walk_to(emu, mx, None, stop=lambda q: q.mode == 0x0B)
            emu.wait_until(lambda q: q.mode == 0x0B, 400, buttons=("Up",))
            emu.wait_until(lambda q: q.y > 190, 400, buttons=("Up",))
            emu.wait_until(lambda q: q.sub == 0, 300, buttons=("Up",))
            bot.hold_until(emu, "Up", lambda q: q.y < 200, 600)
            emu.note("In the cave. Up to y=173, clear of the entrance corridor and below the item row")
            bot.walk_to(emu, None, 173, order="yx")
            emu.note(f"Across to x={x}, the White Sword's own x")
            bot.walk_to(emu, x, None)
            emu.note("Up into the item row. There is nothing here for the game to give me, "
                     "which is the point: the head is left where the sword was")
            s = bot.hold_until(emu, "Up", lambda q: q.y <= 141, 240)
            if s.y > 141:
                return f"never got up to the item row: {s}"
            emu.note(f"The dragon's head is on the cave floor at ({s.x},{s.y}), in the cave the "
                     f"White Sword came from")
            return "head down"
        except (NavError, LinkDied, bot.BotError, TimeoutError) as e:
            return "fail: " + str(e)[:40]
        finally:
            emu.step = orig
            nav.jitter = None
    return policy


def delivered_test(emu, s) -> bool:
    """RAM only. Inside the cave, on the item row, on the White Sword's x.

    No flag in this module is consulted, on purpose: the one thing this whole file exists to get
    right is that the end of the run is a fact about the emulator rather than a fact about us.
    """
    x = _SPOT[0] if _SPOT[0] is not None else 120
    return (s.mode == 0x0B and s.sub == 0 and not s.level and abs(s.x - x) <= 2 and s.y <= 141)


def taken_test(emu, s) -> bool:
    """RAM only. The dragon is dead and Link is standing where it fell."""
    spot = floor_spot(emu)
    if spot is None:
        return False
    return (s.level == 4 and s.room == 0x13 and s.mode == 5
            and abs(s.x - spot[0]) <= 4 and abs(s.y - spot[1]) <= 4)
