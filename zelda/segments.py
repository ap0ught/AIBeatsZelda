"""Segment search: cross or clear one room many times from a bookmark, keep the best, chain on.

Objective order: survive with the most hearts, then the fewest frames. Each winner is an input
list replayable from its start state, and the end state is bookmarked for the next segment.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from .emulator import BizHawk, LOGS_DIR
from .overworld import Navigator, NavError, LinkDied, read_enemies, read_room_item
from .combat import Fighter
from .search import random_search, make_cross_policy, Recorder

SEG_DIR = LOGS_DIR / "segments"


def make_clear_grab_policy(nav: Navigator, then_exit: str | None = None, lookahead: bool = True):
    """Clear the room, then take whatever it leaves behind (many rooms only reveal their key once
    everything is dead), then optionally leave."""
    from .lookahead import plan_fight

    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        emu.step = rec.step
        f = Fighter(nav)
        f.jitter = (rng, rng.choice([0.05, 0.15]))
        nav.jitter = (rng, rng.choice([0.05, 0.15]))
        try:
            rec.step((), rng.randint(0, 8))
            from .search import nudge_into_room
            nudge_into_room(emu, rec.step)
            if lookahead:
                emu.step = orig
                res = plan_fight(emu, rec, max_frames=2500, rng=rng, log=True)
                emu.step = rec.step
                if res != "clear":
                    return res
            elif not f.clear_room():
                return "not cleared"
            for _ in range(14):                      # the reward appears a few frames later
                if read_room_item(emu) is not None:
                    break
                rec.step((), 8)
            if read_room_item(emu) is not None:
                f.grab_key_by_dodging()
            if then_exit:
                s = nav.exit_screen(then_exit)
                return "done" if s.mode in (5, 9) else "odd"
            return "done"
        except NavError as e:
            return "nav: " + str(e)[:40]
        finally:
            emu.step = orig
            f.jitter = None
            nav.jitter = None
    return policy


def make_cross_at_policy(nav: Navigator, direction: str, at: int | None = None, stage=None):
    """Cross the screen, optionally staging at a spot first and leaving at a fixed column/row.
    Needed where the next screen is split by water and only one side is any use."""
    def policy(emu, rec, rng, max_frames):
        orig_step = emu.step
        emu.step = rec.step
        from .overworld import OLD_AVOIDANCE
        nav.jitter = (rng, rng.choice([0.05, 0.12, 0.25] if OLD_AVOIDANCE[0] else [0.0, 0.03, 0.08]))
        try:
            rec.step((), rng.randint(0, 40) if OLD_AVOIDANCE[0] else rng.randint(0, 6))
            if stage is not None:
                nav.go(lambda x, y: x == stage[0] and y == stage[1], f"the staging spot {stage}", max_replans=80)
            s = nav.exit_screen(direction, at=at)
            return "crossed" if s.mode in (5, 9) else "odd"
        except NavError as e:
            return "nav: " + str(e)[:40]
        finally:
            emu.step = orig_step
            nav.jitter = None
    return policy


def make_clear_policy(nav: Navigator, then_exit: str | None = None):
    """Policy: kill everything (collecting drops), optionally then leave through `then_exit`."""
    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        emu.step = rec.step
        f = Fighter(nav)
        f.jitter = (rng, rng.choice([0.05, 0.15, 0.3]))
        nav.jitter = (rng, rng.choice([0.05, 0.15]))
        try:
            rec.step((), rng.randint(0, 30))
            if not f.clear_room():
                return "not cleared"
            if then_exit:
                s = nav.exit_screen(then_exit)
                return "cleared+left" if s.mode in (5, 9) else "odd"
            return "cleared"
        except NavError as e:
            return "nav: " + str(e)[:40]
        finally:
            emu.step = orig
            f.jitter = None
            nav.jitter = None
    return policy


def make_grab_policy(nav: Navigator, then_exit: str | None = None):
    """Policy: take the room's floor item by dodging, optionally then leave."""
    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        emu.step = rec.step
        nav.jitter = (rng, rng.choice([0.05, 0.15, 0.3]))
        try:
            rec.step((), rng.randint(0, 30))
            # Step clear of the doorway first. make_clear_grab_policy has always done this; this one
            # did not, and a segment that starts with Link standing in a door gives the planner
            # nothing to path from - room 0x66 in Level 5 failed all 50 attempts with the key lying
            # on the floor in front of him.
            from .search import nudge_into_room
            nudge_into_room(emu, rec.step)
            for _ in range(12):                      # after-clear items appear a few frames later
                if read_room_item(emu) is not None:
                    break
                rec.step((), 8)
            Fighter(nav).grab_key_by_dodging()
            if read_room_item(emu) is not None:
                # Still there after standing on it: something is CARRYING it (a Stalfos holds a key in
                # Level 1 - the "item" moves about with it). Kill the carrier and take what it drops. The old
                # navigator got this by accident: it waited on the Stalfos in its way and then killed it.
                from .lookahead import plan_fight

                def carrier(e):
                    it = read_room_item(e)
                    if it is None:
                        return []
                    near = [q for q in read_enemies(e) if q[1] < 0x40 and max(abs(q[2] - it[1]), abs(q[3] - it[2])) <= 12]
                    return near[:1]
                if carrier(emu):
                    emu.step = orig
                    plan_fight(emu, rec, max_frames=1500, rng=rng, targets=carrier,
                               done=lambda e: not carrier(e), log=True)
                    emu.step = rec.step
                    for _ in range(10):
                        if read_room_item(emu) is not None:
                            break
                        rec.step((), 4)
                    Fighter(nav).grab_key_by_dodging()
            if read_room_item(emu) is not None:
                return "item not taken"
            if then_exit:
                s = nav.exit_screen(then_exit)
                return "grabbed+left" if s.mode in (5, 9) else "odd"
            return "grabbed"
        except NavError as e:
            return "nav: " + str(e)[:40]
        finally:
            emu.step = orig
            nav.jitter = None
    return policy


