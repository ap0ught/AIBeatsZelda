"""Milestone 3: from power-on, get the sword, walk to Level 3, clear it, take the Triforce.

Several emulators. MAIN plays from power-on and never loads a savestate, so its input log is the
run. The SCOUTS load copies of MAIN's state and search each room for the best inputs (no damage
first, speed second); MAIN then plays the winner. Finally the whole log is replayed in a fresh
emulator and exported as a .bk2.

SCOUT COUNT: ZELDA_SCOUTS, default 4 - the same knob the full route uses (zelda/runner.py). One
thread per scout, attempts handed out by seed. Emulation is socket I/O, so it releases the GIL and
K scouts really do run K attempts in nearly the time of one.
"""
import contextlib
import json
import os
import time

from zelda import BizHawk, ram, bot, replay, bk2
from zelda.overworld import Navigator, NavError, LinkDied, read_enemies, read_room_item
from zelda.combat import Fighter
from zelda.segments import make_cross_policy, make_grab_policy, make_clear_policy, make_lafight_policy, make_lareach_policy
from zelda.lookahead import Goal
from zelda.cellar import take_raft_cellar_la
from zelda.search import parallel_search
from zelda.boss import Manhandla, parts
from zelda.emulator import LOGS_DIR

SCOUTS = max(1, int(os.environ.get("ZELDA_SCOUTS", "4")))

t0 = time.time()
LOG = open(LOGS_DIR / "milestone3.txt", "w", buffering=1)


def P(*a):
    print(*a, flush=True)
    print(*a, file=LOG)


def bomb_policy(nav):
    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        emu.step = rec.step
        nav.jitter = (rng, rng.choice([0.05, 0.15]))
        try:
            rec.step((), rng.randint(0, 20))
            bot.bomb_door(nav, "Right")
            s = nav.exit_screen("Right")
            return "in" if s.room == 0x4D else "odd"
        except (NavError, bot.BotError) as e:
            return "nav: " + str(e)[:40]
        finally:
            emu.step = orig
            nav.jitter = None
    return policy


def boss_policy(nav):
    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        emu.step = rec.step
        try:
            rec.step((), rng.randint(0, 20))
            return "dead" if Manhandla(nav, rng).fight(max_frames=2500) else "alive"
        finally:
            emu.step = orig
    return policy


def cellar_policy(nav):
    def policy(emu, rec, rng, max_frames):
        try:
            rec.step((), rng.randint(0, 30))
            return "raft" if take_raft_cellar_la(emu, rec, rng) else "no raft"
        except (NavError, LinkDied) as e:
            return "fail: " + str(e)[:40]
    return policy


