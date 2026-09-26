"""The whole run: power-on to the end, one master input log, segment by segment.

Development resumes the latest checkpoint; the claim is always made by replaying the entire log
from power-on in a fresh emulator (Run.finish).

    python fullgame.py            # resume the latest checkpoint and continue
    python fullgame.py --from L3_done
    python fullgame.py --verify   # replay the saved log and export the movie, no new segments
"""
import os
import sys
import time

from zelda import ram, bot, replay, bk2
from zelda.runner import Run
from zelda.overworld import Navigator, NavError, LinkDied, read_enemies, read_room_item
from zelda.combat import Fighter
from zelda.segments import (make_cross_policy, make_cross_at_policy, make_grab_policy,
                            make_clear_policy, make_clear_grab_policy, make_lafight_policy,
                            make_lareach_policy)
from zelda.lookahead import Goal
from zelda.search import nudge_into_room
from zelda.cellar import take_raft_cellar_la, take_cellar_item_la
from zelda.boss import Manhandla, parts, gleeok_dead as gleeok_is_dead
from zelda.emulator import LOGS_DIR

LOG = open(LOGS_DIR / "fullgame.txt", "a", buffering=1)


def P(*a):
    print(*a, flush=True)
    print(*a, file=LOG)


# ---------------------------------------------------------------- policies
def start_policy(nav):
    """Power-on to standing outside the sword cave with the sword."""
    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        emu.step = rec.step
        try:
            bot.new_game(emu, log=lambda *a: None)
            bot.enter_cave_up(emu, cave_x=64, log=lambda *a: None)
            bot.take_cave_item(emu, item_x=120, flag_addr=ram.SWORD, log=lambda *a: None)
            bot.exit_cave_down(emu, log=lambda *a: None)
            return "sword"
        except (bot.BotError, NavError, LinkDied) as e:
            return "fail: " + str(e)[:40]
        finally:
            emu.step = orig
    return policy


def enter_level_policy(nav, level):
    """Find this screen's dungeon doorway and go in."""
    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        emu.step = rec.step
        nav.jitter = (rng, rng.choice([0.05, 0.15]))
        try:
            rec.step((), rng.randint(0, 10))
            bot.enter_entrance(nav, level)
            return "in"
        except (NavError, LinkDied, bot.BotError) as e:
            return "nav: " + str(e)[:40]
        finally:
            emu.step = orig
            nav.jitter = None
    return policy


def warp_policy(nav):
    """After a Triforce, wait out the warp back to the dungeon entrance."""
    def policy(emu, rec, rng, max_frames):
        for _ in range(40):
            s = emu.state()
            if s.mode == 5 and s.level == 0:
                return "outside"
            rec.step((), 20)
        return "still warping"
    return policy


def dock_policy(nav):
    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        emu.step = rec.step
        nav.jitter = (rng, rng.choice([0.0, 0.1]))
        try:
            rec.step((), rng.randint(0, 8))
            bot.ride_dock(nav, log=lambda *a: None)
            return "sailed"
        except (bot.BotError, NavError, LinkDied) as e:
            return "fail: " + str(e)[:40]
        finally:
            emu.step = orig
            nav.jitter = None
    return policy


def bomb_policy(nav, direction="Right", then_room=None):
    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        emu.step = rec.step
        nav.jitter = (rng, rng.choice([0.05, 0.15]))
        try:
            rec.step((), rng.randint(0, 8))
            # Standing in the doorway he arrived through, Link cannot be routed anywhere.
            nudge_into_room(emu, rec.step)
            # B uses whatever is in the B slot; make sure that is bombs, not the boomerang
            if not bot.select_b_item(emu, rec.step, bot.B_BOMBS):
                return "could not select bombs"
            try:
                bot.bomb_door(nav, direction)
            except NavError:
                # Only fight when the room is actually in the way. Clearing on principle cost
                # 38 seconds an attempt in Level 7's room 0C, whose three 15-hit monsters the
                # sword cannot finish and whose east wall is a bombable, not a shutter.
                from zelda.lookahead import plan_fight
                emu.step = orig
                plan_fight(emu, rec, max_frames=1800, rng=rng, log=True)
                emu.step = rec.step
                bot.bomb_door(nav, direction)
            s = nav.exit_screen(direction)
            return "through" if (then_room is None or s.room == then_room) else "odd"
        except (NavError, bot.BotError, LinkDied) as e:
            return "nav: " + str(e)[:40]
        finally:
            emu.step = orig
            nav.jitter = None
    return policy


def dash_bomb_policy(nav, direction, then_room=None):
    """Bomb a wall in a room full of things that must not be fought: dash to the spot with the damage-aware
    planner, drop the bomb, keep dodging near it while the fuse burns, and leave through the hole.

    Level 8's Pols Voice room (4C) is the case: its north wall opens straight into the boss room, so the eight
    Pols Voices never have to die - but bomb_policy walks there with the plain navigator and then stands still
    for the fuse, and they hit for two hearts each."""
    from zelda.lookahead import plan_reach

    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        emu.step = rec.step
        try:
            rec.step((), rng.randint(0, 6))
            nudge_into_room(emu, rec.step)
            if not bot.select_b_item(emu, rec.step, bot.B_BOMBS):
                return "could not select bombs"
            tx, ty, face = bot.bomb_spot(emu, direction)
            doors0 = emu.byte(0xEE)
            for _ in range(3):
                if emu.state().bombs < 1:
                    return "no bombs"
                emu.step = orig
                res = plan_reach(emu, rec, Goal(tx, ty, 3), max_frames=900, rng=rng)
                emu.step = rec.step
                if res != "arrived":
                    return res
                st = emu.state()
                for _ in range(24):
                    if (st.x, st.y) == (tx, ty):
                        break
                    st = rec.step(("Right" if st.x < tx else "Left") if st.x != tx else
                                  ("Down" if st.y < ty else "Up"), 1)
                rec.step(face, 1)
                rec.step("B", 2)
                emu.step = orig
                plan_reach(emu, rec, Goal(tx, ty, -1), max_frames=72, rng=rng)     # dodge while it burns
                emu.step = rec.step
                for _ in range(30):
                    if emu.byte(0xEE) != doors0:
                        break
                    rec.step((), 1)
                if emu.byte(0xEE) != doors0:
                    break
            else:
                return "the wall never opened"
            s = nav.exit_screen(direction)
            return "through" if (then_room is None or s.room == then_room) else "odd"
        except (NavError, bot.BotError, LinkDied) as e:
            return "nav: " + str(e)[:40]
        finally:
            emu.step = orig
    return policy


def gleeok_policy(nav, budget=6000):
    # 6,000, the value that has actually won this fight. Widening it to 10,000 made things WORSE,
    # not better: the boss finished on 4-8 health and Link fell to 0.5-2.5 hearts, so extra time
    # buys the planner more damage taken rather than a kill. The old run won here about one
    # attempt in ten, at 6,000, with 80 tries - which is the budget this segment needs.
    # (The 52-minute stall that prompted the change was two runs sharing one CPU, not slowness.)
    # Historic note kept because it is still true of the winning attempts:
    # finished run EVERY successful attempt landed at 6,012-6,020 frames against a 6,000-frame
    # budget; a diagnostic of six fresh attempts timed out with the boss on 10, 8, 2, 10, 10 and
    # 10 health - the kill was close but never inside the window. A bigger window costs search
    # time, not video: Run.segment trims the recorded inputs back to the frame the room clears.
    # Budget halved from 6000 after this fight ate 52 minutes of wall clock without finishing
    # ten attempts. Each attempt runs the lookahead to its budget, and at full health Link
    # survives long enough to use all of it, so 80 tries extrapolated to four hours for one
    # room. The archived winner's room is actually clear by frame 2,345, so 3,000 is enough
    # fight and half the search cost.
    """Gleeok: a stationary head (type 0x43, 10 hits with the wooden sword) that fires unblockable
    fireballs. The lookahead planner scores damage taken during its rollouts, so it learns to
    strike and retreat rather than stand in the fire."""
    from zelda.lookahead import plan_fight

    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        emu.step = rec.step
        try:
            # A WIDE lead-in here, unlike everywhere else. Gleeok's movement and its fireballs
            # run off the frame counter, so when an attempt starts decides which phase of the
            # boss's cycle it fights - and four diagnostics with an 8-frame spread came back
            # byte-for-byte identical, with the body untouched at full health in half of them.
            # 90 frames of spread lets 80 attempts sample the cycle instead of one corner of it.
            rec.step((), rng.randint(0, 90))
            s = emu.state()
            if s.x <= 16 or s.x >= 224 or s.y >= 205 or s.y <= 69:
                rec.step("Right" if s.x <= 16 else "Left" if s.x >= 224 else "Up" if s.y >= 205 else "Down", 16)
            emu.step = orig
            from zelda.boss import gleeok_head_tracker, gleeok_dead
            # Measured against this boss: the sword is the ONLY thing that hurts it (bombs,
            # boomerang and arrows all did nothing), and most swings miss - it took 19 tries to
            # land one by hand. Penalising missed swings, which is right everywhere else, made
            # the planner stop swinging at all here, so switch that penalty off for this fight.
            return plan_fight(emu, rec, max_frames=budget, rollout=20, rng=rng, log=True,
                              targets=gleeok_head_tracker(emu), done=gleeok_dead,
                              hp_weight=140.0, miss_penalty=0.0)
        except LinkDied:
            return "died"
        finally:
            emu.step = orig
    return policy


def manhandla_policy(nav):
    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        emu.step = rec.step
        try:
            # Wide lead-in: this boss moves and fires off the frame counter, so when an
            # attempt starts decides which phase of its cycle gets fought. Gleeok proved it -
            # with an 8-frame spread four diagnostics came back byte-for-byte identical and
            # never killed it; with 90 frames of spread it died on the third attempt.
            rec.step((), rng.randint(0, 30))
            rec.step("Right" if emu.state().x <= 32 else (), 16)      # out of the bombed doorway
            # The scripted bomber (zelda.boss.Manhandla) died 60 times out of 60 from the third run's state.
            # The lookahead fighter with bombs free to use killed it 8 of 8 in 190-260 frames: it SEES, in
            # its rollouts, where a blast catches the heads and where standing gets Link hit.
            from zelda.lookahead import plan_fight
            emu.step = orig
            res = plan_fight(emu, rec, max_frames=2500, rng=rng, use_bombs="free", log=True)
            return "dead" if res == "clear" else res
        except LinkDied:
            return "died"
        finally:
            emu.step = orig
    return policy


def dodongo_policy(nav):
    """Dodongo is the one enemy the general fight planner cannot solve by search: the sword does
    nothing, a blast does nothing, and the only thing that hurts it is swallowing a live bomb.
    That needs a deliberate feed, so it gets its own routine."""
    from zelda.boss import fight_dodongo

    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        try:
            rec.step((), rng.randint(0, 40))
            # B throws whatever is in the B slot, and Link is still carrying the boomerang from
            # Level 1. Put bombs in the slot or this whole fight is a boomerang toss.
            if not bot.select_b_item(emu, rec.step, bot.B_BOMBS):
                return "could not select bombs"
            rec.step("Up", 40)                # clear of the doorway before it can corner Link
            return "dead" if fight_dodongo(emu, rec.step) else "alive"
        except LinkDied:
            return "died"
        finally:
            emu.step = orig
    return policy


def passage_policy(nav):
    """Walk through a passage staircase and out the far end."""
    from zelda.cellar import walk_passage

    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        emu.step = rec.step
        try:
            rec.step((), rng.randint(0, 8))
            walk_passage(emu, rec.step)
            emu.wait_until(lambda s: s.mode == 5, 400)
            return "through"
        except (NavError, LinkDied, bot.BotError) as e:
            return "fail: " + str(e)[:40]
        finally:
            emu.step = orig
    return policy


DIGDOGGER = 0x38


def digdogger_policy(nav, then_exit=None):
    """Digdogger (object type 0x38) ignores the sword until the RECORDER is played at it: the
    noise splits it into a small version that dies to the sword. So put the recorder in the B
    slot, play it, then fight normally.

    Level 7 has one too, and it sits in a room the route passes through twice - and dungeon rooms
    repopulate when Link re-enters them, so the room that was a simple walk on the way out is a
    Digdogger fight on the way back. A plain sword fight there never ends.
    """
    from zelda.lookahead import plan_fight

    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        emu.step = rec.step
        try:
            # Wide lead-in: this boss moves and fires off the frame counter, so when an
            # attempt starts decides which phase of its cycle gets fought. Gleeok proved it -
            # with an 8-frame spread four diagnostics came back byte-for-byte identical and
            # never killed it; with 90 frames of spread it died on the third attempt.
            rec.step((), rng.randint(0, 90))
            nudge_into_room(emu, rec.step)
            s = emu.state()
            if s.x <= 16 or s.x >= 224 or s.y >= 205 or s.y <= 69:
                rec.step("Right" if s.x <= 16 else "Left" if s.x >= 224 else
                         "Up" if s.y >= 205 else "Down", 16)
            if not bot.select_b_item(emu, rec.step, bot.B_RECORDER):
                return "could not select the recorder"
            emu.note("Playing the recorder at Digdogger to break it up")
            rec.step("B", 2)
            rec.step((), 90)
            emu.step = orig
            res = plan_fight(emu, rec, max_frames=4000, rollout=16, rng=rng, log=True)
            emu.step = rec.step
            if res != "clear":
                return res
            Fighter(nav).collect_drop()
            if then_exit:
                s = nav.exit_screen(then_exit)
                return "cleared+left" if s.mode in (5, 9) else "odd"
            return "clear"
        except (LinkDied, NavError, bot.BotError) as e:
            return "fail: " + str(e)[:40]
        finally:
            emu.step = orig
    return policy


OW_STAIRS = {0x70, 0x71, 0x72, 0x73}