def make_lafight_policy(nav, then_exit=None, types=None):
    """Policy: clear the room with lookahead (sword), optionally then leave."""
    from .lookahead import plan_fight
    def policy(emu, rec, rng, max_frames):
        orig = emu.step; emu.step = rec.step
        try:
            rec.step((), rng.randint(0, 8))
            from .search import nudge_into_room
            nudge_into_room(emu, rec.step)
            emu.step = orig                      # lookahead branches must not be recorded
            res = plan_fight(emu, rec, max_frames=max_frames, rng=rng, types=types, log=True)
            if res != "clear":
                return res
            emu.step = rec.step
            Fighter(nav).collect_drop()
            if then_exit:
                s = nav.exit_screen(then_exit)
                return "cleared+left" if s.mode in (5, 9) else "odd"
            return "cleared"
        except NavError as e:
            return "nav: " + str(e)[:40]
        finally:
            emu.step = orig
    return policy


def make_lareach_policy(nav, goal, then_exit=None, exit_ok=False):
    """Policy: reach goal(x, y) with lookahead (dash through enemies), optionally then leave."""
    from .lookahead import plan_reach
    def policy(emu, rec, rng, max_frames):
        orig = emu.step; emu.step = rec.step
        try:
            rec.step((), rng.randint(0, 8))
            from .search import nudge_into_room
            nudge_into_room(emu, rec.step)
            emu.step = orig
            res = plan_reach(emu, rec, goal, max_frames=max_frames, rng=rng, exit_ok=exit_ok)
            if res != "arrived":
                return res
            emu.step = rec.step
            t = getattr(goal, "target", None)
            if exit_ok and t is not None and emu.state().mode == 5:
                # stairs/doors trigger only with Link's box fully inside the tile: nudge to the exact spot
                s = emu.state()
                for _ in range(40):
                    if s.mode not in (5, 9) or (s.x == t[0] and s.y == t[1]):
                        break
                    s = rec.step("Right" if s.x < t[0] else "Left" if s.x > t[0] else "Down" if s.y < t[1] else "Up", 1)
                for _ in range(30):
                    if s.mode not in (5, 9): break
                    s = rec.step((), 1)
                if s.mode not in (5, 9):
                    s = emu.wait_until(lambda s: s.mode in (5, 9), 600); rec.step((), 2)
                    emu.note(f"Transition done: room {s.room:02X}, level {s.level}, item {read_room_item(emu)}")
            if then_exit:
                s = nav.exit_screen(then_exit)
                return "reached+left" if s.mode in (5, 9) else "odd"
            return "reached"
        except NavError as e:
            return "nav: " + str(e)[:40]
        finally:
            emu.step = orig
    return policy