def finish_policy(nav):
    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        emu.step = rec.step
        try:
            for _ in range(8):
                if read_room_item(emu):
                    break
                rec.step((), 15)
            nav.grab_room_item()
            nav.exit_screen("Up")
            it = read_room_item(emu)
            if not it:
                return "no triforce?"
            t, ix, iy = it
            nav.go(lambda x, y: abs(x - ix) <= 8 and abs(y - iy) <= 8, "the Triforce", max_replans=80)
            for _ in range(3):
                if emu.byte(0x671) & 0x04:
                    break
                nav.go(lambda x, y: x == (ix // 8) * 8 and y == ((iy - 5) // 8) * 8 + 5, "the Triforce exactly")
                rec.step((), 4)
            for _ in range(40):
                if emu.state().level == 0:
                    break
                rec.step((), 20)
            return "triforce" if emu.byte(0x671) & 0x04 else "missed"
        except (NavError, LinkDied) as e:
            return "nav: " + str(e)[:40]
        finally:
            emu.step = orig
    return policy


SEGMENTS = [
    # name, policy factory, success(emu, s), tries
    ("7c_left",   lambda nav: make_cross_policy(nav, "Left"),         lambda emu, s: s.room == 0x7B and s.mode == 5 and s.hearts > 0, 20),
    ("7b_key",    lambda nav: make_grab_policy(nav, "Up"),            lambda emu, s: s.room == 0x6B and s.mode == 5 and s.keys >= 1, 40),
    ("6b_up",     lambda nav: make_cross_policy(nav, "Up"),           lambda emu, s: s.room == 0x5B and s.mode == 5 and s.hearts > 0, 40),
    ("5b_bombs",  lambda nav: make_clear_policy(nav, "Up"),           lambda emu, s: s.room == 0x4B and s.mode == 5 and s.bombs > 0, 80),
    ("4b_left",   lambda nav: make_cross_policy(nav, "Left"),         lambda emu, s: s.room == 0x4A and s.mode == 5 and s.hearts > 0, 30),
    ("4a_bombs",  lambda nav: make_clear_policy(nav, "Left"),         lambda emu, s: s.room == 0x49 and s.mode == 5 and s.hearts > 0, 60),
    ("49_key",    lambda nav: make_grab_policy(nav, "Down"),          lambda emu, s: s.room == 0x59 and s.mode == 5 and s.keys >= 1, 40),
    ("59_fight",  lambda nav: make_lafight_policy(nav, "Down"),       lambda emu, s: s.room == 0x69 and s.mode == 5 and s.hearts > 0, 20),
    ("69_stairs", lambda nav: make_lareach_policy(nav, Goal(208, 141, 6), exit_ok=True),
                                                                      lambda emu, s: s.hearts > 0 and s.room == 0x0F and s.mode == 9, 40),
    ("cellar",    cellar_policy,                                      lambda emu, s: s.hearts > 0 and emu.byte(0x660) == 1 and s.room == 0x69 and s.mode == 5, 30),
    ("69_up",     lambda nav: make_lareach_policy(nav, Goal(120, 77, 4), then_exit="Up"),
                                                                      lambda emu, s: s.hearts > 0 and s.room == 0x59 and s.mode == 5, 40),
    ("59_up",     lambda nav: make_cross_policy(nav, "Up"),           lambda emu, s: s.room == 0x49 and s.mode == 5 and s.hearts > 0, 30),
    ("49_right",  lambda nav: make_cross_policy(nav, "Right"),        lambda emu, s: s.room == 0x4A and s.mode == 5 and s.hearts > 0, 30),
    ("4a_right",  lambda nav: make_cross_policy(nav, "Right"),        lambda emu, s: s.room == 0x4B and s.mode == 5 and s.hearts > 0, 30),
    ("4b_right",  lambda nav: make_cross_policy(nav, "Right"),        lambda emu, s: s.room == 0x4C and s.mode == 5 and s.hearts > 0, 40),
    ("4c_bomb",   bomb_policy,                                        lambda emu, s: s.room == 0x4D and s.mode == 5 and s.hearts > 0, 40),
    ("4d_boss",   boss_policy,                                        lambda emu, s: s.room == 0x4D and not parts(emu) and s.hearts > 0, 60),
    ("finish",    finish_policy,                                      lambda emu, s: bool(emu.byte(0x671) & 0x04), 10),
]

ROUTE = ["Left", "Up", "Left", "Left", "Left", "Down", "Right"]

with BizHawk(log_name="m3_main.log", record="milestone3") as main:
    main.note("MILESTONE 3 (with the raft): power-on to the Level 3 Triforce. No bookmarks in this run; a scout emulator searches each room from a copy of this state")
    bot.new_game(main)
    bot.enter_cave_up(main, cave_x=64)
    bot.take_cave_item(main, item_x=120, flag_addr=ram.SWORD)
    bot.exit_cave_down(main)
    nav = Navigator(main)
    OW_ROOMS = [0x76, 0x66, 0x65, 0x64, 0x63, 0x73, 0x74]
    ow_segments = [(f"ow_{r:02x}", (lambda d: (lambda nav: make_cross_policy(nav, d)))(d),
                    (lambda r: (lambda emu, s: s.room == r and s.level == 0 and s.mode == 5 and s.hearts > 0))(r), 30)
                   for d, r in zip(ROUTE, OW_ROOMS)]

    def enter_policy(nav):
        def policy(emu, rec, rng, max_frames):
            orig = emu.step; emu.step = rec.step
            nav.jitter = (rng, rng.choice([0.05, 0.15]))
            try:
                rec.step((), rng.randint(0, 10))
                nav.go(lambda x, y: x == 128 and y == 141, "the spot below the Level 3 entrance")
                emu.wait_until(lambda s: s.level == 3, 300, buttons=("Up",))
                emu.wait_until(lambda s: s.mode == ram.MODE_NORMAL, 400)
                return "in"
            except NavError as e:
                return "nav: " + str(e)[:40]
            finally:
                emu.step = orig; nav.jitter = None
        return policy
    ow_segments.append(("enter_L3", enter_policy, lambda emu, s: s.level == 3 and s.mode == 5 and s.hearts > 0, 20))

    with contextlib.ExitStack() as stack:
        scouts = [stack.enter_context(BizHawk(log_name=f"m3_scout{i or ''}.log", clean_sram=False))
                  for i in range(SCOUTS)]
        snavs = [Navigator(s) for s in scouts]
        P(f"{SCOUTS} scout emulator(s) searching alongside MAIN")
        for name, factory, success, tries in ow_segments + SEGMENTS:
            start = f"m3_{name}_start"
            main.save(start)
            s0 = main.state()
            main.note(f"SEGMENT {name}: room {s0.room:02X}, {s0.hearts} hearts. {SCOUTS} scout(s) searching up to {tries} attempts...")
            best = parallel_search(scouts, snavs, start, factory, success, tries=tries, max_frames=2500,
                                   label=name, log=P)
            if best is None:
                P(f"FAILED: {name}")
                raise SystemExit(1)
            main.note(f"SEGMENT {name}: best of {tries} attempts = {best.frames} frames, {best.hearts} hearts. Playing it")
            for b in best.inputs:
                main.step(b, 1)
            s = main.state()
            if name == "enter_L3":
                P(f"inside Level 3 at frame {s.frame}, hearts {s.hearts} ({time.time()-t0:.0f}s)")
            ok = success(main, s)
            P(f"[{name}] {best.frames} frames, hearts {best.hearts} -> main: {s} ok={ok} ({time.time()-t0:.0f}s)")
            if not ok:
                P("desync between scout and main!")
                raise SystemExit(2)
            (LOGS_DIR / "segments").mkdir(exist_ok=True)
            (LOGS_DIR / "segments" / f"m3_{name}.json").write_text(json.dumps(
                {"frames": best.frames, "hearts": best.hearts, "seed": best.seed, "inputs": [",".join(b) for b in best.inputs]}))

    final = main.state()
    main_raft = main.byte(0x660)
    fp = replay.fingerprint(main)
    inputs = main.save_inputs("milestone3")
    main.save("milestone3_end")
    main.screenshot("m3_end")

P(f"run finished in {time.time()-t0:.0f}s wall")
P(f"final state : {final}  triforce flags {final.triforce:02x}  raft {main_raft}")
P(f"frames      : {final.frame}  ({final.frame/60.0988:.2f}s of game time)")
P("verifying by replay from power-on in a fresh emulator...")
s2, fp2 = replay.verify(inputs, fp, log=P)
assert fp2 == fp and (s2.triforce & 0x04) and main_raft == 1, "replay mismatch"
movie = bk2.from_inputs_file(inputs, comment="Milestone 3 v2: sword, overworld, Level 3 cleared with the raft, Triforce. Generated by the AI harness.")
P(f"bk2 movie   : {movie}")
P("MILESTONE 3 COMPLETE AND VERIFIED")