def stairs_on_screen(emu):
    """(x, y) of a staircase tile on this screen, or None."""
    from zelda.overworld import read_cells, snap
    cells = read_cells(emu)
    spots = sorted({(r // 2, c // 2) for r in range(22) for c in range(32)
                    if cells[r][c] in OW_STAIRS})
    if not spots:
        return None
    r16, c16 = spots[0]
    return snap(c16 * 16, 64 + r16 * 16 - 3)


def pond_policy(nav):
    """Level 7 sits under a pond. Playing the RECORDER on that screen drains it and uncovers a
    staircase.

    This screen cost the run a whole detour once, because playing the recorder here ALSO summons
    the travelling whirlwind, and "a whirlwind came, so this is the wrong screen" was accepted as
    proof without ever looking at the floor. It is not proof. The water drains about 240 frames
    after the note, whirlwind or no whirlwind, so watch the TILES and wait for the whirlwind to
    leave before walking anywhere.
    """
    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        emu.step = rec.step
        try:
            rec.step((), rng.randint(0, 8))
            if stairs_on_screen(emu) is not None:
                return "already drained"       # the pond stays dry once it has been played to
            s = emu.state()
            if s.y > 200:                      # off the very bottom edge of the screen
                rec.step("Up", 24)
            if not bot.select_b_item(emu, rec.step, bot.B_RECORDER):
                return "could not select the recorder"
            emu.note("Playing the recorder to drain the pond over Level 7")
            rec.step("B", 2)
            for _ in range(30):
                rec.step((), 20)
                spot = stairs_on_screen(emu)
                if spot and not any(t == 0x5E for t in emu.ram(0x34F, 12)):
                    emu.note(f"The pond is gone and there are stairs at {spot}")
                    return "drained"
            return "still wet" if stairs_on_screen(emu) is None else "whirlwind still here"
        except (NavError, LinkDied, bot.BotError) as e:
            return "fail: " + str(e)[:40]
        finally:
            emu.step = orig
    return policy


def stairs_entry_policy(nav, level):
    """Walk into a staircase that is sitting in the open on an overworld screen."""
    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        emu.step = rec.step
        nav.jitter = (rng, rng.choice([0.0, 0.1]))
        try:
            rec.step((), rng.randint(0, 8))
            spot = stairs_on_screen(emu)
            if spot is None:
                return "no stairs on this screen"
            tx, ty = spot
            # The path planner will not route onto a staircase tile - it has never seen one be
            # walkable, and on a drained pond it is surrounded by tiles it also does not know.
            # Walking straight at it works, so square up on x and then hold the direction in.
            st = emu.state()
            for _ in range(400):
                if st.level == level or st.mode not in (5, 9):
                    break
                st = rec.step("Right" if st.x < tx else "Left" if st.x > tx else
                              "Down" if st.y < ty else "Up", 1)
            st = emu.wait_until(lambda s: s.level == level and s.mode == 5, 900)
            rec.step((), 4)
            return "inside" if st.level == level else "did not go down"
        except (NavError, LinkDied, bot.BotError) as e:
            return "fail: " + str(e)[:40]
        finally:
            emu.step = orig
            nav.jitter = None
    return policy


def leave_dungeon_policy(nav):
    """Walk back out of a dungeon the way Link came in, room by room, until he is outside."""
    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        emu.step = rec.step
        try:
            from zelda.lookahead import plan_fight
            rec.step((), rng.randint(0, 8))
            for _ in range(12):
                s = emu.state()
                if s.level == 0:
                    return "outside"
                # several rooms on the way out have shutter doors, so they have to be cleared
                # again on the return trip: use the planner, not a plain walk
                emu.step = orig
                plan_fight(emu, rec, max_frames=2500, rng=rng)
                emu.step = rec.step
                # the way out is not always straight down: 78's only other door is east, and
                # it is locked
                for d in ("Down", "Right", "Left", "Up"):
                    try:
                        nav.exit_screen(d)
                        break
                    except NavError:
                        continue
                else:
                    return "stuck inside"
            return "still inside"
        except (LinkDied, bot.BotError) as e:
            return "fail: " + str(e)[:40]
        finally:
            emu.step = orig
    return policy


def farm_rupees_policy(nav, target):
    """Earn rupees the only way the game offers: kill things and pick up what they drop. Clears
    the screen, steps to a neighbour and back (which respawns it), and repeats."""
    from zelda.lookahead import plan_fight
    from zelda.combat import Fighter

    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        try:
            rec.step((), rng.randint(0, 8))
            for _ in range(8):
                if emu.byte(0x66D) >= target:
                    return "rich"
                emu.step = orig
                plan_fight(emu, rec, max_frames=1200, rng=rng)
                emu.step = rec.step
                Fighter(nav).collect_drop()
                d = rng.choice(["Left", "Right", "Up", "Down"])
                try:
                    nav.exit_screen(d)
                    nav.exit_screen({"Left": "Right", "Right": "Left",
                                     "Up": "Down", "Down": "Up"}[d])
                except NavError:
                    pass
            return "rupees " + str(emu.byte(0x66D))
        except (LinkDied, NavError, bot.BotError) as e:
            return "fail: " + str(e)[:40]
        finally:
            emu.step = orig
    return policy


def farm_dungeon_policy(nav, target, level=6):
    """Earn rupees in a dungeon's entrance rooms, which refill with enemies every time Link walks
    back into the DUNGEON - not when he steps back into the room.

    Two things this got wrong the first time. It only farmed the room to the east, which halves
    the takings when the room to the west is just as full; and it started the cycle wherever the
    last attempt had left Link, so if that was already the east room, the first pass fought an
    empty room. Now every cycle begins outside and works both neighbours.

    Drops are also mostly invisible when Link is at full health and full bombs, so ask for a few
    rupees at a time: an attempt reliably earns about ten, and a segment that asks for fifteen
    more than Link has will fail every single try.
    """
    from zelda.lookahead import plan_fight
    from zelda.combat import Fighter

    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        emu.step = rec.step          # every frame Link actually plays has to be in the log
        entrance = None
        try:
            rec.step((), rng.randint(0, 8))
            for _ in range(6):
                if emu.byte(0x66D) >= target:
                    return "rich"
                # Get back outside so the rooms repopulate. A segment can start Link in either
                # of the two side rooms, not just the entrance, so do not assume which way is
                # out: try south first (that is the way out of an entrance room) and otherwise
                # take any door that works and try again.
                for _ in range(6):
                    if emu.state().level == 0:
                        break
                    for d in ("Down", "Left", "Right", "Up"):
                        try:
                            nav.exit_screen(d)
                            break
                        except (NavError, LinkDied):
                            continue
                    else:
                        break
                if emu.state().level == 0:
                    try:
                        bot.enter_entrance(nav, level)
                    except (NavError, bot.BotError):
                        spot = stairs_on_screen(emu)
                        if spot is None:
                            return "cannot get back in"
                        tx, ty = spot
                        st = emu.state()
                        for _ in range(400):
                            if st.level == level or st.mode not in (5, 9):
                                break
                            st = rec.step("Right" if st.x < tx else "Left" if st.x > tx else
                                          "Down" if st.y < ty else "Up", 1)
                        emu.wait_until(lambda q: q.level == level and q.mode == 5, 900)
                entrance = emu.state().room
                for out, back in (("Right", "Left"), ("Left", "Right")):
                    try:
                        nav.exit_screen(out)
                    except (NavError, LinkDied):
                        continue
                    emu.step = orig
                    plan_fight(emu, rec, max_frames=1500, rng=rng, rupee_target=target)
                    emu.step = rec.step
                    Fighter(nav).collect_drop()
                    if emu.byte(0x66D) >= target:
                        return "rich"
                    try:
                        nav.exit_screen(back)
                    except NavError:
                        pass
            return "rupees " + str(emu.byte(0x66D))
        except (LinkDied, NavError, bot.BotError) as e:
            return "fail: " + str(e)[:40]
        finally:
            emu.step = orig
    return policy


def whirlwind_policy(nav):
    """Play the recorder on the overworld. Instead of draining anything it summons a whirlwind
    that carries Link to the entrance of a dungeon he has already been inside - the game's own
    fast travel, and the only safe way out of the west."""
    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        emu.step = rec.step
        try:
            rec.step((), rng.randint(0, 8))
            if not bot.select_b_item(emu, rec.step, bot.B_RECORDER):
                return "could not select the recorder"
            start = emu.state().room
            emu.note("Playing the recorder outside: the whirlwind is a free ride across the map")
            rec.step("B", 2)
            for _ in range(20):
                s = rec.step((), 30)
                if s.room != start:
                    break
            rec.step((), 150)
            return f"blown to {emu.state().room:02X}"
        except (NavError, LinkDied, bot.BotError) as e:
            return "fail: " + str(e)[:40]
        finally:
            emu.step = orig
    return policy


LEVEL_DOORS = [0x37, 0x3C, 0x74, 0x45, 0x0B, 0x22, 0x42, 0x6D]   # Levels 1-8, all finished


def whirl_to_policy(nav, target, counter=None):
    """Ride the recorder's whirlwind to a finished dungeon's door: one ride, as many notes as it takes.

    From the disassembly (Z_07 WieldFlute, Z_01 SummonWhirlwind / UpdateWhirlwind):
      * the destination counter is RAM $523 (TeleportingLevelIndex; & 7 -> Levels 1..8). Every recorder use
        on the overworld moves it one OWNED level forward (Link facing Right or Up) or back (Left or Down),
        even with a whirlwind already on screen, and the destination is read when the wind picks Link up.
      * the game freezes for the $98-frame tune - the wind too - and a press during the freeze is ignored.
    So read the counter, play one note per step the moment the previous tune ends, and take ONE ride.
    `counter` is ignored now (kept for the call sites): the RAM byte is the truth.
    0x42 is Level 7's pond, where the recorder drains the water instead; step off it first."""
    POND = 0x42

    def owned_steps(idx, goal, step, tri):
        n, i = 0, idx
        while n < 9:
            i = (i + step) % 8
            if tri & (1 << i):
                n += 1
                if i == goal:
                    return n
        return 99

    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        emu.step = rec.step
        try:
            rec.step((), rng.randint(0, 6))
            goal = LEVEL_DOORS.index(target)
            for ride in range(4):
                st = emu.state()
                if st.room == target and st.mode == 5 and not st.level:
                    return "arrived"
                if st.level:
                    bot.hold_until(emu, "Down", lambda q: q.level == 0 and q.mode == 5, 600)
                    continue
                if st.room == POND:
                    nav.exit_screen("Down")
                    continue
                if not bot.select_b_item(emu, rec.step, bot.B_RECORDER):
                    return "could not select the recorder"
                st = emu.state()
                tri = emu.byte(0x671)
                idx = emu.byte(0x523) & 7
                up, down = owned_steps(idx, goal, 1, tri), owned_steps(idx, goal, -1, tri)
                if min(up, down) >= 99:
                    return "that level's Triforce is not owned"
                notes = min(up, down)
                # the facing picks the direction; never face off the edge of the screen
                if up <= down:
                    face = "Up" if st.x >= 224 else "Right"
                else:
                    face = "Down" if st.x <= 16 else "Left"
                # Items cannot be used inside the screen's border strip (a note played at x=240, just off
                # the edge Link walked in by, simply does not sound), and the wind arrives from the left,
                # so keep clear of that side too while there are notes left to play.
                if st.x > 208:
                    rec.step("Left", st.x - 208)
                elif st.x < 48:
                    rec.step("Right", 48 - st.x)
                if st.y > 189:
                    rec.step("Up", st.y - 189)
                elif st.y < 85:
                    rec.step("Down", 85 - st.y)
                st = emu.state()
                if idx == goal:
                    faces = ["Right", "Left"]                # away one level and straight back
                else:
                    faces = [face] * notes
                room0 = st.room
                played = 0
                for face in faces:
                    rec.step(face, 1)
                    rec.step("B", 2)
                    if emu.byte(0x3C) == 0:
                        rec.step((), 2)
                    if emu.byte(0x3C) == 0:
                        break                                # the note did not sound: re-plan from RAM
                    played += 1
                    for _ in range(200):                     # the tune: the whole game is frozen
                        if emu.byte(0x3C) == 0:
                            break
                        rec.step((), 1)
                if not played:
                    rec.step("Right" if st.x < 120 else "Left", 16)
                    continue
                if 0x2E not in emu.ram(0x34F, 12) and emu.byte(0x522) == 0:
                    # no free object slot for the wind (the counter still moved): thin the screen out
                    from zelda.lookahead import plan_fight
                    emu.step = orig
                    plan_fight(emu, rec, max_frames=500, rng=rng)
                    emu.step = rec.step
                    continue
                notes = 0
                # The ride. The wind can MISS: while Link is flashing from a hit the game skips his
                # collisions, the wind's included (a Zora's fireball did exactly this on 0x47). If it sweeps
                # past, the counter has still moved - re-plan from RAM rather than wait for nothing.
                landed = False
                stuck, lastx = 0, -1
                for f in range(900):
                    # walk to meet the wind along its row: a moving Link is a harder target for whatever is
                    # shooting at him, and it costs nothing (the ride is just as long wherever it starts)
                    meet = emu.byte(0x522) == 0 and stuck < 6 and emu.state().x > 56
                    q = rec.step("Left" if meet else (), 1)
                    stuck = stuck + 1 if (meet and q.x == lastx) else 0 if meet else stuck
                    lastx = q.x
                    if q.room != room0 and q.mode == 5 and emu.byte(0x522) == 0 and not (emu.byte(0xAC) & 0x40):
                        landed = True
                        break
                    if (f > 8 and f % 4 == 0 and q.room == room0 and emu.byte(0x522) == 0
                            and 0x2E not in emu.ram(0x34F, 12)):
                        break
                if not landed:
                    continue
            st = emu.state()
            return "arrived" if (st.room == target and not st.level) else f"stopped at {st.room:02X}"
        except (NavError, LinkDied, bot.BotError) as e:
            return "fail: " + str(e)[:40]
        finally:
            emu.step = orig
    return policy


def shop_policy(nav, want_addr, xs=(152, 120, 72)):
    """Walk into the cave on this screen and buy the item that sets `want_addr`.
    `xs` are the counter columns to try, in order - pass only the right one when walking into the
    wrong ware could spend rupees on something else (the 0x44 shop: bombs x=120, arrows x=152)."""
    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        emu.step = rec.step
        try:
            rec.step((), rng.randint(0, 8))
            spot = bot.find_entrance(emu)
            if spot is None:
                return "no cave here"
            ex, ey = spot
            nav.allow_entrances = True
            try:
                nav.go(lambda x, y: abs(x - ex) <= 4 and abs(y - (ey + 16)) <= 8, "below the shop")
            finally:
                nav.allow_entrances = False
            emu.wait_until(lambda s: s.mode == 0x0B, 400, buttons=("Up",))
            emu.wait_until(lambda s: s.y > 190, 400, buttons=("Up",))
            emu.wait_until(lambda s: s.sub == 0, 300, buttons=("Up",))
            # the shopkeeper's text freezes Link exactly like an old man's: hold UP until he
            # is really walking before trying to steer him
            st = bot.hold_until(emu, "Up", lambda s: s.y < 200, 600)
            if st.y >= 200:
                return "never got moving in the shop"
            # The wares are NOT evenly spaced under their price labels: sweeping the counter
            # showed the only two that respond are x=120 (the 20-rupee one) and x=152 (the
            # arrows). Walking into the wrong one spends rupees on something we do not need,
            # so go straight to the right column.
            before = emu.byte(want_addr)
            for x in xs:
                bot.walk_to(emu, None, 173, order="yx", max_frames=300)
                bot.walk_to(emu, x, None, max_frames=300)
                bot.hold_until(emu, "Up", lambda s: emu.byte(want_addr) != before or s.y <= 141, 120)
                if emu.byte(want_addr) != before:
                    emu.note(f"Bought it: RAM ${want_addr:04X} is now {emu.byte(want_addr)}")
                    return "bought"
            return "could not buy"
        except (NavError, LinkDied, bot.BotError) as e:
            return "fail: " + str(e)[:40]
        finally:
            emu.step = orig
    return policy


def cave_exit_policy(nav):
    """Walk back out of a cave or shop onto the overworld."""
    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        emu.step = rec.step
        try:
            rec.step((), rng.randint(0, 8))
            bot.exit_cave_down(emu, log=lambda *a: None)
            return "outside"
        except (NavError, LinkDied, bot.BotError) as e:
            return "fail: " + str(e)[:40]
        finally:
            emu.step = orig
    return policy


def gohma_policy(nav):
    """Gohma: an arrow through the open eye, fired from directly below it, and nothing else.

    That is not from a walkthrough - zelda/tactics.py replayed the real fight from one savestate
    with every weapon from six standing positions, and only arrow-from-below moved its health at
    all (2 hits). The sword, bombs, the boomerang and the recorder all did nothing from anywhere.
    """
    from zelda.boss import fight_gohma

    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        emu.step = rec.step
        try:
            # Wide lead-in: this boss moves and fires off the frame counter, so when an
            # attempt starts decides which phase of its cycle gets fought. Gleeok proved it -
            # with an 8-frame spread four diagnostics came back byte-for-byte identical and
            # never killed it; with 90 frames of spread it died on the third attempt.
            rec.step((), rng.randint(0, 90))
            if not bot.select_b_item(emu, rec.step, bot.B_BOW):
                return "could not select the bow"
            emu.note("GOHMA: sword, bombs and boomerang do nothing. Arrows, from underneath.")
            s = emu.state()
            if s.y >= 205:
                rec.step("Up", 10)
            return "clear" if fight_gohma(emu, rec.step, rng, max_steps=500) else "still alive"
        except (NavError, LinkDied, bot.BotError) as e:
            return "fail: " + str(e)[:40]
        finally:
            emu.step = orig
    return policy


def feed_goriya_policy(nav):
    """Room 28 of Level 7 is the only door into the northern half, and a Goriya is standing in it.
    Nothing kills it. Dropping the FOOD makes it walk off to eat, and then the door is free."""
    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        emu.step = rec.step
        try:
            rec.step((), rng.randint(0, 8))
            nudge_into_room(emu, rec.step)
            if not bot.select_b_item(emu, rec.step, bot.B_BAIT):
                return "could not select the food"
            emu.note("Dropping the food for the hungry Goriya")
            rec.step("B", 2)
            rec.step((), 120)
            s = nav.exit_screen("Up")
            return "fed" if s.mode in (5, 9) else "odd"
        except (NavError, LinkDied, bot.BotError) as e:
            return "fail: " + str(e)[:40]
        finally:
            emu.step = orig
    return policy


FAIRY = 0x2F


def fairy_policy(nav):
    """An overworld fairy pond restores every heart. The fairy (object type 2F) drifts around the
    middle of the pond; Link only has to touch it, so chase it until the hearts come back."""
    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        emu.step = rec.step
        try:
            rec.step((), rng.randint(0, 8))
            s = emu.state()
            if s.hearts >= s.containers:
                return "already full"
            if s.y > 200:
                rec.step("Up", 24)
            def back_out():
                # Chasing the fairy walks Link INTO the pond, and the path planner cannot route
                # him out of water - every neighbouring square is water too, so it reports no
                # path in any direction and the next segment fails. Walk back south by hand.
                for _ in range(200):
                    q = emu.state()
                    if q.mode != 5 or q.y >= 200:
                        return
                    rec.step("Down", 2)

            for _ in range(400):
                s = emu.state()
                if s.hearts >= s.containers:
                    back_out()
                    return "healed"
                ts = emu.ram(0x34F, 12); xs = emu.ram(0x70, 12); ys = emu.ram(0x84, 12)
                live = [i for i in range(12) if ts[i] == FAIRY]
                if not live:
                    rec.step(rng.choice(("Up", "Down", "Left", "Right")), 6)
                    continue
                i = min(live, key=lambda i: abs(xs[i] - s.x) + abs(ys[i] - s.y))
                dx, dy = xs[i] - s.x, ys[i] - s.y
                d = ("Right" if dx > 0 else "Left") if abs(dx) > abs(dy) else ("Down" if dy > 0 else "Up")
                rec.step(d, 3)
            back_out()
            return f"still on {emu.state().hearts} hearts"
        except (NavError, LinkDied, bot.BotError) as e:
            return "fail: " + str(e)[:40]
        finally:
            emu.step = orig
    return policy


def grave_shop_policy(nav, want_addr):
    """The cheap food shop (square E-4, screen 0x34) has no cave mouth at all: that screen is a
    GRAVEYARD, and the stairs are underneath the middle gravestone of the top row. Gravestones
    slide without the Power Bracelet, so stand west of it at (48,125), push east until a
    staircase tile appears, and walk in. Found by pushing every stone on the screen from every
    side off an in-memory snapshot; only that one opens anything. Inside, the food is at x=152.
    """
    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        emu.step = rec.step
        try:
            rec.step((), rng.randint(0, 8))
            spot = stairs_on_screen(emu)
            if spot is None:
                nav.go(lambda x, y: abs(x - 48) <= 4 and abs(y - 125) <= 4,
                       "west of the gravestone", optimistic=True, max_replans=60)
                for _ in range(24):
                    rec.step("Right", 6)
                    if stairs_on_screen(emu):
                        break
                spot = stairs_on_screen(emu)
                if spot is None:
                    return "the gravestone did not move"
            sx, sy = spot
            emu.note(f"Stairs under the gravestone at {spot}; walking in")
            st = emu.state()
            for _ in range(300):
                if st.mode != 5:
                    break
                st = rec.step("Right" if st.x < sx else "Left" if st.x > sx else
                              "Down" if st.y < sy else "Up", 1)
            emu.wait_until(lambda q: q.mode == 0x0B, 400, buttons=("Up",))
            emu.wait_until(lambda q: q.y > 190, 400, buttons=("Up",))
            emu.wait_until(lambda q: q.sub == 0, 300, buttons=("Up",))
            st = bot.hold_until(emu, "Up", lambda q: q.y < 200, 600)
            if st.y >= 200:
                return "never got moving in the shop"
            before = emu.byte(want_addr)
            for x in (152, 120, 72):
                bot.walk_to(emu, None, 173, order="yx", max_frames=300)
                bot.walk_to(emu, x, None, max_frames=300)
                bot.hold_until(emu, "Up", lambda q: emu.byte(want_addr) != before or q.y <= 141, 150)
                if emu.byte(want_addr) != before:
                    emu.note(f"Bought it: RAM ${want_addr:04X} is now {emu.byte(want_addr)}")
                    return "bought"
            return "could not buy"
        except (NavError, LinkDied, bot.BotError) as e:
            return "fail: " + str(e)[:40]
        finally:
            emu.step = orig
    return policy


def burn_entry_policy(nav, stand, face, level):
    """Burn the scenery at a measured spot and walk into what it uncovers.

    Level 8's front door is here. Every guide calls it a burnable bush; on screen it is drawn
    with the same tiles as the mountain around it, which is why sweeping outward from anything
    tree-shaped found nothing. zelda/secrets.py found it by standing on every square Link can
    reach and burning in every direction that faced something solid.
    """
    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        emu.step = rec.step
        nav.jitter = (rng, rng.choice([0.0, 0.1]))
        try:
            rec.step((), rng.randint(0, 8))
            from zelda import secrets
            spot = secrets.opening(emu)
            if spot is None:
                tx, ty = stand
                nav.go(lambda x, y: abs(x - tx) <= 4 and abs(y - ty) <= 4,
                       "the burning spot", optimistic=True, max_replans=60)
                if not bot.select_b_item(emu, rec.step, bot.B_CANDLE):
                    return "could not select the candle"
                rec.step(face, 1)
                rec.step("B", 2)
                for _ in range(20):
                    rec.step((), 12)
                    spot = secrets.opening(emu)
                    if spot:
                        break
                if spot is None:
                    return "nothing burned"
            sx, sy = spot
            emu.note(f"Burned it open: a staircase at {spot}")
            # What the fire uncovers is a staircase, not a cave mouth - it is walked ONTO, not
            # entered from below. And it needs the path planner to get there: aiming Link at it
            # in a straight line wedges him against the mountain while the screen's Moblins take
            # pieces out of him.
            nav.go(lambda x, y: abs(x - sx) <= 8 and abs(y - sy) <= 8, "the stairs",
                   optimistic=True, max_replans=80)
            st = emu.state()
            for _ in range(300):
                if st.level == level or st.mode not in (5, 9):
                    break
                st = rec.step("Right" if st.x < sx else "Left" if st.x > sx else
                              "Down" if st.y < sy else "Up", 1)
            st = emu.wait_until(lambda q: q.level == level and q.mode == 5, 900)
            rec.step((), 4)
            return "inside" if st.level == level else "did not go in"
        except (NavError, LinkDied, bot.BotError) as e:
            return "fail: " + str(e)[:40]
        finally:
            emu.step = orig
            nav.jitter = None
    return policy


# What the rest of the route can still spend: arrows at a rupee a shot. The first run's kept attempts
# spent Gohma 2, Pols Voices 8-10, Level 9's Like Likes 13-27 and Ganon a few; probes put the Like Likes
# at up to 27. 60 covers the worst of those with room for the odd arrow the planner's "bomb" move fires
# when the bow is still in the B slot. ganon_policy gives up at zero rupees, so this is not optional.
ARROW_PURSE = 60


def purse_or_cave_policy(cave, need):
    """Run a money cave only when the purse is below `need`; otherwise do nothing at all."""
    def policy(emu, rec, rng, max_frames):
        if emu.byte(0x66D) >= need:
            rec.step((), 2)
            return f"skipped: {emu.byte(0x66D)} rupees cover the arrows"
        return cave(emu, rec, rng, max_frames)
    return policy


def burn_cave_policy(nav, stand, face, want_rupees=True):
    """Burn a measured spot, walk into whatever it uncovers, take what is inside, come back out.

    This is how the secret money caves work: an old man who hands over 30 or 100 rupees for
    nothing. zelda/secrets.py finds the spot; this just performs it.
    """
    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        emu.step = rec.step
        nav.jitter = (rng, rng.choice([0.0, 0.1]))
        try:
            from zelda import secrets
            rec.step((), rng.randint(0, 8))
            before = emu.byte(0x66D)
            spot = secrets.opening(emu)
            if spot is None:
                tx, ty = stand
                nav.go(lambda x, y: abs(x - tx) <= 4 and abs(y - ty) <= 4,
                       "the burning spot", optimistic=True, max_replans=60)
                if not bot.select_b_item(emu, rec.step, bot.B_CANDLE):
                    return "could not select the candle"
                rec.step(face, 1)
                rec.step("B", 2)
                for _ in range(20):
                    rec.step((), 12)
                    spot = secrets.opening(emu)
                    if spot:
                        break
                if spot is None:
                    return "nothing burned"
            emu.note(f"Burned it open: {spot}")
            mouth = bot.find_entrance(emu)
            if mouth:
                bot.enter_entrance(nav, None)
            else:
                sx, sy = spot
                nav.go(lambda x, y: abs(x - sx) <= 8 and abs(y - sy) <= 8, "the stairs",
                       optimistic=True, max_replans=80)
                st = emu.state()
                for _ in range(300):
                    if st.mode not in (5, 9) or st.level:
                        break
                    st = rec.step("Right" if st.x < sx else "Left" if st.x > sx else
                                  "Down" if st.y < sy else "Up", 1)
            emu.wait_until(lambda q: q.mode == 0x0B, 400, buttons=("Up",))
            emu.wait_until(lambda q: q.y > 190, 400, buttons=("Up",))
            emu.wait_until(lambda q: q.sub == 0, 300, buttons=("Up",))
            bot.hold_until(emu, "Up", lambda q: q.y < 200, 600)
            bot.walk_to(emu, None, 173, order="yx", max_frames=300)
            bot.walk_to(emu, 120, None, max_frames=300)
            # The rupee counter ANIMATES - about fifteen a second - so a hundred-rupee cave looks
            # exactly like a one-rupee cave if you read the total the moment it first moves. Wait
            # until it has been still for a while before believing it.
            last, still = emu.byte(0x66D), 0
            for _ in range(40):
                rec.step("Up", 20)
                now = emu.byte(0x66D)
                still = still + 1 if now == last else 0
                last = now
                if still >= 4:
                    break
            got = emu.byte(0x66D) - before
            emu.note(f"That cave was worth {got} rupees")
            bot.exit_cave_down(emu, log=lambda *a: None)
            return f"took {got}" if (got > 0 or not want_rupees) else "nothing in there"
        except (NavError, LinkDied, bot.BotError) as e:
            return "fail: " + str(e)[:40]
        finally:
            emu.step = orig
            nav.jitter = None
    return policy


def bow_fight_policy(nav, then_exit=None):
    """Clear a room with the BOW in the B slot and the lookahead free to use it.

    Pols Voice - the hopping rabbit-eared things - have ten hit points and take exactly ten from
    one arrow, while the White Sword does two and gets Link killed. Measured with tactics.survey
    on Level 8's room 4C: arrows 50 damage and Link alive, sword 8 damage and Link dead every
    time. The boomerang and the recorder do nothing at all.
    """
    from zelda.lookahead import plan_fight

    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        emu.step = rec.step
        try:
            rec.step((), rng.randint(0, 8))
            nudge_into_room(emu, rec.step)
            if not bot.select_b_item(emu, rec.step, bot.B_BOW):
                return "could not select the bow"
            emu.step = orig
            res = plan_fight(emu, rec, max_frames=max_frames, rng=rng, log=True,
                             use_bow=True, miss_penalty=0.0, hp_weight=140.0)
            emu.step = rec.step
            if res != "clear":
                return res
            Fighter(nav).collect_drop()
            if then_exit:
                s = nav.exit_screen(then_exit)
                return "cleared+left" if s.mode in (5, 9) else "odd"
            return "clear"
        except (NavError, LinkDied, bot.BotError) as e:
            return "fail: " + str(e)[:40]
        finally:
            emu.step = orig
    return policy


def bow_clear_grab_policy(nav, max_fight=4500):
    """Clear a room with the BOW available to the lookahead, then take the reward it leaves.

    Level 9 room 0x25 holds the bomb pile Link needs, and its floor item only appears once the room
    is cleared. The sword-only make_clear_grab_policy timed out on all fifty attempts there (2500
    frames each): two Like Likes, which this run already learned shrug off the sword but die to one
    arrow each, two Zols, and two Bubbles - unkillable, and touching one disables the SWORD, not the
    bow. bow_fight_policy clears such rooms but never waits for the reward; this does both.
    """
    from zelda.lookahead import plan_fight

    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        emu.step = rec.step
        f = Fighter(nav)
        try:
            rec.step((), rng.randint(0, 8))
            nudge_into_room(emu, rec.step)
            if not bot.select_b_item(emu, rec.step, bot.B_BOW):
                return "could not select the bow"
            emu.step = orig
            res = plan_fight(emu, rec, max_frames=max_fight, rng=rng, log=True,
                             use_bow=True, miss_penalty=0.0, hp_weight=140.0)
            emu.step = rec.step
            if res != "clear":
                return res
            for _ in range(14):                      # the reward appears a few frames later
                if read_room_item(emu) is not None:
                    break
                rec.step((), 8)
            if read_room_item(emu) is None:
                return "cleared, but no reward appeared"
            f.grab_key_by_dodging()
            return "done"
        except (NavError, LinkDied, bot.BotError) as e:
            return "fail: " + str(e)[:40]
        finally:
            emu.step = orig
    return policy


def stairs_here_policy(nav, spot=None):
    """Walk into a staircase that is already visible in this room (no clearing, no block push)."""
    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        emu.step = rec.step
        try:
            rec.step((), rng.randint(0, 8))
            nudge_into_room(emu, rec.step)
            from zelda.overworld import read_cells, snap
            cells = read_cells(emu)
            found = sorted({(r // 2, c // 2) for r in range(22) for c in range(32)
                            if cells[r][c] in OW_STAIRS})
            if not found and spot is None:
                return "no stairs here"
            tx, ty = spot if spot else snap(found[0][1] * 16, 64 + found[0][0] * 16 - 3)
            nav.go(lambda x, y: abs(x - tx) <= 8 and abs(y - ty) <= 8, "the stairs",
                   optimistic=True, max_replans=80)
            st = emu.state()
            for _ in range(200):
                if st.mode != 5:
                    break
                st = rec.step("Right" if st.x < tx else "Left" if st.x > tx else
                              "Down" if st.y < ty else "Up", 1)
            st = emu.wait_until(lambda q: q.mode == 9 and q.sub >= 9, 900)
            return "descended"
        except (NavError, LinkDied, bot.BotError) as e:
            return "fail: " + str(e)[:40]
        finally:
            emu.step = orig
    return policy


def bomb_entry_policy(nav, stand, face, doorway, level):
    """Blow open a dungeon door in the overworld rock and walk in.

    Level 9's door is the south wall of the left rock of Spectacle Rock: stand at (80,173), face
    up, one bomb. The four tiles above turn into the black doorway 0x24 - with no arch above them,
    which is why the usual cave-mouth finder cannot see it. Then simply hold UP.
    """
    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        emu.step = rec.step
        nav.jitter = (rng, rng.choice([0.0, 0.1]))
        try:
            rec.step((), rng.randint(0, 8))
            tx, ty = stand
            # Spectacle Rock is Lynel country and the plain path planner walks Link straight
            # through them - he died on every single attempt. plan_reach scores the damage it
            # would take during its rollouts, so it goes round them instead.
            from zelda.lookahead import plan_reach
            # ...that was the OLD navigator. The new one prices Lynels by what they do and cuts down what
            # stands in the lane, and it gets here in 270-311 frames against the planner's 424-810. The search
            # tries both and keeps whichever came out ahead.
            res = None
            if rng.random() < 0.65:
                try:
                    nav.go(lambda x, y: abs(x - tx) <= 6 and abs(y - ty) <= 6, "the bombing spot",
                           optimistic=True, max_replans=80)
                    res = "arrived"
                except NavError:
                    res = None
            if res is None:
                emu.step = orig
                res = plan_reach(emu, rec, Goal(tx, ty, 6), max_frames=4000, rng=rng)
                emu.step = rec.step
            if res != "arrived":
                return "could not reach the bombing spot: " + str(res)
            dx, dy = doorway
            from zelda.overworld import read_cells
            cells = read_cells(emu)
            r8, c8 = (dy + 3 - 64) // 8, dx // 8
            if not (0 <= r8 < 22 and 0 <= c8 < 32 and cells[r8][c8] == 0x24):
                # Coming back from the Magical Sword: a doorway this run already blew open is
                # still open, and bombing it again would spend a bomb Level 9 needs. If this
                # check is ever wrong it just bombs, exactly as before.
                if not bot.select_b_item(emu, rec.step, bot.B_BOMBS):
                    return "could not select bombs"
                rec.step(face, 1)
                rec.step("B", 2)
                for i in range(160):
                    rec.step((), 1)
                    if i >= 40 and i % 2 == 0 and read_cells(emu)[r8][c8] == 0x24:
                        break                      # the rock is open: go, do not stand among the Lynels
            st = emu.state()
            for _ in range(300):
                if st.level == level or st.mode not in (5, 9):
                    break
                st = rec.step("Right" if st.x < dx else "Left" if st.x > dx else
                              "Down" if st.y < dy else "Up", 1)
            st = emu.wait_until(lambda q: q.level == level and q.mode == 5, 900)
            rec.step((), 4)
            return "inside" if st.level == level else "did not go in"
        except (NavError, LinkDied, bot.BotError) as e:
            return "fail: " + str(e)[:40]
        finally:
            emu.step = orig
            nav.jitter = None
    return policy


def cellar_policy(nav):
    def policy(emu, rec, rng, max_frames):
        try:
            rec.step((), rng.randint(0, 30))
            return "raft" if take_raft_cellar_la(emu, rec, rng) else "no raft"
        except (NavError, LinkDied) as e:
            return "fail: " + str(e)[:40]
    return policy


def triforce_policy(nav, bit, direction='Up'):
    """Take the boss's heart container, go north, take the Triforce, wait for the warp."""
    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        emu.step = rec.step
        try:
            for _ in range(8):
                if read_room_item(emu):
                    break
                rec.step((), 15)
            nav.grab_room_item()
            nav.exit_screen(direction)
            it = read_room_item(emu)
            if not it:
                return "no triforce"
            t, ix, iy = it
            nav.go(lambda x, y: abs(x - ix) <= 8 and abs(y - iy) <= 8, "the Triforce", max_replans=80)
            for _ in range(3):
                if emu.byte(0x671) & bit:
                    break
                nav.go(lambda x, y: x == (ix // 8) * 8 and y == ((iy - 5) // 8) * 8 + 5, "the Triforce exactly")
                rec.step((), 4)
            for _ in range(40):
                if emu.state().level == 0:
                    break
                rec.step((), 20)
            return "triforce" if emu.byte(0x671) & bit else "missed"
        except (NavError, LinkDied) as e:
            return "nav: " + str(e)[:40]
        finally:
            emu.step = orig
    return policy



def clear_push_stairs_policy(nav):
    """Take the staircase in this room. Some rooms show it from the start (just walk in), others
    only reveal it once the room is cleared and a block is pushed. Unkillable things (blade traps,
    bubbles) are never waited on."""
    from zelda.overworld import read_cells, snap
    from zelda.lookahead import plan_fight, killable
    STAIRS = {0x70, 0x71, 0x72, 0x73}

    def stairs_at(emu):
        cells = read_cells(emu)
        spots = sorted({(r // 2, c // 2) for r in range(22) for c in range(32) if cells[r][c] in STAIRS})
        if not spots:
            return None
        r16, c16 = spots[0]
        return snap(c16 * 16, 64 + r16 * 16 - 3)

    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        emu.step = rec.step
        try:
            rec.step((), rng.randint(0, 8))
            s = emu.state()
            if s.level and (s.x <= 16 or s.x >= 224 or s.y >= 205 or s.y <= 69):
                rec.step("Right" if s.x <= 16 else "Left" if s.x >= 224 else "Up" if s.y >= 205 else "Down", 16)
            spot = stairs_at(emu)
            if spot is None:
                if [e for e in read_enemies(emu) if killable(e)]:
                    emu.step = orig
                    res = plan_fight(emu, rec, max_frames=2500, rng=rng, log=True)
                    emu.step = rec.step
                    if res != "clear":
                        return res
                nav.push_blocks_for_door("Up")
                spot = stairs_at(emu)
                if spot is None:
                    # push_blocks_for_door only tries the blocks that would open a door. Level
                    # 7's room 0D hides its staircase under a different one, so fall back to
                    # shoving whatever will move.
                    nav.push_any_block(rng)
                    spot = stairs_at(emu)
                if spot is None:
                    return "no stairs appeared"
            tx, ty = spot
            emu.note(f"Stairs at ({tx},{ty}); walking in")
            room0 = emu.state().room
            try:
                nav.go(lambda x, y: abs(x - tx) <= 8 and abs(y - ty) <= 8, "the stairs",
                       optimistic=True, max_replans=80)
            except NavError:
                # visible but walled in: a ring of blocks guards it and one of them shifts
                emu.note("The stairs are walled in; looking for the block that moves")
                if [e for e in read_enemies(emu) if killable(e)]:
                    emu.step = orig
                    plan_fight(emu, rec, max_frames=2500, rng=rng, log=True)
                    emu.step = rec.step
                if not nav.push_any_block(rng):
                    return "stairs walled in"
                spot = stairs_at(emu) or spot
                tx, ty = spot
                nav.go(lambda x, y: abs(x - tx) <= 8 and abs(y - ty) <= 8, "the stairs",
                       optimistic=True, max_replans=80)
            st = emu.state()
            for _ in range(160):
                if st.mode not in (5, 9) or st.room != room0:
                    break
                st = rec.step("Right" if st.x < tx else "Left" if st.x > tx else "Down" if st.y < ty else "Up", 1)
            for _ in range(600):
                st = emu.state()
                if st.mode == 9 and st.sub >= 9:
                    break
                rec.step((), 4)
            emu.note(f"Down the stairs: room {st.room:02X} mode {st.mode:02x}")
            return "descended"
        except (NavError, LinkDied) as e:
            return "fail: " + str(e)[:40]
        finally:
            emu.step = orig
    return policy


def cave_item_policy(nav, flag_addr):
    """Overworld cave: walk into the doorway, take what is inside, walk back out. Used for the
    White Sword (and the starting sword works the same way)."""
    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        emu.step = rec.step
        nav.jitter = (rng, rng.choice([0.0, 0.1]))
        try:
            rec.step((), rng.randint(0, 8))
            spot = bot.find_entrance(emu)
            if spot is None:
                return "no cave here"
            ex, ey = spot
            # this screen can hold a Blue Lynel, which hits for two hearts; use the damage-aware
            # planner to get to the mouth rather than walking a shortest path through it
            from zelda.lookahead import plan_reach, Goal
            nav.allow_entrances = True
            try:
                emu.step = orig
                res = plan_reach(emu, rec, Goal(ex, ey + 16, 6), max_frames=5000, rng=rng)
                emu.step = rec.step
                if res != "arrived":
                    return "approach: " + res
            finally:
                nav.allow_entrances = False
            # the planner stops within a few pixels of the mouth; the cave only swallows Link
            # if he is lined up on its x exactly, so square up before walking in
            bot.walk_to(emu, ex, None, stop=lambda s: s.mode == 0x0B)
            emu.wait_until(lambda s: s.mode == 0x0B, 400, buttons=("Up",))
            bot.take_cave_item(emu, item_x=None, flag_addr=flag_addr, log=lambda *a: None)
            bot.exit_cave_down(emu, log=lambda *a: None)
            return "got it"
        except (NavError, LinkDied, bot.BotError) as e:
            return "fail: " + str(e)[:40]
        finally:
            emu.step = orig
            nav.jitter = None
    return policy


def cellar_item_policy(nav, flag_addr):
    """Standard item cellar: fetch the item and climb back out."""
    def policy(emu, rec, rng, max_frames):
        try:
            rec.step((), rng.randint(0, 30))
            return "item" if take_cellar_item_la(emu, rec, flag_addr, rng) else "no item"
        except (NavError, LinkDied) as e:
            return "fail: " + str(e)[:40]
    return policy


# filled in from the explorer's findings
L1_TO_WS_DIRS = ["Right", "Up", "Right", "Right", "Right", "Right", "Up", "Left", "Left", "Up"]
L1_TO_WS_ROOMS = [0x38, 0x28, 0x29, 0x2A, 0x2B, 0x2C, 0x1C, 0x1B, 0x1A, 0x0A]
L3_TO_L1_DIRS = ["Left", "Up", "Right", "Right", "Right", "Right", "Right", "Up", "Up", "Up", "Left"]
L3_TO_L1_ROOMS = [0x73, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x58, 0x48, 0x38, 0x37]
# the White Sword screen back down to the raft dock: retrace the way up, then south and west
# 1B -> 1C is not walkable even though 1C -> 1B is, so the explorer found the way round: west
# along row 1, down the west side, then south-east to the dock.
WS_TO_L4_DIRS = ["Down", "Right", "Left", "Left", "Left", "Left", "Down", "Right", "Down",
                 "Down", "Left", "Left", "Down", "Left"]
WS_TO_L4_ROOMS = [0x1A, 0x1B, 0x1A, 0x19, 0x18, 0x17, 0x27, 0x28, 0x38,
                  0x48, 0x47, 0x46, 0x56, 0x55]
# the Level 4 dock to Level 2's screen
L4_TO_L2_DIRS = ["Right", "Right", "Right", "Right", "Right", "Right", "Right", "Right",
                 "Up", "Left", "Up"]
L4_TO_L2_ROOMS = [0x56, 0x57, 0x58, 0x59, 0x5A, 0x5B, 0x5C, 0x5D, 0x4D, 0x4C, 0x3C]
# Level 2's screen to the foot of the Lost Hills
L2_TO_HILLS_DIRS = ["Down", "Right", "Up", "Up", "Left", "Up", "Left"]
L2_TO_HILLS_ROOMS = [0x4C, 0x4D, 0x3D, 0x2D, 0x2C, 0x1C, 0x1B]
# the Lost Hills down to Level 7's pond screen
# 55 is the lake screen: water splits it down the middle, so arriving from the east there is no
# way to its west edge on foot. Go south out of it and round instead.
# the foot of the Lost Hills to the shop cave at 0x44
HILLS_TO_SHOP_DIRS = ["Left", "Left", "Left", "Left", "Down", "Right", "Down", "Down",
                      "Left", "Left", "Down", "Left", "Down", "Left", "Up", "Up"]
HILLS_TO_SHOP_ROOMS = [0x1A, 0x19, 0x18, 0x17, 0x27, 0x28, 0x38, 0x48,
                       0x47, 0x46, 0x56, 0x55, 0x65, 0x64, 0x54, 0x44]

L5_TO_L7_DIRS = ["Left", "Left", "Left", "Left", "Down", "Right", "Down", "Down",
                 "Left", "Left", "Down", "Left", "Down", "Left", "Left", "Left", "Up", "Up"]
L5_TO_L7_ROOMS = [0x1A, 0x19, 0x18, 0x17, 0x27, 0x28, 0x38, 0x48,
                  0x47, 0x46, 0x56, 0x55, 0x65, 0x64, 0x63, 0x62, 0x52, 0x42]


def hc_cave_policy(nav, stand, face, method, item_x=152):
    """Open a measured secret, walk in, and take the HEART CONTAINER from a TAKE-ANY-ONE cave.

    Two of the overworld heart containers sit in caves where the old man offers a red potion on
    the LEFT or a heart container on the RIGHT, and the other choice is gone for good. The wares are
    not in the object table - only the old man (type 6B, x=120) and his two flames (x=72, 168) are -
    so bot.cave_item_x reports the old man. x=152 comes from screenshots of both caves, and success
    is counted in heart containers, never in "some byte changed".
    """
    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        emu.step = rec.step
        nav.jitter = (rng, rng.choice([0.0, 0.1]))
        try:
            from zelda import secrets
            from zelda.overworld import read_cells
            from zelda.lookahead import plan_reach
            rec.step((), rng.randint(0, 8))
            want = emu.state().containers + 1
            tx, ty = stand
            emu.step = orig
            res = plan_reach(emu, rec, Goal(tx, ty, 4), max_frames=4000, rng=rng)
            emu.step = rec.step
            if res != "arrived":
                return "could not reach the spot: " + str(res)
            # plan_reach stops within a few pixels. A bomb's blast forgives that; a candle flame
            # does not - 0x47's tree opened for none of four seeds from "close enough" - so square
            # up exactly on the measured spot before using the item.
            try:
                bot.walk_to(emu, tx, ty, order="xy", max_frames=120)
            except (bot.BotError, NavError):
                pass
            base = read_cells(emu)
            if not bot.select_b_item(emu, rec.step, bot.B_BOMBS if method == "bomb" else bot.B_CANDLE):
                return f"could not select the {method}"
            rec.step(face, 1)
            rec.step("B", 2)
            spot = None
            for _ in range(20):
                rec.step((), 12)
                spot = secrets.opening(emu, base)
                if spot:
                    break
            if spot is None:
                q = emu.state()
                return f"nothing opened from ({q.x},{q.y}) facing {face}"
            ox, oy = spot
            emu.note(f"The {method} opened a secret at {spot}. Going in for the heart container")
            st = emu.state()
            if stairs_on_screen(emu):
                # a burned tree leaves a staircase: step onto it
                for _ in range(300):
                    if st.mode != 5:
                        break
                    st = rec.step("Right" if st.x < ox else "Left" if st.x > ox else
                                  "Down" if st.y < oy else "Up", 1)
            else:
                # a bombed rock leaves a bare doorway: square up underneath it, then walk in
                nav.go(lambda x, y: abs(x - ox) <= 2 and abs(y - (oy + 16)) <= 4,
                       "just below the new doorway", optimistic=True, max_replans=60)
                for _ in range(120):
                    st = rec.step("Up", 1)
                    if st.mode != 5:
                        break
            if st.mode == 5:
                return "could not get in"
            emu.wait_until(lambda q: q.mode == 0x0B, 400, buttons=("Up",))
            emu.wait_until(lambda q: q.y > 190, 400, buttons=("Up",))
            emu.wait_until(lambda q: q.sub == 0, 300, buttons=("Up",))
            st = bot.hold_until(emu, "Up", lambda q: q.y < 200, 600)
            if st.y >= 200:
                return "never got moving in the cave"
            bot.walk_to(emu, None, 173, order="yx", max_frames=300)
            bot.walk_to(emu, item_x, None, max_frames=300)
            bot.hold_until(emu, "Up", lambda q: q.containers >= want or q.y <= 141, 200)
            if emu.state().containers < want:
                return "did not get the heart container"
            emu.note(f"HEART CONTAINER! Link now has {emu.state().containers}")
            bot.exit_cave_down(emu, log=lambda *a: None)
            return "took the heart container"
        except (NavError, LinkDied, bot.BotError) as e:
            return "fail: " + str(e)[:40]
        finally:
            emu.step = orig
            nav.jitter = None
    return policy


def grave_sword_policy(nav, need=12):
    """The MAGICAL SWORD. Overworld 0x21 is the graveyard's top-right screen; the stone at tile
    (row 5, col 9) - middle row, third from the left - slides when pushed UP from (144,157), and
    holding Up afterwards walks Link straight down the new staircase. The old man hands the sword
    over only at TWELVE heart containers. Touching graveyard stones calls Ghinis, so the approach
    is damage-aware. Verified by screenshot before this policy was written."""
    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        emu.step = rec.step
        nav.jitter = (rng, rng.choice([0.0, 0.1]))
        try:
            from zelda.lookahead import plan_reach
            rec.step((), rng.randint(0, 8))
            if emu.state().containers < need:
                return f"fewer than {need} heart containers"
            emu.step = orig
            res = plan_reach(emu, rec, Goal(144, 157, 4), max_frames=4000, rng=rng)
            emu.step = rec.step
            if res != "arrived":
                return "could not reach the gravestone: " + str(res)
            try:
                bot.walk_to(emu, 144, 157, order="xy", max_frames=120)
            except bot.BotError:
                pass
            st = emu.state()
            for _ in range(60):
                st = rec.step("Up", 4)
                if st.mode != 5:
                    break
            if st.mode == 5:
                return "the gravestone did not move"
            emu.note("The gravestone slid and Link walked down the stairs: the Magical Sword's cave")
            bot.take_cave_item(emu, item_x=120, flag_addr=0x657, log=lambda *a: None)
            bot.exit_cave_down(emu, log=lambda *a: None)
            return "got the Magical Sword"
        except (NavError, LinkDied, bot.BotError) as e:
            return "fail: " + str(e)[:40]
        finally:
            emu.step = orig
            nav.jitter = None
    return policy


def open_or_bomb_policy(nav, direction, then_room=None):
    """Go through a bombable wall, bombing it only if it is still shut. A wall this run already
    blew open stays open, and bomb_policy would spend a bomb Level 9 cannot spare."""
    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        emu.step = rec.step
        nav.jitter = (rng, rng.choice([0.05, 0.15]))
        try:
            rec.step((), rng.randint(0, 8))
            nudge_into_room(emu, rec.step)
            try:
                s = nav.exit_screen(direction)
            except NavError:
                if not bot.select_b_item(emu, rec.step, bot.B_BOMBS):
                    return "could not select bombs"
                try:
                    bot.bomb_door(nav, direction)
                except NavError:
                    from zelda.lookahead import plan_fight
                    emu.step = orig
                    plan_fight(emu, rec, max_frames=1800, rng=rng, log=True)
                    emu.step = rec.step
                    bot.bomb_door(nav, direction)
                s = nav.exit_screen(direction)
            return "through" if (then_room is None or s.room == then_room) else "odd"
        except (NavError, bot.BotError, LinkDied) as e:
            return "nav: " + str(e)[:40]
        finally:
            emu.step = orig
            nav.jitter = None
    return policy


def fight_then_bomb_policy(nav, direction, then_room=None, max_fight=2500):
    """Kill what is in the room with the damage-aware planner FIRST, then open the bombable wall.

    open_or_bomb_policy walks straight to the wall and bombs it with the room still alive. In Level 9's
    0x20 that means three Blue and two Red Wizzrobes shooting through walls while Link stands still to
    place a bomb: every success of the live run's search lost 7-10 of 11.5 hearts, and the next rooms
    (more Wizzrobes, then Ganon) are not survivable at 1.5. The Magical Sword kills a Red Wizzrobe in one
    hit and a Blue in three, and dead Wizzrobes drop hearts."""
    from zelda.lookahead import plan_fight

    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        try:
            rec.step((), rng.randint(0, 8))
            emu.step = rec.step
            nudge_into_room(emu, rec.step)
            emu.step = orig                              # lookahead branches must not be recorded
            plan_fight(emu, rec, max_frames=max_fight, rng=rng, log=True)
            emu.step = rec.step
            Fighter(nav).collect_drop()
            nav.jitter = (rng, rng.choice([0.05, 0.15]))
            try:
                s = nav.exit_screen(direction)
            except NavError:
                if not bot.select_b_item(emu, rec.step, bot.B_BOMBS):
                    return "could not select bombs"
                bot.bomb_door(nav, direction)
                s = nav.exit_screen(direction)
            return "through" if (then_room is None or s.room == then_room) else "odd"
        except (NavError, bot.BotError, LinkDied) as e:
            return "nav: " + str(e)[:40]
        finally:
            emu.step = orig
            nav.jitter = None
    return policy


def settle_policy(nav, pred, max_wait=900):
    """Press nothing until `pred(state)` holds - e.g. until a raft ride has actually ended.

    dock_policy's segments succeed the moment the screen changes, but the raft keeps sailing Link
    down the channel to the pier after that. The next segment then planned from open water - "no
    path to the Down edge from (128,90)" - or pressed Up and sailed straight back to the island."""
    def policy(emu, rec, rng, max_frames):
        for _ in range(max_wait // 10):
            if pred(emu.state()):
                return "settled"
            rec.step((), 10)
        return "never settled"
    return policy


GANON = 0x3E        # object type: entry 62 of UpdateObject_JumpTable (disassembly Z_07.asm)


def ganon_slot(emu):
    ts = emu.ram(0x34F, 12)
    for i in range(1, 12):
        if ts[i] == GANON:
            return i
    return None


def ganon_dead(emu):
    """True once Ganon's death has run far enough for the Triforce of Power to appear (phase $A0)."""
    sl = ganon_slot(emu)
    return sl is not None and emu.byte(0x42C + sl) >= 0xA0


def ganon_policy(nav, budget=12000):
    """GANON, written from the game's own code (aldonunez/zelda1-disassembly: Z_04.asm UpdateGanon,
    Ganon_UpdateBrownState, Ganon_CheckCollisions) rather than from a walkthrough's description.

    - $445 scene phase 0 and 1 are the Triforce scene, with Link halted; 2 is the fight.
    - BLUE (ObjState $AC+slot = 0): invisible and teleport-walking, a fireball every $40 frames. A sword
      hit only lands while his timer ($28+slot) is 0; a hit shows him for $40 frames, unhurtable.
    - Four Magical Sword hits make him BROWN: ObjState becomes $FF and counts down every other frame,
      about 510 frames, while he stands still. At 0 he is blue again somewhere new, at full strength.
    - Only while he is brown does an arrow hurt him, and only the SILVER arrow ($0659 = 2). That starts
      his death (Ganon_ObjPhase $42C+slot > 0); at phase $A0 the Triforce of Power appears.

    So: bow into the B slot first, the sword under the lookahead while he is blue, and the moment he
    turns brown, line up on his middle and shoot. Every arrow costs a rupee."""
    from zelda.lookahead import plan_fight, plan_reach

    def blue_ganon(e):
        sl = ganon_slot(e)
        if sl is None or e.byte(0xAC + sl) != 0 or e.byte(0x42C + sl):
            return []
        return [x for x in read_enemies(e) if x[0] == sl]

    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        try:
            # Wide lead-in: this boss moves and fires off the frame counter, so when an
            # attempt starts decides which phase of its cycle gets fought. Gleeok proved it -
            # with an 8-frame spread four diagnostics came back byte-for-byte identical and
            # never killed it; with 90 frames of spread it died on the third attempt.
            rec.step((), rng.randint(0, 90))
            for _ in range(240):                                   # the Triforce scene: Link is halted
                if emu.byte(0x445) >= 2:
                    break
                rec.step((), 5)
            emu.step = rec.step
            if not bot.select_b_item(emu, rec.step, bot.B_BOW):
                return "could not select the bow"
            emu.step = orig
            used = 0
            while used < budget:
                s = emu.state()
                if s.hearts <= 0:
                    return "died"
                sl = ganon_slot(emu)
                if sl is None:
                    return "no Ganon in the room"
                if emu.byte(0x42C + sl):
                    break                                          # the silver arrow landed: dying
                f0 = s.frame
                if emu.byte(0xAC + sl) == 0:
                    # BLUE: let the lookahead swing at him and dodge the fireballs. It scores health
                    # going DOWN, and the stunning fourth hit sends his HP UP to $F0 - so as far as
                    # the planner is concerned, Ganon is gone the moment he turns brown.
                    plan_fight(emu, rec, max_frames=240, rng=rng, targets=blue_ganon,
                               done=lambda e: not blue_ganon(e))
                else:
                    # BROWN: he stands still. Line up on his middle (x+16, y+16) and loose an arrow.
                    if s.rupees <= 0:
                        return "no rupees left to shoot"
                    gx, gy = emu.byte(0x70 + sl), emu.byte(0x84 + sl)
                    cx, cy = gx + 16, gy + 16
                    spots = [(gx - 28, cy - 8, "Right"), (gx + 44, cy - 8, "Left"),
                             (cx - 8, gy - 28, "Down"), (cx - 8, gy + 44, "Up")]
                    spots = [(x, y, f) for x, y, f in spots if 32 <= x <= 208 and 77 <= y <= 189]
                    spots.sort(key=lambda sp: abs(sp[0] - s.x) + abs(sp[1] - s.y))
                    for tx, ty, face in spots:
                        if emu.byte(0xAC + sl) == 0 or emu.byte(0x42C + sl):
                            break
                        res = plan_reach(emu, rec, Goal(tx, ty, 6), max_frames=160, rng=rng)
                        if res != "arrived":
                            continue
                        rec.step(face, 1)
                        rec.step("B", 2)
                        for _ in range(30):
                            rec.step((), 1)
                            if emu.byte(0x42C + sl):
                                break
                        if emu.byte(0x42C + sl):
                            break
                used += emu.state().frame - f0
            sl = ganon_slot(emu)
            if sl is None or not emu.byte(0x42C + sl):
                return "Ganon still standing"
            for _ in range(400):                                   # burst, ashes, Triforce of Power
                if ganon_dead(emu):
                    break
                rec.step((), 1)
            return "GANON DEFEATED" if ganon_dead(emu) else "dying, but no Triforce yet"
        except (NavError, LinkDied, bot.BotError) as e:
            return "fail: " + str(e)[:40]
        finally:
            emu.step = orig
    return policy


RED_WIZZROBE = 0x24
DROPPED_ITEM = 0x60          # a dead monster's slot becomes this object type while its drop lies there


def dropped_items(emu):
    """(slot, item id, x, y) for every monster drop lying in the room. A drop is NOT the room item
    (read_room_item's slot 0x13): the dead monster's own slot turns into object type $60 and the item
    id sits in $AC+slot (disassembly: Z_07 UpdateMetaObjectEnd, Z_04 SetUpDroppedItem)."""
    ts = emu.ram(0x34F, 12)
    return [(i, emu.byte(0xAC + i), emu.byte(0x70 + i), emu.byte(0x84 + i))
            for i in range(1, 12) if ts[i] == DROPPED_ITEM]


def bomb_drop_policy(nav, max_fight=2000):
    """Earn a bomb the way the game hands them out. Written from the drop code in
    aldonunez/zelda1-disassembly, not from folklore:
    - WorldKillCycle ($52A) steps 0..9 on every kill, BEFORE the drop is chosen; it is the column.
    - A Red Wizzrobe (0x24) is in drop row 2: 22,00,18,21,18,22,00,18,00,22 - a bomb in columns 1, 6
      and 8, and the drop happens when a random byte is below $68 (41%).
    - The tenth-kill 'help' drop only gives a bomb if the tenth kill was BY a bomb - useless with none -
      and any hit on Link resets that count anyway.
    Level 9's room 0x04 is where the passage from 0x30 surfaces; its only way on is a bombable wall,
    and Link arrives with none. The kill cycle there is 0, so the very next kill picks column 1: if
    that kill is a Red Wizzrobe, it can drop a bomb. So fight only the red ones until one dies, then
    walk to whatever it left. If the drop is not a bomb, the attempt has failed and the search retries."""
    from zelda.lookahead import plan_fight, plan_reach

    def reds(e):
        return [x for x in read_enemies(e) if x[1] == RED_WIZZROBE]

    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        try:
            rec.step((), rng.randint(0, 40))
            if emu.state().bombs > 0:
                return "already have bombs"
            cyc0 = emu.byte(0x52A)
            if (cyc0 + 1) % 10 not in (1, 6, 8):
                return f"kill cycle {cyc0}: the next kill is not a bomb column"
            if not reds(emu):
                return "no Red Wizzrobe here"
            drops0 = {d[0] for d in dropped_items(emu)}
            res = plan_fight(emu, rec, max_frames=max_fight, rng=rng, targets=reds,
                             done=lambda e: e.byte(0x52A) != cyc0)
            if emu.byte(0x52A) == cyc0:
                return "no kill: " + res
            drop = None
            for _ in range(60):                       # the death cloud comes first, then the item
                new = [d for d in dropped_items(emu) if d[0] not in drops0]
                if new:
                    drop = new[0]
                    break
                rec.step((), 1)
            if drop is None or drop[1] != 0x00:
                return f"kill at column {emu.byte(0x52A)} dropped {'nothing' if drop is None else hex(drop[1])}"
            sl, _, ix, iy = drop
            emu.note(f"A BOMB DROP at ({ix},{iy}) - going for it")
            for _ in range(6):
                if emu.state().bombs > 0 or emu.byte(0x34F + sl) != DROPPED_ITEM:
                    break
                plan_reach(emu, rec, Goal(ix, iy, 4), max_frames=240, rng=rng)
                st = emu.state()
                for _ in range(24):
                    if st.bombs > 0 or emu.byte(0x34F + sl) != DROPPED_ITEM:
                        break
                    dx, dy = ix - st.x, iy - st.y
                    if dx == 0 and dy == 0:
                        break
                    st = rec.step(("Right" if dx > 0 else "Left") if abs(dx) >= abs(dy)
                                  else ("Down" if dy > 0 else "Up"), 1)
            s = emu.state()
            return f"bombs {s.bombs}" if s.bombs > 0 else "the bomb got away"
        except (NavError, LinkDied, bot.BotError) as e:
            return "fail: " + str(e)[:40]
        finally:
            emu.step = orig
    return policy


GUARD_FIRE = 0x3F
ZELDA = 0x37


def zelda_policy(nav, budget=3000):
    """The last room, written from the game's code (aldonunez/zelda1-disassembly Z_04 InitZelda,
    UpdateGuardFire, UpdateZelda):
    - Zelda is object type $37 in slot 1 at ($78,$88); four guard fires, type $3F, stand in slots 2-5 at
      ($60,$B5) ($70,$9D) ($80,$9D) ($90,$B5). The fires die to the sword like any monster.
    - Nothing happens until Link stands with X in $70..$80 and Y exactly $95. Then Link is halted,
      moved to ($88,$88) facing her, the fanfare plays, and $80 frames later GameMode ($12) becomes $13:
      the ending. The two inner fires sit at Y $9D, right under that spot, so they have to go first."""
    from zelda.lookahead import plan_fight

    def fires(e):
        return [x for x in read_enemies(e) if x[1] == GUARD_FIRE]

    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        try:
            rec.step((), rng.randint(0, 8))
            if fires(emu):
                res = plan_fight(emu, rec, max_frames=budget, rng=rng, targets=fires,
                                 done=lambda e: not fires(e))
                if fires(emu):
                    return "the fires still burn: " + res
            emu.step = rec.step
            nav.go(lambda x, y: x == 120 and 157 <= y <= 173, "below Zelda", optimistic=True, max_replans=40)
            st = emu.state()
            for _ in range(120):                       # straight up the middle to Y $95
                if emu.byte(0x12) == 0x13 or (0x70 <= st.x <= 0x80 and st.y == 0x95):
                    break
                st = rec.step("Up" if st.y > 0x95 else "Down", 1)
            for _ in range(400):                       # the fanfare, then mode $13
                if emu.byte(0x12) == 0x13:
                    return "ZELDA RESCUED"
                rec.step((), 1)
            s = emu.state()
            return f"no ending: Link at ({s.x},{s.y}) mode {emu.byte(0x12):02X}"
        except (NavError, LinkDied, bot.BotError) as e:
            return "fail: " + str(e)[:40]
        finally:
            emu.step = orig
    return policy


def credits_policy(nav, hold=300, max_wait=20000):
    """Let the ending play out, touching nothing. Mode $13 (Z_02 UpdateMode13WinGame): the curtain,
    Zelda's thanks, the flashing Link-and-Zelda scene, the peace text, the credits scroll, and finally
    submode 4 - the Triforce over Ganon's ashes, waiting for Start. Pressing Start there saves and
    switches the profile to the second quest, so the run stops on that screen with no input at all."""
    def policy(emu, rec, rng, max_frames):
        for _ in range(max_wait // 10):
            if emu.byte(0x12) == 0x13 and emu.byte(0x13) == 4:
                rec.step((), hold)
                return "THE END"
            rec.step((), 10)
        return f"still in the ending: mode {emu.byte(0x12):02X} submode {emu.byte(0x13):02X}"
    return policy


def take_triforce_policy(nav, budget=600):
    """Take the Triforce of Power out of Ganon's ashes. The generic grab policy failed all 12 probe
    attempts with "gave up reaching the item", for two reasons: the ashes are still an object of
    Ganon's own type (0x3E) sitting on the item, so the navigator counts that square as occupied; and
    the item lies at x 60, which is not on Link's eight-pixel walking grid, so "stand exactly on it"
    can never come true. Nothing in the room can hurt Link any more - so walk straight at it and let
    the game's own collision do the rest (Z_01 TakeItem: in a dungeon it is taken on touch, no lift).

    There is no inventory byte to check. Measured by diffing all 2KB of RAM across the pickup: taking
    it changes no item slot at all - not Items+$1B ($0672), which the item table would suggest.
    Z_01 TakePowerTriforce only sets TriforceFanfareActive ($509) and halts Link for $C0 frames. So
    "taken" means the room item is gone, with the fanfare flag up while it plays."""
    def policy(emu, rec, rng, max_frames):
        rec.step((), rng.randint(0, 8))
        for _ in range(budget):
            it = read_room_item(emu)
            if it is None:
                break
            _, ix, iy = it
            s = emu.state()
            if s.hearts <= 0:
                return "died"
            dx, dy = ix - s.x, iy - s.y
            if abs(dx) <= 2 and abs(dy) <= 2:
                rec.step((), 1)
                continue
            rec.step(("Right" if dx > 0 else "Left") if abs(dx) >= abs(dy)
                     else ("Down" if dy > 0 else "Up"), 1)
        if read_room_item(emu) is not None:
            return f"not taken: item still at {read_room_item(emu)[1:]}"
        rec.step((), 200)                        # the fanfare halts Link for $C0 frames; let it finish
        return "TRIFORCE OF POWER"
    return policy


def walk_out_policy(nav, direction, then_room, spot=None, budget=900):
    """Leave by a door without asking the navigator to find the way. Ganon's room defeated nav.go()
    12/12 times ("gave up reaching the Up door") even with the shutter open and nothing alive: its
    floor is drawn in the doorway-style tiles (0x24), which the walkability map does not count as
    floor, so no route exists as far as the planner is concerned. Both other ways out worked in the
    probe - plan_reach to the doorway then hold the direction, and even walking straight at it."""
    from zelda.lookahead import plan_reach
    SPOTS = {"Up": (120, 85), "Down": (120, 189), "Left": (32, 141), "Right": (208, 141)}

    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        try:
            rec.step((), rng.randint(0, 8))
            tx, ty = spot or SPOTS[direction]
            room0 = emu.state().room

            def line_up(step):
                st = emu.state()
                stall, last = 0, None
                for _ in range(240):
                    if abs(st.x - tx) <= 2 and abs(st.y - ty) <= 2:
                        return True
                    st = step(("Right" if st.x < tx else "Left") if abs(st.x - tx) > 2
                              else ("Down" if st.y < ty else "Up"), 1)
                    stall = stall + 1 if (st.x, st.y) == last else 0
                    last = (st.x, st.y)
                    if stall >= 8 or st.room != room0 or st.mode != 5:
                        return False
                return False

            h0 = emu.state().hearts
            root = emu.msave()
            straight = line_up(emu.step) and emu.state().hearts >= h0          # scratch copy: not recorded
            emu.mload(root)
            emu.mfree(root)
            if straight:
                line_up(rec.step)
                res = "arrived"
            else:
                res = plan_reach(emu, rec, Goal(tx, ty, 6), max_frames=budget, rng=rng)
            emu.step = rec.step
            if res != "arrived" and emu.state().room == room0:
                st = emu.state()                     # last resort: line up on the door and push
                for _ in range(200):
                    if abs(st.x - tx) <= 2 and abs(st.y - ty) <= 2:
                        break
                    st = rec.step(("Right" if st.x < tx else "Left") if abs(st.x - tx) > 2
                                  else ("Down" if st.y < ty else "Up"), 1)
            st = emu.state()
            for _ in range(400):
                if st.room != room0 and st.mode == 5:
                    break
                st = rec.step(direction, 1)
            for _ in range(300):
                st = emu.state()
                if st.mode == 5 and st.room != room0:
                    break
                rec.step((), 2)
            s = emu.state()
            return f"in room {s.room:02X}" if s.room == then_room else f"ended in room {s.room:02X}"
        except (NavError, LinkDied, bot.BotError) as e:
            return "fail: " + str(e)[:40]
        finally:
            emu.step = orig
    return policy


def bomb_cave_policy(nav, stand, face, want=30, budget=2500):
    """Bomb open a money cave, walk in, take what the old man leaves, and come back out.

    Written from four probes on screen 0x67. The cave pays 30 rupees; farming the same money cost
    about 620 frames per rupee, this costs about 37. Two things had to be measured rather than
    assumed: `read_room_item` is None for an old man's gift (so the money is found by walking north
    up the middle and watching the rupee counter, not by looking at the item slot), and the cave
    needs a couple of hundred frames to finish loading before any of that works."""
    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        emu.step = rec.step
        try:
            rec.step((), rng.randint(0, 8))
            before = emu.byte(0x66D)
            if emu.state().bombs < 1:
                return "no bombs to open it with"
            nav.go(lambda x, y: (x, y) == stand, "the rock", optimistic=True, max_replans=40)
            rec.step(face, 2)
            if not bot.select_b_item(emu, rec.step, bot.B_BOMBS):
                return "could not select bombs"
            rec.step("B", 2)
            for _ in range(90):
                rec.step((), 1)
            st = emu.state()
            for _ in range(240):                      # walk into the hole the bomb made
                if st.mode in (0x0B, 0x10):
                    break
                st = rec.step("Up", 1)
            if emu.state().mode not in (0x0B, 0x10):
                return "the bomb opened nothing"
            for _ in range(400):                      # let the cave load
                st = emu.state()
                if st.mode == 0x0B and st.y > 150:
                    break
                rec.step((), 2)
            for _ in range(400):                      # north up the middle, onto the money
                st = emu.state()
                if emu.byte(0x66D) >= before + want:
                    break
                if st.x < 116:
                    rec.step("Right", 1)
                elif st.x > 124:
                    rec.step("Left", 1)
                elif st.y > 140:
                    rec.step("Up", 1)
                else:
                    rec.step((), 1)
            got = emu.byte(0x66D) - before
            for _ in range(200):                      # back out the way we came in
                st = emu.state()
                if st.mode == 5:
                    break
                rec.step("Down", 1)
            return f"took {got}" if got else "the cave paid nothing"
        except (NavError, LinkDied, bot.BotError) as e:
            return "fail: " + str(e)[:40]
        finally:
            emu.step = orig
    return policy


def secret_cave_policy(nav, stand, face, method, want=30, budget=900):
    """Open a secret rupee cave (or walk into one already drawn), take the money, walk back out.

    method: "push" leans on the Armos from `stand`; "bomb" blows the rock in front of `stand`;
    "walk" is for a staircase already drawn on the screen (stand may be None).

    All of it was learned by probing. The navigator stands on the exact tile (the planner alone reached
    0x3D's spot one time in three) with the planner as fallback. A bombed doorway only shows up as tiles
    that CHANGED, so the screen is photographed first. Link enters a cave at the bottom, the gift sits in
    the middle and the room-item slot reads empty for it, so the money is found by walking north watching
    $066D - and a 100-rupee gift is counted up one rupee at a time, so wait for the WHOLE amount (a probe
    that stopped early read +46 on 0x0F's hundred). Owner's rule: never farm; the caves hold 550 rupees."""
    from zelda.lookahead import plan_reach
    from zelda.overworld import read_cells
    from zelda import secrets

    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        try:
            rec.step((), rng.randint(0, 8))
            before = emu.byte(0x66D)
            if method == "bomb" and emu.state().bombs < 1:
                return "no bombs to open it with"
            emu.step = rec.step
            base = None
            if method != "walk":
                try:
                    nav.go(lambda x, y: (x, y) == stand, "the cave spot", optimistic=True, max_replans=60)
                except NavError:
                    emu.step = orig
                    plan_reach(emu, rec, Goal(stand[0], stand[1], 3), max_frames=budget, rng=rng)
                    emu.step = rec.step
                st = emu.state()
                for _ in range(60):
                    if (st.x, st.y) == stand:
                        break
                    st = rec.step(("Right" if st.x < stand[0] else "Left") if st.x != stand[0]
                                  else ("Down" if st.y < stand[1] else "Up"), 1)
                if (st.x, st.y) != stand:
                    return f"could not stand at {stand}"
                base = read_cells(emu)
                if method == "push":
                    for _ in range(140):
                        if emu.state().mode in (0x0B, 0x10) or secrets.opening(emu, base):
                            break
                        rec.step(face, 1)
                else:
                    if not bot.select_b_item(emu, rec.step, bot.B_BOMBS):
                        return "could not select bombs"
                    rec.step(face, 1)
                    rec.step("B", 2)
                    for i in range(150):
                        rec.step((), 1)
                        if i >= 40 and i % 2 == 0 and secrets.opening(emu, base) is not None:
                            break                  # the cave mouth is drawn: stop waiting for the smoke
            st = emu.state()
            for _ in range(400):                               # onto the staircase
                if st.mode in (0x0B, 0x10):
                    break
                op = secrets.opening(emu, base) if base is not None else secrets.opening(emu)
                if op is None:
                    st = rec.step(face, 1)
                    continue
                dx, dy = op[0] - st.x, op[1] - st.y
                st = rec.step(("Right" if dx > 0 else "Left") if abs(dx) > 2 else ("Down" if dy > 0 else "Up"), 1)
            if emu.state().mode not in (0x0B, 0x10):
                return "never got into the cave"
            for _ in range(400):                               # let the cave finish loading
                st = emu.state()
                if st.mode == 0x0B and st.y > 150:
                    break
                rec.step((), 2)
            target = min(255, before + want)
            for _ in range(700):                               # onto the money, and let it count up
                st = emu.state()
                if emu.byte(0x66D) >= target:
                    break
                rec.step("Right" if st.x < 116 else "Left" if st.x > 124 else ("Up" if st.y > 140 else ()), 1)
            got = emu.byte(0x66D) - before
            for _ in range(260):                               # back out
                if emu.state().mode == 5:
                    break
                rec.step("Down", 1)
            for _ in range(200):
                st = emu.state()
                if st.mode == 5 and st.level == 0:
                    break
                rec.step((), 2)
            return f"took {got}" if got > 0 else "the cave paid nothing"
        except (NavError, LinkDied, bot.BotError) as e:
            return "fail: " + str(e)[:40]
        finally:
            emu.step = orig
    return policy


def hold_through_policy(nav, x, direction, to_room, budget=400):
    """Walk through a gap the navigator believes is solid rock.

    0x1F's top edge reads as unbroken rock in the tile map and nav.exit_screen refuses it at every
    column, yet holding Up at x=128 walks straight into 0x0F - the screen with the guide's 100-rupee
    cave. Get to that column near the edge with the navigator, square up, and hold the direction."""
    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        emu.step = rec.step
        try:
            rec.step((), rng.randint(0, 8))
            if direction == "Up":
                near = lambda px, py: px == x and py <= 93
            else:
                near = lambda px, py: px == x and py >= 189
            try:
                nav.go(near, f"the gap at x={x}", optimistic=True, max_replans=60)
            except (NavError, LinkDied):
                pass
            st = emu.state()
            for _ in range(60):
                if st.x == x:
                    break
                st = rec.step("Right" if st.x < x else "Left", 1)
            start = st.room
            for _ in range(budget):
                if st.room != start:
                    break
                st = rec.step(direction, 1)
            for _ in range(200):
                if emu.state().mode == 5:
                    break
                rec.step((), 2)
            r = emu.state().room
            return "through" if r == to_room else f"ended on {r:02X}"
        except (NavError, LinkDied) as e:
            return "fail: " + str(e)[:40]
        finally:
            emu.step = orig
    return policy


def cross(d, room, tries=30):
    return (lambda nav: make_cross_policy(nav, d),
            (lambda emu, s: s.room == room and s.mode == 5 and s.hearts > 0), tries)


# ---------------------------------------------------------------- the run
def segments():
    """The route in force. ZELDA_ROUTE=4 selects the route planner's errand order (route4.py, journal 41); the
    default is still route 3, the order the verified 41:15 run was played in - its checkpoints, recording and
    captions all key on these names."""
    base = segments_v3()
    if os.environ.get("ZELDA_ROUTE", "3") == "4":
        import route4
        return route4.build(base, sys.modules[__name__])
    return base


def segments_v3():
    """(name, factory, success, tries) in order. Rooms are ROM ids; overworld ids are screens."""
    def cleared(emu, s):
        return s.hearts > 0 and not [e for e in read_enemies(emu)
                                     if e[1] not in (0x49, 0x2B, 0x2C, 0x2D) and e[1] < 0x50]

    def ok(room, **need):
        return lambda emu, s: (s.room == room and s.mode == 5 and s.hearts > 0
                               and all(getattr(s, k) >= v for k, v in need.items()))

    def started():
        from zelda import runner as zrunner
        return zrunner.SEG_START

    def ok_gain(room, **gain):
        """ok(), counted from the state the segment STARTED in - "one more key than Link walked in with".
        The absolute counts copied from the first run go true too early (or never) as soon as the route
        before them changes what Link carries, and the single Level 6 climb already does."""
        return lambda emu, s: (s.room == room and s.mode == 5 and s.hearts > 0
                               and all(getattr(s, k) >= getattr(started(), k) + v for k, v in gain.items()))

    S = []
    S.append(("start", start_policy, lambda emu, s: s.sword >= 1 and s.mode == 5 and s.level == 0, 8))
    # overworld to Level 3
    for d, room in zip(["Left", "Up", "Left", "Left", "Left", "Down", "Right"],
                       [0x76, 0x66, 0x65, 0x64, 0x63, 0x73, 0x74]):
        S.append((f"ow_{room:02x}",) + cross(d, room))
    S.append(("enter_L3", lambda nav: enter_level_policy(nav, 3),
              lambda emu, s: s.level == 3 and s.mode == 5 and s.hearts > 0, 20))
    # Level 3
    L3 = [("7c_left", lambda nav: make_cross_policy(nav, "Left"), 0x7B, 20, {}),
          ("7b_key", lambda nav: make_grab_policy(nav, "Up"), 0x6B, 40, {"keys": 1}),
          ("6b_up", lambda nav: make_cross_policy(nav, "Up"), 0x5B, 40, {}),
          ("5b_bombs", lambda nav: make_clear_grab_policy(nav, "Up"), 0x4B, 80, {"bombs": 1}),
          ("4b_left", lambda nav: make_cross_policy(nav, "Left"), 0x4A, 30, {}),
          ("4a_bombs", lambda nav: make_clear_policy(nav, "Left"), 0x49, 60, {"bombs": 5}),
          ("49_key", lambda nav: make_grab_policy(nav, "Down"), 0x59, 40, {"keys": 1}),
          ("59_fight", lambda nav: make_lafight_policy(nav, "Down"), 0x69, 20, {}),
          ]
    for name, fac, room, tries, need in L3:
        S.append((name, fac, (lambda room, need: (lambda emu, s: s.room == room and s.mode == 5 and s.hearts > 0
                                                  and all(getattr(s, k) >= v for k, v in need.items())))(room, need), tries))
    S.append(("69_stairs", lambda nav: make_lareach_policy(nav, Goal(208, 141, 6), exit_ok=True),
              lambda emu, s: s.hearts > 0 and s.room == 0x0F and s.mode == 9, 40))
    S.append(("cellar", cellar_policy,
              lambda emu, s: s.hearts > 0 and emu.byte(0x660) == 1 and s.room == 0x69 and s.mode == 5, 30))
    S.append(("69_up", lambda nav: make_lareach_policy(nav, Goal(120, 77, 4), then_exit="Up"),
              lambda emu, s: s.hearts > 0 and s.room == 0x59 and s.mode == 5, 40))
    for name, d, room in (("59_up", "Up", 0x49), ("49_right", "Right", 0x4A),
                          ("4a_right", "Right", 0x4B), ("4b_right", "Right", 0x4C)):
        S.append((name,) + cross(d, room, 40))
    S.append(("4c_bomb", lambda nav: bomb_policy(nav, "Right", 0x4D),
              lambda emu, s: s.room == 0x4D and s.mode == 5 and s.hearts > 0, 40))
    S.append(("manhandla", manhandla_policy,
              lambda emu, s: s.room == 0x4D and not parts(emu) and s.hearts > 0, 60))
    S.append(("L3_done", lambda nav: triforce_policy(nav, 0x04),
              lambda emu, s: bool(emu.byte(0x671) & 0x04), 10))
    # --- plan revised 2026-09-12: Gleeok needs the White Sword, and the White Sword needs a
    # fifth heart container, so Level 1 (and Aquamentus) comes before Level 4.
    S.append(("warp_L3", warp_policy, lambda emu, s: s.mode == 5 and s.level == 0, 4))
    for d, room in zip(L3_TO_L1_DIRS, L3_TO_L1_ROOMS):
        S.append((f"ow1_{room:02x}",) + cross(d, room))
        if room == 0x67:
            # "IT'S A SECRET TO EVERYBODY" - 30 rupees under a rock Link is already walking past,
            # for one of the six bombs he is carrying. Measured: +30 in about 1,100 frames, against
            # ~620 frames per rupee for farming. This is the only cave whose money arrives before
            # the arrows have to be bought; every burn cave waits on a candle from Level 7.
            S.append(("cave_67", lambda nav: bomb_cave_policy(nav, (112, 93), "Up", want=30),
                      lambda emu, s: (s.hearts > 0 and s.level == 0 and s.mode == 5
                                      and s.room == 0x67 and emu.byte(0x66D) >= 25), 30))
    S.append(("enter_L1", lambda nav: enter_level_policy(nav, 1),
              lambda emu, s: s.level == 1 and s.mode == 5 and s.hearts > 0, 20))
    # Level 1 (route in knowledge/route_level1_and_white_sword.md)
    S.append(("l1_72",      lambda nav: make_cross_policy(nav, "Left"),   ok(0x72), 30))
    S.append(("l1_72_key",  lambda nav: make_clear_grab_policy(nav, "Right"), ok(0x73, keys=1), 60))
    # (The detour east for 74's key is gone: bombing 53's north wall below saves the locked door that key
    # was for. Keys: 72, 53, 33, 23, 45 for the five locks 63, 23, 22, 44, 35.)
    S.append(("l1_63",      lambda nav: make_cross_policy(nav, "Up"),     ok(0x63), 40))
    S.append(("l1_53",      lambda nav: make_cross_policy(nav, "Up"),     ok(0x53), 40))
    S.append(("l1_53_key",  lambda nav: make_clear_grab_policy(nav, None),    cleared, 60))
    # no bombs in hand, so take the walkthrough's alternative: west and north through locked
    # doors instead of blasting the wall (53 -> 52 -> 42 -> 43)
    # Link HAS bombs now (Level 3 came first), so blast 53's north wall - 280 frames in the probe, 3 of 3 -
    # instead of the three-room loop through a locked door that the bombless route needed.
    S.append(("l1_43",      lambda nav: bomb_policy(nav, "Up", 0x43),     ok(0x43), 40))
    S.append(("l1_33",      lambda nav: make_cross_policy(nav, "Up"),     ok(0x33), 40))
    S.append(("l1_33_key",  lambda nav: make_grab_policy(nav, "Up"),      ok(0x23), 50))
    S.append(("l1_23_key",  lambda nav: make_clear_grab_policy(nav, None),    cleared, 40))
    S.append(("l1_22",      lambda nav: make_cross_policy(nav, "Left"),   ok(0x22), 40))
    S.append(("l1_bow_st",  clear_push_stairs_policy,                     lambda emu, s: s.hearts > 0 and s.mode == 9, 30))
    S.append(("l1_bow",     lambda nav: cellar_item_policy(nav, 0x65A),
              lambda emu, s: s.hearts > 0 and emu.byte(0x65A) == 1 and s.room == 0x22 and s.mode == 5, 30))
    S.append(("l1_b23",     lambda nav: make_cross_policy(nav, "Right"),  ok(0x23), 30))
    S.append(("l1_b33",     lambda nav: make_cross_policy(nav, "Down"),   ok(0x33), 30))
    S.append(("l1_b43",     lambda nav: make_cross_policy(nav, "Down"),   ok(0x43), 30))
    # reach the boomerang room through its locked west door rather than bombing up from 54
    S.append(("l1_44",      lambda nav: make_cross_policy(nav, "Right"),  ok(0x44), 40))
    # The boomerang in here was fought for and never thrown once in the whole run. Walk on through.
    S.append(("l1_45",      lambda nav: make_cross_policy(nav, "Right"),  ok(0x45), 40))
    S.append(("l1_45_key",  lambda nav: make_clear_grab_policy(nav, "Up"),   ok(0x35), 60))
    S.append(("aquamentus", lambda nav: make_lafight_policy(nav, None),
              lambda emu, s: s.hearts > 0 and s.room == 0x35 and not read_enemies(emu), 60))
    S.append(("L1_done",    lambda nav: triforce_policy(nav, 0x01, "Right"),
              lambda emu, s: bool(emu.byte(0x671) & 0x01), 12))
    # --- the White Sword: five heart containers in hand, so the cave at K-1 will hand it over
    S.append(("warp_L1", warp_policy, lambda emu, s: s.mode == 5 and s.level == 0, 4))
    for d, room in zip(L1_TO_WS_DIRS, L1_TO_WS_ROOMS):
        S.append((f"ws_{room:02x}",) + cross(d, room))
    S.append(("white_sword", lambda nav: cave_item_policy(nav, 0x657),
              lambda emu, s: s.sword >= 2 and s.mode == 5 and s.level == 0 and s.hearts > 0, 60))
    # --- back down to Level 4: retrace the White Sword walk, then south and west to the raft
    # dock at F-6 (room 0x55), which sails Link to the island at F-5 (room 0x45).
    # the path doubles back through 1A, so number the screens instead of naming them by room
    for i, (d, room) in enumerate(zip(WS_TO_L4_DIRS, WS_TO_L4_ROOMS)):
        S.append((f"l4w{i:02d}_{room:02x}",) + cross(d, room, 40))
    S.append(("l4_sail", dock_policy, lambda emu, s: s.room == 0x45 and s.mode == 5 and s.hearts > 0, 20))
    S.append(("enter_L4", lambda nav: enter_level_policy(nav, 4),
              lambda emu, s: s.level == 4 and s.mode == 5 and s.hearts > 0, 20))
    # --- Level 4, first half: three keys, then the block puzzle in 32 and the LADDER cellar.
    # Route and door types in knowledge/route_level4.md. Keys 70, 51, 40; locks 30->31, 30->20.
    S.append(("l4_70",      lambda nav: make_cross_policy(nav, "Left"),        ok(0x70), 40))
    S.append(("l4_70_key",  lambda nav: make_clear_grab_policy(nav, "Right"),  ok(0x71, keys=1), 60))
    S.append(("l4_61",      lambda nav: make_cross_policy(nav, "Up"),          ok(0x61), 40))
    S.append(("l4_51",      lambda nav: make_cross_policy(nav, "Up"),          ok(0x51), 50))
    S.append(("l4_51_key",  lambda nav: make_clear_grab_policy(nav, "Left"),   ok(0x50, keys=2), 60))
    S.append(("l4_40",      lambda nav: make_cross_policy(nav, "Up"),          ok(0x40), 50))
    # 40's key lies on the floor (ROM: not an after-clear item). Grab it and go - clearing five Zols in the
    # dark first cost 1,579 frames and was the owner's "stuck in the dark room for nearly 30 seconds".
    S.append(("l4_40_key",  lambda nav: make_grab_policy(nav, "Up"),           ok_gain(0x30, keys=1), 60))
    S.append(("l4_31",      lambda nav: make_cross_policy(nav, "Right"),       ok(0x31), 50))
    # Room 0x32 decides whether the rest of Level 4 is playable. make_clear_policy trades damage
    # freely, and sixty searched attempts from 3.5 hearts never came out with more than ONE -
    # after which Link cannot cross a room at all (the damage-aware planner refuses to walk past
    # anything, and five rooms later he died 26 times in 40 attempts). Its neighbours that do
    # survive at low health use the lookahead fighter, which scores the damage it takes during
    # its rollouts, so use that here: fewer frames spent is worth nothing if it costs the dungeon.
    S.append(("l4_32",      lambda nav: make_lafight_policy(nav, "Right"),     ok(0x32), 60))
    S.append(("l4_lad_st",  clear_push_stairs_policy,
              lambda emu, s: s.hearts > 0 and s.mode == 9, 40))
    S.append(("l4_ladder",  lambda nav: cellar_item_policy(nav, ram.LADDER),
              lambda emu, s: s.hearts > 0 and emu.byte(ram.LADDER) == 1 and s.room == 0x32 and s.mode == 5, 30))
    # --- Level 4, second half, bombless. The walkthrough blasts 21->11->01, but the ROM door
    # table gives a way round with no bombs at all: 30 -> 20 -> 10 -> 00 -> 01 -> 02 -> 12 -> 13.
    # Three keys collected, three locks used (30 east for the ladder, 30 north, 00 east). Exact.
    # Rooms 10, 00 and 12 have shutter doors, so everything in them has to die.
    S.append(("l4_b31",     lambda nav: make_cross_policy(nav, "Left"),        ok(0x31), 40))
    # Crossing 0x31 westward defeated the navigator at low health: 34 of 40 attempts ended "gave up
    # reaching the Left door" with only three deaths, because nav.go refuses to path through enemies
    # when a single hit would kill Link. The damage-aware planner handles exactly this case two rooms
    # later in 0x12, so use it here too - it walks the gaps instead of declaring the room impassable.
    S.append(("l4_b30",     lambda nav: make_lareach_policy(nav, Goal(32, 141, 6), then_exit="Left"),
              ok(0x30), 40))
    S.append(("l4_20",      lambda nav: make_cross_policy(nav, "Up"),          ok(0x20), 50))
    S.append(("l4_10",      lambda nav: make_cross_policy(nav, "Up"),          ok(0x10), 50))
    # room 10 is MANHANDLA, which the walkthrough skips by bombing round it. With no bombs the
    # run has to go through it: the plain fighter died every attempt, the lookahead planner kills
    # it with the White Sword every attempt for about one heart.
    S.append(("l4_00",      lambda nav: make_lafight_policy(nav, "Up"),        ok(0x00), 40))
    S.append(("l4_01",      lambda nav: make_cross_policy(nav, "Right"),       ok(0x01), 40))
    # 01's floor key is the one Level 5 starts on, so take it on purpose rather than by luck.
    S.append(("l4_02",      lambda nav: make_grab_policy(nav, "Right"),        ok_gain(0x02, keys=1), 50))
    # room 02 is six blade traps. The navigator died crossing it every time at 2.5 hearts; the
    # damage-aware planner walks it untouched, so reach the south door with that instead.
    S.append(("l4_12",      lambda nav: make_lareach_policy(nav, Goal(120, 189, 6), then_exit="Down"),
              ok(0x12), 40))
    S.append(("l4_13",      lambda nav: make_lafight_policy(nav, "Right"),     ok(0x13), 80))
    S.append(("gleeok",     gleeok_policy,
              lambda emu, s: s.hearts > 0 and s.room == 0x13 and (emu.byte(0x34D) != 0 or not read_enemies(emu)), 80))
    S.append(("l4_heart",   lambda nav: make_grab_policy(nav, None),
              lambda emu, s: s.hearts > 0 and s.room == 0x13 and read_room_item(emu) is None, 30))
    S.append(("L4_done",    lambda nav: triforce_policy(nav, 0x08, "Up"),
              lambda emu, s: bool(emu.byte(0x671) & 0x08), 12))
    # --- to Level 2 (the Moon) at M5 = room 0x3C. Raft off the island, east along row 5, then
    # north: 3C is walled on three sides and is only entered from 4C below it.
    S.append(("warp_L4", warp_policy, lambda emu, s: s.mode == 5 and s.level == 0, 4))
    S.append(("l2_sail", dock_policy, lambda emu, s: s.room == 0x55 and s.mode == 5 and s.hearts > 0, 20))
    for i, (d, room) in enumerate(zip(L4_TO_L2_DIRS, L4_TO_L2_ROOMS)):
        S.append((f"l2w{i:02d}_{room:02x}",) + cross(d, room, 40))
    S.append(("enter_L2", lambda nav: enter_level_policy(nav, 2),
              lambda emu, s: s.level == 2 and s.mode == 5 and s.hearts > 0, 20))
    # --- Level 2 (the Moon). From the ROM: a straight climb up column E with no locked doors at
    # all on the main line, just shutters. Rooms 2E, 1E and 0E have to be cleared to open them.
    # The detour east from 3E is for BOMBS, which Dodongo cannot be killed without.
    S.append(("l2_6d",      lambda nav: make_cross_policy(nav, "Up"),      ok(0x6D), 40))
    S.append(("l2_6e",      lambda nav: make_cross_policy(nav, "Right"),   ok(0x6E), 40))
    S.append(("l2_5e",      lambda nav: make_cross_policy(nav, "Up"),      ok(0x5E), 50))
    S.append(("l2_4e",      lambda nav: make_cross_policy(nav, "Up"),      ok(0x4E), 50))
    S.append(("l2_3e",      lambda nav: make_cross_policy(nav, "Up"),      ok(0x3E), 50))
    S.append(("l2_3f",      lambda nav: make_cross_policy(nav, "Right"),   ok(0x3F), 50))
    S.append(("l2_bombs",   lambda nav: make_grab_policy(nav, "Left"),
              lambda emu, s: s.room == 0x3E and s.mode == 5 and s.hearts > 0 and s.bombs > 0, 60))
    S.append(("l2_2e",      lambda nav: make_cross_policy(nav, "Up"),      ok(0x2E), 50))
    S.append(("l2_1e",      lambda nav: make_lafight_policy(nav, "Up"),    ok(0x1E), 60))
    S.append(("l2_0e",      lambda nav: make_lafight_policy(nav, "Up"),    ok(0x0E), 60))
    S.append(("dodongo",    dodongo_policy,
              lambda emu, s: s.hearts > 0 and s.room == 0x0E and not read_enemies(emu), 60))
    S.append(("L2_done",    lambda nav: triforce_policy(nav, 0x02, "Left"),
              lambda emu, s: bool(emu.byte(0x671) & 0x02), 12))
    # --- to Level 5 (L8 = room 0x0B) through the LOST HILLS. Level 6 at C6 = 0x22 is sealed off:
    # the whole north-west block has no walkable way in from the south or east, and the underground
    # passages that reach it are hidden behind a bomb or a candle the run does not have yet.
    # Level 5 is reachable now and holds the WHISTLE, which is what opens Level 7.
    # The Lost Hills: from 0x1B, north loops back to 0x1B twice and the third north breaks out.
    S.append(("warp_L2", warp_policy, lambda emu, s: s.mode == 5 and s.level == 0, 4))
    for i, (d, room) in enumerate(zip(L2_TO_HILLS_DIRS, L2_TO_HILLS_ROOMS)):
        S.append((f"l5w{i:02d}_{room:02x}",) + cross(d, room, 40))
        # Secret rupee caves the route walks straight through (Zelda Dungeon wiki list, each one
        # probed before it went in). The owner's rule: never farm - the caves hold 550 rupees.
        if room == 0x3D:
            S.append(("cave_3d", lambda nav: secret_cave_policy(nav, (144, 109), "Down", "push", want=30),
                      lambda emu, s: (s.hearts > 0 and s.room == 0x3D and s.level == 0 and s.mode == 5
                                      and emu.byte(0x66D) >= 75), 30))
        if room == 0x2D:
            # THE 100-RUPEE CAVE on 0x0F - no item needed, and none of the way there is visible to
            # the navigator (six probes to find it):
            #   leave 0x2D upward at column 120 (the default column lands in a dead-end pocket on
            #   0x1D), go right twice to 0x1F, then HOLD UP at x=128 through rock the tile map calls
            #   solid; the staircase is already drawn at (128,125). Then all the way back to 0x2D,
            #   where the route carries on west. The gift counts up one rupee at a time.
            S.append(("c0f_1d", lambda nav: make_cross_at_policy(nav, "Up", at=120), ok(0x1D), 30))
            S.append(("c0f_1e",) + cross("Right", 0x1E, 30))
            S.append(("c0f_1f",) + cross("Right", 0x1F, 30))
            S.append(("c0f_0f", lambda nav: hold_through_policy(nav, 128, "Up", 0x0F), ok(0x0F), 30))
            S.append(("cave_0f", lambda nav: secret_cave_policy(nav, None, "Up", "walk", want=100),
                      lambda emu, s: (s.hearts > 0 and s.room == 0x0F and s.level == 0 and s.mode == 5
                                      and emu.byte(0x66D) >= 150), 30))
            S.append(("c0f_b1f", lambda nav: hold_through_policy(nav, 128, "Down", 0x1F), ok(0x1F), 30))
            S.append(("c0f_b1e",) + cross("Left", 0x1E, 30))
            S.append(("c0f_b1d",) + cross("Left", 0x1D, 30))
            S.append(("c0f_b2d", lambda nav: make_cross_at_policy(nav, "Down", at=120), ok(0x2D), 30))
    # FOUR norths, not three: the hills send Link back to 0x1B three times and break out on the
    # fourth. (A probe suggested three, but that savestate had already walked one north.)
    S.append(("hills_1", lambda nav: make_cross_policy(nav, "Up"), ok(0x1B), 30))
    S.append(("hills_2", lambda nav: make_cross_policy(nav, "Up"), ok(0x1B), 30))
    S.append(("hills_3", lambda nav: make_cross_policy(nav, "Up"), ok(0x1B), 30))
    S.append(("hills_4", lambda nav: make_cross_policy(nav, "Up"), ok(0x0B), 30))
    S.append(("enter_L5", lambda nav: enter_level_policy(nav, 5),
              lambda emu, s: s.level == 5 and s.mode == 5 and s.hearts > 0, 20))
    # --- Level 5 (the Lizard), route from the ROM. Keys at 77, 66, 47, 27, 26; three locked
    # doors (56 north, 27 west, 25 west). The WHISTLE is in 57 and is what Level 7 needs - and
    # what shrinks Digdogger, the boss sitting in front of the heart container in 24.
    S.append(("l5_66",      lambda nav: make_cross_policy(nav, "Up"),      ok(0x66), 50))
    # 66's key is a FLOOR key: take it (the first locked door is on the far side of the passage). The old
    # route also went east for 77's key (1,720 frames), up to 56 and 57 and back (exploration residue) and
    # cleared 65 on principle - none of it needed. Both walls are dashed with the damage-aware planner:
    # Gibdos and Blue Darknuts hit for two hearts and bomb_policy stands still for the fuse.
    S.append(("l5_66_key",  lambda nav: make_grab_policy(nav, None),
              lambda emu, s: s.hearts > 0 and s.room == 0x66 and s.mode == 5 and s.keys >= started().keys + 1, 60))
    S.append(("l5_65",      lambda nav: dash_bomb_policy(nav, "Left", 0x65),   ok(0x65), 50))
    S.append(("l5_64",      lambda nav: dash_bomb_policy(nav, "Left", 0x64),   ok(0x64), 50))
    S.append(("l5_rec_st",  clear_push_stairs_policy,
              lambda emu, s: s.hearts > 0 and s.mode == 9, 40))
    # That staircase is a PASSAGE, not an item room: it surfaces at 06, which has two locked
    # doors. The west one opens on six more Blue Darknuts and the lone block the guides mention;
    # under that block are the stairs that actually hold the recorder.
    S.append(("l5_passage", passage_policy,
              lambda emu, s: s.hearts > 0 and s.room == 0x06 and s.level == 5, 20))
    S.append(("l5_05",      lambda nav: make_cross_policy(nav, "Left"),    ok(0x05), 40))
    S.append(("l5_rec_st2", clear_push_stairs_policy,
              lambda emu, s: s.hearts > 0 and s.mode == 9, 40))
    S.append(("l5_recorder", lambda nav: cellar_item_policy(nav, ram.WHISTLE),
              lambda emu, s: s.hearts > 0 and emu.byte(ram.WHISTLE) == 1 and s.room == 0x05
                             and s.mode == 5, 30))
    # Back out through the passage and up the east side to Digdogger. The door table offers
    # 56 -> 46 -> 47, but 46 is the moat room whose east door cannot be reached from its south
    # door, so go 56 -> 57 -> 47 instead.
    S.append(("l5_b06",     lambda nav: make_cross_policy(nav, "Right"),   ok(0x06), 40))
    S.append(("l5_back_st", clear_push_stairs_policy,
              lambda emu, s: s.hearts > 0 and s.mode == 9, 40))
    S.append(("l5_back",    passage_policy,
              lambda emu, s: s.hearts > 0 and s.room == 0x64 and s.level == 5, 20))
    S.append(("l5_b65",     lambda nav: make_cross_policy(nav, "Right"),   ok(0x65), 40))
    S.append(("l5_b66",     lambda nav: make_cross_policy(nav, "Right"),   ok(0x66), 40))
    # Coming back through, 66 has repopulated with three Blue Darknuts and its north shutter is
    # shut again, so this is a fight now, not a walk.
    S.append(("l5_c56",     lambda nav: make_lafight_policy(nav, "Up"),    ok(0x56), 60))
    S.append(("l5_c57",     lambda nav: make_cross_policy(nav, "Right"),   ok(0x57), 40))
    S.append(("l5_47b",     lambda nav: make_cross_policy(nav, "Up"),      ok(0x47), 50))
    S.append(("l5_47_key",  lambda nav: make_clear_grab_policy(nav, "Up"), ok_gain(0x37, keys=1), 60))
    S.append(("l5_27",      lambda nav: make_cross_policy(nav, "Up"),      ok(0x27), 50))
    S.append(("l5_27_key",  lambda nav: make_grab_policy(nav, "Left"),
              lambda emu, s: s.room == 0x26 and s.mode == 5 and s.hearts > 0 and s.keys >= started().keys, 50))
    S.append(("l5_26_key",  lambda nav: make_clear_grab_policy(nav, "Left"), ok_gain(0x25, keys=1), 60))
    S.append(("l5_24",      lambda nav: make_cross_policy(nav, "Left"),    ok(0x24), 50))
    # "no enemies left" has to ignore projectiles (types 0x50+): Digdogger's death leaves a
    # couple in flight, and counting those as living enemies threw away a won fight.
    S.append(("digdogger",  digdogger_policy,
              lambda emu, s: s.hearts > 0 and s.room == 0x24 and cleared(emu, s), 60))
    S.append(("l5_heart",   lambda nav: make_grab_policy(nav, None),
              lambda emu, s: s.hearts > 0 and s.room == 0x24 and read_room_item(emu) is None, 30))
    S.append(("L5_done",    lambda nav: triforce_policy(nav, 0x10, "Up"),
              lambda emu, s: bool(emu.byte(0x671) & 0x10), 12))
    # --- to Level 7 (C4 = room 0x42). Its entrance is under a pond that only drains when the
    # RECORDER is played on that screen, which is what Level 5 was really for.
    S.append(("warp_L5", warp_policy, lambda emu, s: s.mode == 5 and s.level == 0, 4))
    # THE WHIRLWIND TO THE SHOPS. Link owns the recorder now, and the wind stops at every finished dungeon.
    # Level 4's island door (0x45) is the raft ride and four screens from the arrows shop; Level 5's door
    # is seventeen screens from it on foot. The counter ($523) sits on Level 1: two notes facing Left move it
    # to Level 5 and then Level 4, one ride. Probe: ~1,900 frames door to shop screen, against ~5,900.
    S.append(("sw_w45", lambda nav: whirl_to_policy(nav, 0x45),
              lambda emu, s: s.room == 0x45 and s.level == 0 and s.mode == 5 and s.hearts > 0, 30))
    S.append(("sw_sail", dock_policy, lambda emu, s: s.room == 0x55 and s.mode == 5 and s.hearts > 0, 20))
    S.append(("sw_land", lambda nav: settle_policy(nav, lambda q: q.y >= 125 and q.mode == 5),
              lambda emu, s: s.room == 0x55 and s.mode == 5 and s.y >= 125 and s.hearts > 0, 10))
    S.append(("sw_shore", lambda nav: make_lareach_policy(nav, Goal(160, 173, 8)),
              lambda emu, s: s.room == 0x55 and s.mode == 5 and s.y >= 157 and s.hearts > 0, 40))
    S.append(("sw_65",) + cross("Down", 0x65, 40))
    S.append(("sw_64",) + cross("Left", 0x64, 40))
    # --- SHOPPING ON THE WAY WEST. The arrows shop (0x44) is two screens north of this one and the
    # graveyard that sells monster bait (0x34) is one more. Gohma in Level 6 needs the arrows and the
    # Goriya in Level 7 needs the bait, and the caves already paid for both (140 rupees). The old route
    # shopped from INSIDE Level 6 instead - out, across the map, back, and the same eight rooms climbed
    # twice - which is what the owner saw in the video as going "in and out of level 6 a lot".
    S.append(("sh7_54",) + cross("Up", 0x54, 40))
    S.append(("sh7_44",) + cross("Up", 0x44, 40))
    S.append(("buy_arrows", lambda nav: shop_policy(nav, ram.ARROWS),
              lambda emu, s: s.hearts > 0 and emu.byte(ram.ARROWS) > 0, 25))
    S.append(("shop_leave", lambda nav: cave_exit_policy(nav),
              lambda emu, s: s.mode == 5 and s.level == 0 and s.hearts > 0, 20))
    S.append(("bait_34",) + cross("Up", 0x34, 40))
    S.append(("buy_food", lambda nav: grave_shop_policy(nav, ram.BAIT),
              lambda emu, s: s.hearts > 0 and emu.byte(ram.BAIT) > 0, 25))
    S.append(("food_leave", lambda nav: cave_exit_policy(nav),
              lambda emu, s: s.mode == 5 and s.level == 0 and s.hearts > 0, 20))
    S.append(("bait_44",) + cross("Down", 0x44, 40))
    # and back to the road west: 54, then along 53 and 52 (the old bait expedition's way back) to 62.
    S.append(("fw7_54",) + cross("Down", 0x54, 40))
    S.append(("fw7_53",) + cross("Left", 0x53, 40))
    S.append(("fw7_52",) + cross("Left", 0x52, 40))
    # Room 42 is a pond but NOT the one: the recorder summons a whirlwind there instead of
    # draining it. The whole west of the map is reached through the LOST WOODS, a maze screen at
    # 0x61 that loops until you walk north, west, south, west. Level 7's empty fairy spring is at
    # 0x32 on the far side, and Level 6 is one screen north of it.
    S.append(("l7_62",   lambda nav: make_cross_policy(nav, "Down"),  ok(0x62), 40))
    S.append(("l7_61",   lambda nav: make_cross_policy(nav, "Left"),  ok(0x61), 40))
    for i, d in enumerate(["Up", "Left", "Down", "Left"]):
        room = 0x61 if i < 3 else 0x60
        S.append((f"woods_{i}", lambda nav, d=d: make_cross_policy(nav, d), ok(room), 30))
    for i, (d, room) in enumerate(zip(["Up", "Up", "Right", "Up", "Right"],
                                      [0x50, 0x40, 0x41, 0x31, 0x32])):
        S.append((f"l7w2{i}_{room:02x}",) + cross(d, room, 40))
    # 32 is not the spring either (no water on it at all), but Level 6's door is one screen
    # north at 0x22, plainly visible. Take Level 6 now and hunt the spring afterwards.
    S.append(("l6_22",   lambda nav: make_cross_policy(nav, "Up"),    ok(0x22), 40))
    S.append(("enter_L6", lambda nav: enter_level_policy(nav, 6),
              lambda emu, s: s.level == 6 and s.mode == 5 and s.hearts > 0, 20))
    # --- Level 6 (the Dragon). Straight up column 8 from the entrance, with a key detour east
    # first. Rooms 58, 38 and 28 have shutters, so everything in them has to die.
    # (No detour east for 7A's key: Link arrives with two from Level 5.)
    S.append(("l6_78",      lambda nav: make_cross_policy(nav, "Left"),    ok(0x78), 50))
    S.append(("l6_68",      lambda nav: make_cross_policy(nav, "Up"),      ok(0x68), 50))
    S.append(("l6_58",      lambda nav: make_cross_policy(nav, "Up"),      ok(0x58), 50))
    S.append(("l6_48",      lambda nav: make_clear_grab_policy(nav, "Up"), ok_gain(0x48, keys=1), 60))
    S.append(("l6_38",      lambda nav: make_cross_policy(nav, "Up"),      ok(0x38), 50))
    S.append(("l6_28",      lambda nav: make_lafight_policy(nav, "Up"),    ok(0x28), 60))
    # FROM 28, BOMB EAST INTO 29. The door table shows 28's east wall and 29's west wall are one bombable
    # wall. The old route went north into a Gleeok mini-boss instead, east through 19, 1A and 1B to an old
    # man's dead end at 0B, all the way back, and south through a locked door - about 7,000 frames - to
    # reach this same room. 28 is a chequerboard of blocks (the standard bombing spot is a block) full of
    # Wizzrobes, so the wall is dashed: probe 3/3 at ~750 frames. 29's key is on the floor.
    S.append(("l6_29",      lambda nav: dash_bomb_policy(nav, "Right", 0x29), ok(0x29), 60))
    S.append(("l6_39",      lambda nav: make_grab_policy(nav, "Down"),     ok_gain(0x39, keys=1), 60))
    # 3A is the end of the line on this side of the map: one door, and once its Wizzrobes and
    # Like Likes are dead the block by the north wall slides aside and uncovers a staircase at
    # (208,93). That passage is the only way into the other half of Level 6 - measured, not
    # guessed: it surfaces in room 1D, two rooms from Gohma.
    S.append(("l6_3a",      lambda nav: make_lafight_policy(nav, "Right"), ok(0x3A), 60))
    S.append(("l6_3a_st",   clear_push_stairs_policy,
              lambda emu, s: s.hearts > 0 and s.mode == 9, 50))
    S.append(("l6_pass",    passage_policy,
              lambda emu, s: s.hearts > 0 and s.room == 0x1D and s.level == 6, 30))
    # 1D's south door is open: cross it (265 frames against 1,166 clearing it first).
    S.append(("l6_1d",      lambda nav: make_cross_policy(nav, "Down"),    ok(0x2D), 60))
    S.append(("l6_2d",      lambda nav: make_clear_grab_policy(nav, "Left"), ok_gain(0x2C, keys=1), 60))
    # 2C is the spike-trap room; north of it, behind the last locked door, is GOHMA. Its shutters
    # close behind Link, so arrive with health: the search ranks attempts by hearts first.
    # 2C's north door is LOCKED, not a shutter: nothing in here has to die. Dash to it (damage-aware -
    # the plain crossing took five hearts from the blade traps and Wizzrobes; Gohma is next door).
    S.append(("l6_2c",      lambda nav: make_lareach_policy(nav, Goal(120, 93, 10), then_exit="Up"), ok(0x1C), 60))
    S.append(("gohma",      gohma_policy,
              lambda emu, s: s.hearts > 0 and s.room == 0x1C and emu.byte(0x34D) != 0, 60))
    S.append(("l6_heart",   lambda nav: make_grab_policy(nav, None),
              lambda emu, s: s.hearts > 0 and s.room == 0x1C and read_room_item(emu) is None, 30))
    S.append(("L6_done",    lambda nav: triforce_policy(nav, 0x20, "Up"),
              lambda emu, s: bool(emu.byte(0x671) & 0x20), 12))
    # --- Level 7. The Triforce warp drops Link at Level 6's own door (0x22), and the pond that
    # hides Level 7 is ten screens away down the west side and out through the Lost Woods.
    S.append(("warp_L6", warp_policy, lambda emu, s: s.mode == 5 and s.level == 0, 4))
    # BY WHIRLWIND. On foot the pond is ten screens from Level 6's door, and the second of them (0x32) is a
    # one-tile staircase with Lynels at the foot of it: four hearts and 1,212 frames in the third run. Level 3's
    # door (0x74) is five quiet screens from the pond - west, north, west, north, north - and the wind's counter
    # sits on Level 4 after the shop trip, so it is ONE note facing Left. The recorder stays in B for the pond.
    S.append(("p7_w74", lambda nav: whirl_to_policy(nav, 0x74),
              lambda emu, s: s.room == 0x74 and s.level == 0 and s.mode == 5 and s.hearts > 0, 30))
    for d, room in zip(["Left", "Up", "Left", "Up", "Up"], [0x73, 0x63, 0x62, 0x52, 0x42]):
        S.append((f"p7_{room:02x}",) + cross(d, room, 40))
    S.append(("l7_drain", pond_policy,
              lambda emu, s: s.hearts > 0 and s.room == 0x42 and stairs_on_screen(emu) is not None, 30))
    # Level 7 is entered ONCE. The bait was bought on the arrows trip, so there is no whirlwind back
    # to Level 6, no farm, no walk across the map for food and no second pond drain.
    S.append(("enter_L7", lambda nav: stairs_entry_policy(nav, 7),
              lambda emu, s: s.level == 7 and s.mode == 5 and s.hearts > 0, 25))
    # --- Level 7 proper. Straight up column 9 from the entrance, bombing the dark room's north
    # wall, then west into 38 and north through the locked door to the hungry Goriya. Everything
    # past him is a single corridor east along the top of the map to a staircase in room 0D, the
    # only join between this half of the dungeon and Aquamentus.
    S.append(("l7_69",  lambda nav: make_lafight_policy(nav, "Up"),   ok(0x69), 60))
    S.append(("l7_59",  lambda nav: bomb_policy(nav, "Up", 0x59),
              lambda emu, s: s.hearts > 0 and s.room == 0x59 and s.level == 7, 40))
    S.append(("l7_49",  lambda nav: make_cross_policy(nav, "Up"),     ok(0x49), 60))
    S.append(("l7_39",  lambda nav: make_lafight_policy(nav, "Up"),   ok(0x39), 60))
    # (No bombing east into 3A for its key: Link arrives with the three keys Level 7 needs, and coming back
    # from 3A is what made 39 repopulate with a Digdogger. West, straight on.)
    S.append(("l7_38",  lambda nav: make_cross_policy(nav, "Left"),   ok(0x38), 60))
    S.append(("l7_28",  lambda nav: make_cross_policy(nav, "Up"),     ok(0x28), 60))
    S.append(("l7_feed", feed_goriya_policy,
              lambda emu, s: s.hearts > 0 and s.room == 0x18 and s.level == 7, 40))
    # 18's east door is LOCKED: it never needed the room cleared (2,653 frames; crossing it, ~450).
    S.append(("l7_19",  lambda nav: make_cross_policy(nav, "Right"),  ok(0x19), 60))
    S.append(("l7_1a",  lambda nav: bomb_policy(nav, "Right", 0x1A),
              lambda emu, s: s.hearts > 0 and s.room == 0x1A and s.level == 7, 40))
    # Room 1A has a staircase standing in the open at (128,141) - no block to push, it is simply
    # there. Down it is the RED CANDLE, Level 7's own item. Link has never owned a candle, which
    # is why Level 8's front door (a burnable bush) and most of Hyrule's secret rupee caves have
    # been shut to this run; the sweeps in knowledge/rupee_caves.md say bombs open none of them.
    S.append(("l7_1a_st", clear_push_stairs_policy,
              lambda emu, s: s.hearts > 0 and s.mode == 9, 40))
    S.append(("l7_candle", lambda nav: cellar_item_policy(nav, ram.CANDLE),
              lambda emu, s: s.hearts > 0 and emu.byte(ram.CANDLE) > 0
                             and s.room == 0x1A and s.mode == 5, 30))
    S.append(("l7d_1b", lambda nav: bomb_policy(nav, "Right", 0x1B),
              lambda emu, s: s.hearts > 0 and s.room == 0x1B and s.level == 7, 40))
    # 1B's east door is locked, not a shutter: cross it (423 frames against 900 clearing six Goriyas).
    S.append(("l7_1c",  lambda nav: make_cross_policy(nav, "Right"),  ok(0x1C), 60))
    # 1C is the second Digdogger of the dungeon (ROM monster byte 0x38 again), and its north
    # shutter only opens when the room is clear - so the recorder has to come out again.
    S.append(("l7_0c",  lambda nav: digdogger_policy(nav, "Up"),       ok(0x0C), 40))
    S.append(("l7_0d",  lambda nav: bomb_policy(nav, "Right", 0x0D),
              lambda emu, s: s.hearts > 0 and s.room == 0x0D and s.level == 7, 20))
    S.append(("l7_0d_st", clear_push_stairs_policy,
              lambda emu, s: s.hearts > 0 and s.mode == 9, 50))
    S.append(("l7_pass", passage_policy,
              lambda emu, s: s.hearts > 0 and s.level == 7 and s.mode == 5 and s.room == 0x29, 30))
    # 29 is a sealed pocket with one bombable wall, and behind it is AQUAMENTUS - the same boss
    # Level 1 opened with, and the same enemy byte in the cartridge. The lookahead planner beat
    # it with the wooden sword back then; Link has the White Sword now.
    S.append(("l7_2a",  lambda nav: bomb_policy(nav, "Right", 0x2A),
              lambda emu, s: s.hearts > 0 and s.room == 0x2A and s.level == 7, 40))
    S.append(("l7_aqua", lambda nav: make_lafight_policy(nav, None),
              lambda emu, s: s.hearts > 0 and s.room == 0x2A and emu.byte(0x34D) != 0, 60))
    S.append(("l7_heart", lambda nav: make_grab_policy(nav, None),
              lambda emu, s: s.hearts > 0 and s.room == 0x2A and read_room_item(emu) is None, 30))
    S.append(("L7_done", lambda nav: triforce_policy(nav, 0x40, "Right"),
              lambda emu, s: bool(emu.byte(0x671) & 0x40), 12))
    # --- Level 8 (the Lion), overworld square N-7 = room 0x6D, behind a bush that only a candle
    # will burn. Link has the Red Candle now, taken out of Level 7. The whirlwind stops at every
    # dungeon he has finished, and Level 2's door at 0x3C is four screens from Level 8's:
    # 3C -Down-> 4C -Right-> 4D -Down-> 5D -Down-> 6D. It will not come while he is standing on
    # the pond screen, though - the recorder drains that one instead - so step off it first.
    S.append(("warp_L7", warp_policy, lambda emu, s: s.mode == 5 and s.level == 0, 4))
    S.append(("w8_52",) + cross("Down", 0x52, 40))
    # (Step off the pond screen first - there the recorder drains the water instead of calling the wind -
    # and ride from 0x52. The second run walked six screens east before riding only because the idea
    # arrived mid-walk.)
    # --- THE WHIRLWIND, NOT THE WALK (switched mid-run at 0x67). Level 8's door (0x6D) is the rest of
    # row 6 plus a loop along the bottom row away on foot. The recorder's wind stops at every finished
    # dungeon, and Level 2's door (0x3C) is four screens from Level 8's: down to 4C, right to 4D, down to
    # 5D, and down into 6D's EAST half at x=192, the half with the burnable bush. probe_single_entries.py
    # chain A: 4,525 frames from the pond into Level 8, against ~8,200 walking. It also skips the
    # 100-rupee tree on 0x6B, which the purse no longer needs (only arrows are left to pay for).
    S.append(("wl8_3c", lambda nav: whirl_to_policy(nav, 0x3C),
              lambda emu, s: s.room == 0x3C and s.level == 0 and s.mode == 5 and s.hearts > 0, 30))
    for d, room in zip(["Down", "Right", "Down"], [0x4C, 0x4D, 0x5D]):
        S.append((f"wl8_{room:02x}",) + cross(d, room, 40))
    S.append(("wl8_6d", lambda nav: make_cross_at_policy(nav, "Down", at=192),
              lambda emu, s: s.hearts > 0 and s.mode == 5 and s.room == 0x6D and s.x >= 176, 40))
    S.append(("enter_L8", lambda nav: burn_entry_policy(nav, (192, 109), "Left", 8),
              lambda emu, s: s.level == 8 and s.mode == 5 and s.hearts > 0, 25))
    # --- Level 8 (the Lion). Entrance room 7E. The cartridge says the boss is a GLEEOK in room
    # 3C with the Triforce above it in 2C, and - like Levels 6 and 7 - that pair sits in a pocket
    # with no door into the rest of the dungeon, so a staircase joins them somewhere. First the
    # keys: there are four of them within three rooms of the front door, and the way north needs
    # three locked doors.
    S.append(("l8_7f",) + cross("Right", 0x7F, 40))
    # 7F's key lies on the floor: grab it (475 frames against 1,383 clearing the room first).
    S.append(("l8_7f_key", lambda nav: make_grab_policy(nav, "Left"), ok_gain(0x7E, keys=1), 50))
    S.append(("l8_6e",  lambda nav: make_cross_policy(nav, "Up"),     ok(0x6E), 50))
    S.append(("l8_5e",  lambda nav: bomb_policy(nav, "Up", 0x5E),
              lambda emu, s: s.hearts > 0 and s.room == 0x5E and s.level == 8, 40))
    S.append(("l8_5e_key", lambda nav: make_clear_grab_policy(nav, "Left"), ok_gain(0x5D, keys=1), 50))
    # 5D's key is on the floor: step in, take it, step back (the third key Level 9 needs). Then NORTH out
    # of 5E: the door table shows 5E's north shutter opens onto 4E, so the old loop west through 5D, 5C and
    # 4D - three rooms and a locked door - was never needed.
    S.append(("l8_5d_key", lambda nav: make_grab_policy(nav, "Right"), ok_gain(0x5E, keys=1), 50))
    S.append(("l8_4e",  lambda nav: make_lafight_policy(nav, "Up"),   ok(0x4E), 50))
    S.append(("l8_3e",) + cross("Up", 0x3E, 50))
    # Straight on east into 3F. 3F has a staircase standing in the open - the join to the wing with the
    # Gleeok and the eighth Triforce - so the rooms above 3E (a bombed wall and a Gohma room with
    # shutters) are never needed. The first run went up there, came back down, walked out of the
    # dungeon for money and climbed all of this again; the money is taken on the walk in now.
    S.append(("r8_3f",  lambda nav: make_lafight_policy(nav, "Right"), ok(0x3F), 50))
    S.append(("r8_3f_bombs", lambda nav: make_clear_grab_policy(nav, None),
              lambda emu, s: (s.hearts > 0 and s.room == 0x3F
                             and s.bombs >= min(emu.byte(0x67C), started().bombs + 4)), 50))
    S.append(("r8_3f_st", clear_push_stairs_policy,
              lambda emu, s: s.hearts > 0 and s.mode == 9, 40))
    S.append(("r8_pass", passage_policy,
              lambda emu, s: s.hearts > 0 and s.level == 8 and s.mode == 5 and s.room == 0x4C, 30))
    # The passage surfaces in 4C among eight Pols Voices - and 4C's NORTH wall is the Gleeok room's south
    # wall, bombable from either side (ROM). Dash to it with the damage-aware planner, bomb it, keep dodging
    # while the fuse burns: ~810 frames with no damage, 4 of 4 in the probe. The old route shot all eight,
    # crossed 4B and 3B and bombed in from the west: 4,121 frames.
    S.append(("l8_3c",  lambda nav: dash_bomb_policy(nav, "Up", 0x3C),
              lambda emu, s: s.hearts > 0 and s.room == 0x3C and s.level == 8, 50))
    # A 40,000-frame budget means every FAILED attempt costs forty thousand frames of lookahead -
    # ninety minutes of wall clock for a fight that succeeds in 1,631 frames. Ten thousand is
    # ample and the search gets through six times as many tries.
    S.append(("l8_gleeok", lambda nav: gleeok_policy(nav, budget=10000),
              lambda emu, s: s.hearts > 0 and s.room == 0x3C and emu.byte(0x34D) != 0, 12))
    S.append(("l8_heart", lambda nav: make_grab_policy(nav, None),
              lambda emu, s: s.hearts > 0 and s.room == 0x3C and read_room_item(emu) is None, 30))
    S.append(("L8_done", lambda nav: triforce_policy(nav, 0x80, "Up"),
              lambda emu, s: bool(emu.byte(0x671) & 0x80), 12))
    # --- Level 9. Its door is a bombable rock on overworld 0x05, up in Death Mountain, and the
    # explorer has never set foot in that whole quadrant - there is no cached route to it from
    # anywhere. What there is: the recorder's whirlwind still stops at every dungeon Link has
    # finished, and Level 5's door at 0x0B sits on Death Mountain's eastern edge. Ride there and
    # explore west. (Step off Level 8's staircase first, or the whirlwind's pickup drops him
    # straight back down it.)
    S.append(("warp_L8", warp_policy, lambda emu, s: s.mode == 5 and s.level == 0, 4))
    S.append(("n9_6c",) + cross("Left", 0x6C, 40))
    # --- EVERYTHING LEVEL 9 NEEDS, FETCHED BEFORE GOING IN. The first run entered Level 9 three times:
    # out again for a heart container and the Magical Sword, back in, out AGAIN to sail across the lake
    # and buy bombs, back in - about 38,000 frames. Now: heart container #12, the Magical Sword (its old
    # man wants twelve), then up Death Mountain once, and the dungeon is played straight through. Bombs
    # are never bought - drops are picked up now, and room 0x16's pile tops Link up inside.
    # Heart container #12: the whirlwind to Level 1's door, three screens to 0x47, burn the tree.
    # (The wind's counter is not known after Level 8, so the first ride learns it; the old man in the
    # cave offers a potion on the left and the container on the right.)
    S.append(("hc_w37", lambda nav: whirl_to_policy(nav, 0x37, counter=0x3C),
              lambda emu, s: s.room == 0x37 and s.level == 0 and s.mode == 5 and s.hearts > 0, 30))
    for d, room in zip(["Right", "Down", "Left"], [0x38, 0x48, 0x47]):
        S.append((f"hc_{room:02x}",) + cross(d, room, 40))
    S.append(("hc_47_heart", lambda nav: hc_cave_policy(nav, (176, 157), "Down", "burn"),
              lambda emu, s: s.containers >= 12 and s.level == 0 and s.mode == 5 and s.hearts > 0, 40))
    # The Magical Sword: the whirlwind to Level 6's door, three screens to the graveyard's corner.
    S.append(("ms_w22", lambda nav: whirl_to_policy(nav, 0x22, counter=0x37),
              lambda emu, s: s.room == 0x22 and s.level == 0 and s.mode == 5 and s.hearts > 0, 30))
    for d, room in zip(["Down", "Left", "Up"], [0x32, 0x31, 0x21]):
        S.append((f"ms_{room:02x}",) + cross(d, room, 40))
    S.append(("ms_sword", grave_sword_policy,
              lambda emu, s: s.sword >= 3 and s.level == 0 and s.mode == 5 and s.hearts > 0, 40))
    # Death Mountain from Level 5's door: west along row 1 to 0x17, up, and west twice to Spectacle
    # Rock - the road the first run's second entry walked (no fairy-pond detour, no 16/15 dead end).
    S.append(("dm9_w0b", lambda nav: whirl_to_policy(nav, 0x0B, counter=0x22),
              lambda emu, s: s.room == 0x0B and s.level == 0 and s.mode == 5 and s.hearts > 0, 30))
    for d, room in zip(["Down", "Left", "Left", "Left", "Left", "Up", "Left", "Left"],
                       [0x1B, 0x1A, 0x19, 0x18, 0x17, 0x07, 0x06, 0x05]):
        S.append((f"dm9_{room:02x}",) + cross(d, room, 40))
    S.append(("enter_L9", lambda nav: bomb_entry_policy(nav, (80, 173), "Up", (80, 157), 9),
              lambda emu, s: s.level == 9 and s.mode == 5 and s.hearts > 0, 40))
    # --- Level 9, once. Room 66 is the old man who lets all-eight-Triforce holders pass - his two flames
    # sit in the object table looking exactly like enemies. North to 56 (a key on the floor), bomb its
    # west wall into 55, the four-bombable-wall hub; the staircase under one of its blocks is the only
    # way into the body of the dungeon.
    S.append(("l9_66",) + cross("Up", 0x66, 40))
    S.append(("l9_56",  lambda nav: make_lafight_policy(nav, "Up"),  ok(0x56), 50))
    S.append(("l9_56_key", lambda nav: make_clear_grab_policy(nav, None),
              lambda emu, s: s.hearts > 0 and s.room == 0x56 and s.keys >= started().keys + 1, 50))
    S.append(("l9_55",  lambda nav: bomb_policy(nav, "Left", 0x55),
              lambda emu, s: s.hearts > 0 and s.room == 0x55 and s.level == 9, 40))
    S.append(("l9_55_st", clear_push_stairs_policy,
              lambda emu, s: s.hearts > 0 and s.mode == 9, 40))
    S.append(("l9_pass", passage_policy,
              lambda emu, s: s.hearts > 0 and s.level == 9 and s.mode == 5 and s.room != 0x55, 30))
    # Surfaced in 14: five LIKE LIKES, nine hit points each - forty-two seconds of sword per attempt and
    # it never finishes. An arrow does ten.
    S.append(("m9_15",  lambda nav: bow_fight_policy(nav, "Right"), ok(0x15), 50))
    S.append(("m9_16",  lambda nav: make_cross_policy(nav, "Right"),  ok(0x16), 50))
    # 0x16's floor item is a pile of four bombs - the only reachable pile before the Silver Arrow walls.
    S.append(("m9_16_bombs", lambda nav: make_clear_grab_policy(nav, None),
              lambda emu, s: (s.hearts > 0 and s.room == 0x16
                              and s.bombs >= min(emu.byte(0x67C), started().bombs + 4)), 50))
    # North through the locked door to the old man ("go to the next room"), bomb his west wall.
    S.append(("s9_06",) + cross("Up", 0x06, 40))
    S.append(("s9_05", lambda nav: open_or_bomb_policy(nav, "Left", 0x05),
              lambda emu, s: s.hearts > 0 and s.room == 0x05 and s.level == 9, 40))
    S.append(("s9_05_st", clear_push_stairs_policy,
              lambda emu, s: s.hearts > 0 and s.mode == 9, 40))
    # Both walkthroughs put the far end of this passage at the bottom of the dungeon. The door table
    # says 0x63 (Zols; locked doors N/S/W). DEDUCED, not walked: if the next segment fails, the
    # search log names the room the passage really came out in.
    S.append(("s9_pass", passage_policy,
              lambda emu, s: s.hearts > 0 and s.level == 9 and s.mode == 5 and s.room != 0x05, 30))
    # (0x53 and the room above it were a wrong deduction: 0x43 is an old man's hint room, not the
    # Silver Arrow. Forty attempts and a bomb went into it. The route now goes west from 0x63, which
    # is also what frees the key that detour used to spend.)
    # 0x43 is NOT the Silver Arrow room. It is an old man's hint room ("PATRA HAS THE MAP"), no
    # blocks at all - the door-graph deduction that put the Wizzrobe room here was wrong, and 40
    # "no stairs appeared" attempts were spent on it. Walk the walkthroughs' route instead:
    # back down to 0x63, west through the locked door to 0x62, west to 0x61 - the Patra room - and
    # STOP there: the Patra gets surveyed with zelda/tactics.py before any strategy is written.
    # The old man's text freezes Link for several hundred frames; moving at once reads as "stuck".
    # 0x53: two Like Likes stand right on the south doorway (plus a Blue Wizzrobe and a Bubble);
    # walking out got Link stuck against them and cost three hearts. One arrow kills a Like Like.
    S.append(("s9_62",) + cross("Left", 0x62, 40))
    S.append(("s9_61",) + cross("Left", 0x61, 40))
    # THE PATRA. Surveyed first (knowledge/level9_route.md): core 0x47 hp 11 plus eight orbiting eyes
    # 0x25 hp 6, and only the sword hurts it - bombs, arrows, boomerang and recorder do nothing, and
    # standing still swinging gets Link killed as the ring sweeps through. The damage-aware lookahead
    # with the sword, validated in the real search from this checkpoint, killed it in 491 frames
    # without taking a hit.
    S.append(("s9_patra", lambda nav: make_lafight_policy(nav, None),
              lambda emu, s: s.hearts > 0 and s.room == 0x61 and emu.byte(0x34D) != 0, 30))
    # "Defeat this Patra and push the leftmost block to reach the staircase."
    S.append(("s9_61_st", clear_push_stairs_policy, lambda emu, s: s.hearts > 0 and s.mode == 9, 40))
    # Where this passage comes out has NOT been walked, and the last deduction on this route was
    # wrong (0x43 was an old man, not the Silver Arrow room). Stop wherever it surfaces and look.
    S.append(("s9_pass3", passage_policy,
              lambda emu, s: s.hearts > 0 and s.level == 9 and s.mode == 5 and s.room != 0x61, 30))
    # WALKED: it surfaces in 0x20, the dungeon's upper-left corner, inside a diamond of eight blocks
    # with three Blue and two Red Wizzrobes about. 0x20 and 0x10 are a sealed two-room pocket with no
    # door to the rest of Level 9. 0x20's only door is a bombable wall north into 0x10 - the
    # walkthroughs' Wizzrobe room, where the middle block on the right hides the Silver Arrow.
    # FIGHT FIRST (2026-09-16, live run): walking to this wall and bombing it with the room alive cost every
    # success 7-10 of 11.5 hearts and left Link at 1.5 for the rest of Level 9. probe_s9_10.py from the same
    # state: fight-first 4/4 at 11.5-12 hearts in 780-918 frames; walk-and-bomb 1.5, died, 1.5, 4.5.
    S.append(("s9_10", lambda nav: fight_then_bomb_policy(nav, "Up", 0x10),
              lambda emu, s: s.hearts > 0 and s.room == 0x10 and s.level == 9, 40))
    S.append(("s9_10_st", clear_push_stairs_policy, lambda emu, s: s.hearts > 0 and s.mode == 9, 40))
    S.append(("s9_silver", lambda nav: cellar_item_policy(nav, 0x659),
              lambda emu, s: s.hearts > 0 and emu.byte(0x659) >= 2 and s.level == 9 and s.mode == 5, 40))
    # --- TOWARD GANON (Zelda Dungeon 10.3 / StrategyWiki; walked stretch by stretch, not deduced).
    # Back down into 0x20, clear its Wizzrobes so the ring of blocks round the staircase will move,
    # and take the passage back to the Patra room 0x61 (verified in the other direction).
    S.append(("g9_20",) + cross("Down", 0x20, 40))
    S.append(("g9_20_st", clear_push_stairs_policy, lambda emu, s: s.hearts > 0 and s.mode == 9, 40))
    S.append(("g9_pass_61", passage_policy,
              lambda emu, s: s.hearts > 0 and s.level == 9 and s.mode == 5 and s.room == 0x61, 30))
    # North three rooms: Like Likes (51), Like Likes and blade traps (41), then 31 - no keys needed.
    S.append(("g9_51",) + cross("Up", 0x51, 40))
    # 0x51 holds SIX Like Likes. The plain crossing got through once in 18 live attempts, in 4,081 frames (a grab
    # pins Link); probe_g9_41.py from the same state: damage-aware dash 2/3 at 1,018 frames, sword 3/3 at
    # 1,207-2,073, plain crossing 1/3. The dash, with the search's 40 tries to cover its misses.
    S.append(("g9_41", lambda nav: make_lareach_policy(nav, Goal(120, 77, 10), then_exit="Up"), ok(0x41), 40))
    S.append(("g9_31",) + cross("Up", 0x31, 40))
    # Bomb 0x31's west wall into 0x30: Wizzrobes, and the staircase is under the LEFT block,
    # beneath a blade trap - trigger the trap, then go for the stairs.
    S.append(("g9_30", lambda nav: fight_then_bomb_policy(nav, "Left", 0x30),
              lambda emu, s: s.hearts > 0 and s.room == 0x30 and s.level == 9, 40))
    S.append(("g9_30_st", clear_push_stairs_policy, lambda emu, s: s.hearts > 0 and s.mode == 9, 40))
    # Where this passage surfaces ("towards the top centre of the dungeon") has NOT been walked:
    # stop there and look before writing the last stretch to the Patra under Ganon.
    S.append(("g9_pass_30", passage_policy,
              lambda emu, s: s.hearts > 0 and s.level == 9 and s.mode == 5 and s.room != 0x30, 30))
    # It surfaced in 0x04 with NO bombs, and 0x04's only way on is a bombable west wall. The drop code
    # says the next kill (cycle 0 -> column 1) of a Red Wizzrobe can drop a bomb: earn one.
    S.append(("g9_04_bomb", bomb_drop_policy, ok(0x04, bombs=1), 40))
    S.append(("g9_03", lambda nav: fight_then_bomb_policy(nav, "Left", 0x03),
              lambda emu, s: s.hearts > 0 and s.room == 0x03 and s.level == 9 and s.mode == 5, 40))
    # 0x03 (VERIFIED by looking): the same diamond of eight blocks around a staircase as 0x20 and 0x04,
    # with Bubbles, Keese and Zols. Its only door is the wall just bombed, so the stairs are the way on.
    S.append(("g9_03_st", clear_push_stairs_policy, lambda emu, s: s.hearts > 0 and s.mode == 9, 40))
    S.append(("g9_pass_03", passage_policy,
              lambda emu, s: s.hearts > 0 and s.level == 9 and s.mode == 5 and s.room != 0x03, 30))
    # Deduced: the passage ends in 0x52, the Patra room directly beneath Ganon (sealed stack 52/42/32).
    # The success test insists on 0x52, so a wrong deduction stops the run here instead of wandering.
    S.append(("g9_52_patra", lambda nav: make_lafight_policy(nav, None),
              lambda emu, s: s.hearts > 0 and s.room == 0x52 and emu.byte(0x34D) != 0, 30))
    S.append(("g9_42",) + cross("Up", 0x42, 40))
    # GANON. Surveyed first (probe_ganon.py from ckpt_fullgame_g9_42): the room is dark for 77 frames,
    # lit at 77, the fight starts at 269; he starts blue with HP $F0. ganon_policy (sword while he is
    # blue, silver arrow the moment he turns brown) won 2 of 6 probe attempts, best 937 frames, no damage.
    # Success is the game's own dying phase reaching $A0 - the Triforce of Power appears.
    S.append(("g9_ganon", ganon_policy,
              lambda emu, s: s.hearts > 0 and s.room == 0x42 and ganon_dead(emu), 20))
    # After Ganon, all four steps validated from his checkpoint by probe_ending.py:
    #   the Triforce of Power (223 frames), north into 0x32, the ending trigger (107), the credits.
    S.append(("g9_power", take_triforce_policy,
              lambda emu, s: s.hearts > 0 and s.room == 0x42 and read_room_item(emu) is None, 20))
    S.append(("g9_32", lambda nav: walk_out_policy(nav, "Up", 0x32),
              lambda emu, s: s.hearts > 0 and s.room == 0x32 and s.mode == 5, 20))
    # ZELDA: sword the guard fires, stand at X $70..$80 / Y $95; GameMode ($12) becomes $13.
    S.append(("g9_zelda", zelda_policy, lambda emu, s: emu.byte(0x12) == 0x13, 20))
    # The ending plays itself out to the Triforce-over-ashes screen (submode 4), which waits for Start.
    # Start there saves and switches to the second quest, so the run ends holding no buttons at all.
    S.append(("g9_credits", credits_policy,
              lambda emu, s: emu.byte(0x12) == 0x13 and emu.byte(0x13) == 4, 3))
    return S


def main():
    args = sys.argv[1:]
    segs = segments()
    names = [s[0] for s in segs]
    with Run("fullgame", log=P) as run:
        run.stamp_segment_list(segs)
        run.allow_legacy = "--allow-legacy" in args
        if "--verify" in args:
            last = run.latest_checkpoint(names)
            if last is None or run.resume(last) is None:
                P("--verify: no checkpoint for this segment list. Refusing: finishing with an empty "
                  "log would overwrite fullgame.inputs.txt with a zero-frame run.")
                return
            run.finish(comment="AI plays The Legend of Zelda. Generated by the harness.")
            return
        start = None
        if "--fresh" in args:
            # A fresh run must start at frame 0. Resuming a checkpoint from the old route would keep
            # its input prefix and skip every segment whose name still matches - and the replay would
            # still say MATCH, because the hybrid log is self-consistent. Refuse instead.
            stale = [p for p in (LOGS_DIR / "checkpoints").glob("fullgame_*.json")]
            if stale and not run.allow_legacy:
                P(f"--fresh: {len(stale)} checkpoints from an earlier run are still in "
                  f"logs/checkpoints. Archive or delete them first (logs/archive/ has a copy).")
                return
            P("--fresh: starting from power-on")
        elif "--from" in args:
            start = args[args.index("--from") + 1]
        else:
            start = run.latest_checkpoint(names)
        skip = set()
        if start:
            if run.resume(start) is None:
                P(f"no checkpoint '{start}'")
                return
            skip = set(run.done)
            P(f"resuming after {len(skip)} segments")
        for name, factory, success, tries in segs:
            if name in skip:
                continue
            run.segment(name, factory, success, tries=tries, max_frames=3000)
        run.finish(comment="AI plays The Legend of Zelda. Generated by the harness.")


if __name__ == "__main__":
    main()