def save_segment(name: str, attempt, start_state: str) -> Path:
    SEG_DIR.mkdir(parents=True, exist_ok=True)
    p = SEG_DIR / f"{name}.json"
    p.write_text(json.dumps({"start_state": start_state, "seed": attempt.seed, "frames": attempt.frames,
                             "hearts": attempt.hearts, "note": attempt.note,
                             "inputs": [",".join(b) for b in attempt.inputs]}))
    return p


def run_segment(emu: BizHawk, nav: Navigator, name: str, start_state: str, kind: str, direction: str | None,
                *, tries: int = 40, max_frames: int = 2000, log=print):
    """kind: 'cross' | 'clear' | 'grab'. Returns (attempt, end_state_name) or (None, None)."""
    if kind == "cross":
        policy = make_cross_policy(nav, direction)
        success = lambda emu, s: s.hearts > 0 and s.mode in (5, 9) and s.room != start_room[0]
    elif kind == "clear":
        policy = make_clear_policy(nav, direction)
        success = (lambda emu, s: s.hearts > 0 and s.mode in (5, 9) and s.room != start_room[0]) if direction else                   (lambda emu, s: s.hearts > 0 and not [e for e in read_enemies(emu) if e[1] not in (0x49, 0x2B, 0x2C, 0x2D) and e[1] < 0x50])
    elif kind == "lafight":
        policy = make_lafight_policy(nav, direction)
        success = (lambda emu, s: s.hearts > 0 and s.mode in (5, 9) and s.room != start_room[0]) if direction else                   (lambda emu, s: s.hearts > 0 and not [e for e in read_enemies(emu) if e[1] not in (0x49, 0x2B, 0x2C, 0x2D) and e[1] < 0x50])
    elif kind == "grab":
        policy = make_grab_policy(nav, direction)
        success = lambda emu, s: s.hearts > 0 and read_room_item(emu) is None and (direction is None or s.room != start_room[0])
    else:
        raise ValueError(kind)
    emu.load(start_state); emu.wait(2)
    s0 = emu.state()
    start_room = [s0.room]
    emu.note(f"SEGMENT {name}: {kind}{' ' + direction if direction else ''} from room {s0.room:02X} with {s0.hearts} hearts")
    best = random_search(emu, start_state, policy, success, tries=tries, max_frames=max_frames,
                         label=name, log=log, prefer_hearts=True)
    if best is None:
        emu.note(f"SEGMENT {name}: no success in {tries} tries")
        return None, None
    # replay the winner to land on its end state and bookmark it
    emu.load(start_state)
    for b in best.inputs:
        emu.step(b, 1)
    s = emu.state()
    end_state = f"seg_{name}"
    emu.save(end_state)
    save_segment(name, best, start_state)
    emu.note(f"SEGMENT {name} done: {best.frames} frames, {s.hearts} hearts, now in room {s.room:02X}")
    log(f"[{name}] {kind} {direction or ''}: {best.frames} frames, hearts {best.hearts}, room {s.room:02x}, keys {s.keys}, bombs {s.bombs}")
    return best, end_state
