"""Cellars (game mode 9) are side-view corridors: floors ('24'), ladders ('6F'), bricks ('FA').
Link moves only along floors and up/down ladders, so a scripted, feedback-driven traversal beats the
room planner. Level 3's raft cellar (room 0F): enter at the top of the left ladder (x=48), floor at
the bottom, right ladder at x=176 up to the upper corridor, raft at (128,144)."""
from __future__ import annotations

from .emulator import BizHawk, State
from .overworld import read_room_item, LinkDied, read_enemies


def beam_ahead(emu: BizHawk, d: str) -> bool:
    """At full hearts, fire a sword beam at an enemy lined up ahead in direction d. Returns True if fired."""
    s = emu.state()
    if s.hearts < s.containers:
        return False
    for e in read_enemies(emu):
        dx, dy = e[2] - s.x, e[3] - s.y
        aligned = (d in ("Left", "Right") and abs(dy) <= 6 and 24 <= abs(dx) <= 160 and (dx > 0) == (d == "Right")) or                   (d in ("Up", "Down") and abs(dx) <= 6 and 24 <= abs(dy) <= 160 and (dy > 0) == (d == "Down"))
        if aligned:
            from .lookahead import face
            face(emu.step, d); emu.step("A", 2); emu.step((), 12)
            return True
    return False


def hold_until_stall(emu: BizHawk, d: str, max_frames: int = 300, stop=None) -> State:
    last, stall = None, 0
    s = emu.state()
    for _ in range(max_frames):
        s = emu.step(d, 1)
        if s.hearts <= 0:
            raise LinkDied("died in cellar")
        if stop and stop(s):
            return s
        if s.mode not in (5, 9):
            return s
        stall = stall + 1 if (s.x, s.y) == last else 0
        last = (s.x, s.y)
        if stall >= 6:
            return s
    return s


def hold_to_x(emu: BizHawk, tx: int, max_frames: int = 400, stop=None) -> State:
    s = emu.state()
    for i in range(max_frames):
        if s.x == tx or (stop and stop(s)) or s.mode not in (5, 9):
            return s
        d = "Right" if s.x < tx else "Left"
        if i % 6 == 0 and beam_ahead(emu, d):
            s = emu.state(); continue
        s = emu.step(d, 1)
        if s.hearts <= 0:
            raise LinkDied("died in cellar")
    return s


def take_raft_cellar(emu: BizHawk, log=None) -> bool:
    """From the cellar entry (top of the left ladder) fetch the raft and climb back out to room 69."""
    for _ in range(60):                       # let the cellar finish loading
        if read_room_item(emu) is not None and emu.state().sub >= 9:
            break
        emu.step((), 4)
    emu.note("Cellar: down the left ladder, right along the floor, up the right ladder, left to the raft")
    s = hold_until_stall(emu, "Down")
    floor_y = s.y
    s = hold_to_x(emu, 176)
    s = hold_until_stall(emu, "Up")
    s = hold_to_x(emu, 128, stop=lambda s: emu.byte(0x660) == 1)
    for _ in range(3):
        if emu.byte(0x660):
            break
        s = hold_to_x(emu, 120); s = hold_to_x(emu, 136)
    if not emu.byte(0x660):
        emu.note("Raft not taken")
        return False
    emu.note("RAFT TAKEN. Climbing back out")
    s = emu.wait(20)                          # item-get pose
    s = hold_to_x(emu, 176)
    s = hold_until_stall(emu, "Down")
    s = hold_to_x(emu, 48)
    s = hold_until_stall(emu, "Up", max_frames=400, stop=lambda s: s.mode not in (5, 9))
    s = emu.wait_until(lambda s: s.mode in (5, 9), 600)
    s = emu.wait(2)
    emu.note(f"Back upstairs: room {s.room:02X}, level {s.level}, hearts {s.hearts}")
    return emu.byte(flag_addr) == 1


def take_cellar_item_la(emu: BizHawk, rec, flag_addr: int, rng=None, log=None) -> bool:
    """The standard item cellar (same layout for the L3 raft and the L4 ladder): enter at the top
    of the left ladder, down, right along the lower floor, up the right ladder, left to the item on
    the upper floor, then back the same way and up the entry ladder. Each leg is driven by the
    lookahead planner so the Keese get dodged or cut down instead of walked into."""
    from .lookahead import plan_reach, Goal
    for _ in range(60):
        if read_room_item(emu) is not None and emu.state().sub >= 9:
            break
        rec.step((), 4)
    cellar = emu.state().room
    # Compare the item flag with its value on ARRIVAL, not with 1. The raft, ladder, candle and
    # recorder all go 0 -> 1, but the SILVER ARROW upgrades the arrows byte 1 -> 2: "== 1" was already
    # true when Link walked in, so the item leg "arrived" at once and he climbed out without it.
    before = emu.byte(flag_addr)

    def taken():
        return emu.byte(flag_addr) != before

    emu.note("Cellar: down the left ladder, along the floor, up the right ladder, take the item, and back")

    def leg(goal, exit_ok=False, frames=1200):
        return plan_reach(emu, rec, goal, max_frames=frames, rng=rng, exit_ok=exit_ok)

    def square_up(x):
        # A ladder only takes Link when he is exactly on its column. A goal tolerance of 4 px left him
        # at x=168..180 under the ladder at 176, holding Up for nothing: 33 of 40 attempts in the Silver
        # Arrow cellar. Step through the recorder, so the main emulator replays the same frames.
        for _ in range(40):
            s = emu.state()
            if s.x == x:
                return True
            rec.step("Right" if s.x < x else "Left", 1)
        return emu.state().x == x

    def climb(x, y_goal, direction):
        # Ladders: climbing a lined-up ladder is deterministic, so do it directly. The lookahead kept
        # choosing to shuffle sideways at the foot of the Silver Arrow cellar's right ladder instead of
        # holding Up - Link sat at (176,189), exactly on the column, then drifted to 168 or 180 and
        # timed out (33 of 40 attempts). Try the column and the pixels either side, holding the
        # direction for as long as it actually moves him.
        for dx in (0, -1, 1, -2, 2, -4, 4):
            square_up(x + dx)
            last_y, stuck = emu.state().y, 0
            for _ in range(240):
                s = rec.step(direction, 1)
                if (direction == "Up" and s.y <= y_goal) or (direction == "Down" and s.y >= y_goal):
                    return True
                if s.room != cellar or s.mode != 9:
                    return True                     # climbed out of the cellar altogether
                stuck = stuck + 1 if s.y == last_y else 0
                last_y = s.y
                if stuck >= 12:
                    break
        return False

    if leg(Goal(48, 186, 6)) != "arrived": return False
    if leg(Goal(176, 186, 4)) != "arrived": return False
    if not climb(176, 141, "Up"): return False

    class ItemGoal:
        target = (128, 141)
        def __call__(self, x, y): return taken()
    if leg(ItemGoal(), frames=900) != "arrived" and not taken():
        emu.note("Item not taken"); return False
    emu.note("ITEM TAKEN. Climbing back out")
    rec.step((), 20)
    if leg(Goal(176, 141, 4)) != "arrived": return False
    if not climb(176, 186, "Down"): return False
    if leg(Goal(48, 186, 4)) != "arrived": return False
    climb(48, 61, "Up")
    s = emu.state()
    for _ in range(900):                       # through the recorder, so the transition is part of the log
        # Wait until Link is really back upstairs. This used to test room != 0x0F - Level 3's raft
        # cellar - so in any other cellar it stopped waiting while he was still on the ladder.
        if s.room != cellar and s.mode == 5:
            break
        s = rec.step((), 1)
    rec.step((), 2)
    emu.note(f"Back upstairs: room {s.room:02X}, hearts {s.hearts}")
    return taken()


def take_raft_cellar_la(emu: BizHawk, rec, rng=None, log=None) -> bool:
    """Level 3's raft cellar."""
    return take_cellar_item_la(emu, rec, 0x660, rng=rng, log=log)


def walk_passage(emu, step, log=print) -> bool:
    """Some staircases are passages, not item rooms: two corridors joined along the bottom, with
    stairs up at each end. Walk down, across to the far corridor, and up out of it."""
    from . import bot
    # Two corridors, one at each end. Walk to whichever one Link did NOT come down, or he just
    # climbs straight back out of the staircase he arrived by.
    here = emu.state().x
    far = 48 if here > 120 else 192
    emu.note(f"This staircase is a passage, not an item room: crossing to the corridor at x={far}")
    bot.walk_to(emu, None, 189, order="yx", max_frames=400)
    bot.walk_to(emu, far, None, max_frames=500)
    for _ in range(40):
        s = step("Up", 8)
        if s.mode != 9:
            return True
    return emu.state().mode != 9
