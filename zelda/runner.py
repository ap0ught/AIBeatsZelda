"""Run manager for the full game.

One master input log grows segment by segment. MAIN plays it forward and never loads a state
except to resume a checkpoint during development; SCOUT searches each segment from a copy of
MAIN's current state. The artifact is always the input log: the final claim is made by replaying
it from power-on in a fresh emulator, so checkpoints cannot launder anything into the run.

  runner = Run("fullgame")
  runner.start()                      # power-on, or resume the last checkpoint
  runner.segment("7c_left", factory, success, tries=20)
  ...
  runner.finish()                     # save log, replay-verify from power-on, export .bk2
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

from .emulator import BizHawk, State, LOGS_DIR, STATES_DIR
from .overworld import Navigator
from .search import random_search, parallel_search
from . import replay, bk2, head

CKPT_DIR = LOGS_DIR / "checkpoints"


# The state MAIN was in when the current segment began. Success tests that must count from the start of
# their own segment ("one more key than Link came in with") read it; runner.segment sets it before the
# search and it stays put while the winner is played into MAIN and trimmed.
SEG_START: State | None = None

# Segments whose damage is about to be refilled: each boss (the Triforce piece behind it restores every
# heart) and everything from the Patra under Ganon to the end. The owner: "he can be more aggressive as you
# fill up on life once you beat the boss."
# Staged fights (see Run._stages). ZELDA_SPLIT=1 turns them on; the per-stage search is smaller because a stage is a
# fraction of the room.
SPLIT_FIGHTS = [bool(int(os.environ.get("ZELDA_SPLIT", "0")))]
MIN_TRIES = [int(os.environ.get("ZELDA_MIN_TRIES", "60"))]         # every segment searches at least this many attempts
STAGE_TRIES = [int(os.environ.get("ZELDA_STAGE_TRIES", "40"))]
STAGE_PATIENCE = [int(os.environ.get("ZELDA_STAGE_PATIENCE", "14"))]

REFILL_SOON = {"manhandla", "aquamentus", "gleeok", "dodongo", "digdogger", "gohma", "l7_aqua", "l8_gleeok",
               "l4_heart", "l5_heart", "l6_heart", "l7_heart", "l8_heart",
               "g9_52_patra", "g9_42", "g9_ganon", "g9_power", "g9_32", "g9_zelda", "g9_credits"}

# Bosses whose behaviour is keyed to the frame counter, so the fight depends on the phase the attempt
# enters in rather than on the quality of the line. For these the four scouts divide the entry window
# between them instead of each rolling their own (search.ENTER_SPREAD), because four independent draws
# out of 90 frames keep landing in the same corner - the note in gleeok_policy records four attempts
# 8 frames apart coming back byte-for-byte identical.
#
# This is REFILL_SOON minus the heart rooms and minus the Ganon coda: those are not phase fights, and
# a segmented entry window there would only throw away a settle value that is doing useful work.
PHASE_LOCKED = {"manhandla", "aquamentus", "gleeok", "dodongo", "digdogger", "gohma", "l7_aqua", "l8_gleeok"}
PHASE_SPREAD = [90]              # frames of entry window, matching the 0-90 gleeok_policy already rolls

# Segments fought at FULL health, because the sword beam only fires at `hearts >= containers` and a
# single lost half-heart there costs the weapon rather than a little time. Empty by default and
# populated per run; "revenge" is the Blue Lynel the owner wants killed with the beam.
NEED_FULL_HEARTS: set[str] = {"revenge"}

# Segments that get a longer search than the patience default, and by how much. The knob is
# PATIENCE, not `tries`, and the difference matters: the stop is
#
#     limit = min(tries, max(patience, patience * FIGHT_PATIENCE * 2.5))    # once the best is >= 500
#
# so with the defaults a segment stops at 35 non-improving attempts whatever its `tries` says - 80
# on 5b_bombs is a number that has never once bound. Raising `tries` there would have changed
# nothing at all, which is why this is a multiplier on patience and not a bigger tries count.
#
# IT IS EMPTY, and it was not. 5b_bombs was given 3x on 2026-10-01 because clearing Level 3's 0x5B
# for the four bombs had spent 24 attempts and 15 minutes, and the owner asked for more budget.
# Measured, 3x bought NOTHING: the run reached attempt 54, the best line was still the 672 frames
# found at attempt 8, and all 46 attempts after it were cut at 672 by cutoff() without beating it.
# 25 extra minutes, zero frames - the same shape as knowledge/rerun_findings.json's "farm43 and
# farm53 ran all 40 attempts for a gain of exactly 0 frames". So it is retracted, the segment is
# below, and the rule for adding a name here is: a measurement, not a feeling about a slow segment.
#
# The knob stays because it is the one that would work if a segment's patience search ever did pay:
# the stop is min(tries, patience-scaled), so raising `tries` on a slow segment is a silent no-op
# and this is the only version of "give it more" that is not.
MORE_SEARCH: dict[str, float] = {}

# Segments that take their FIRST success rather than searching for a faster line. See the note on
# MORE_SEARCH for why 5b_bombs ended up here instead of there.
FIRST_SUCCESS: set[str] = {"5b_bombs"}


class Run:
    def __init__(self, name: str, *, record: bool = False, log=print):
        self.name = name
        self.record = record
        self.log = log
        self.main: BizHawk | None = None
        self.scout: BizHawk | None = None
        self.nav: Navigator | None = None
        self.snav: Navigator | None = None
        self.done: list[str] = []
        self.t0 = time.time()
        CKPT_DIR.mkdir(parents=True, exist_ok=True)

    # -- lifecycle -------------------------------------------------------
    def open(self) -> None:
        self.main = BizHawk(log_name=f"{self.name}_main.log", record=self.name if self.record else None)
        import os
        k = max(1, int(os.environ.get("ZELDA_SCOUTS", "4")))
        self.scouts = [BizHawk(log_name=f"{self.name}_scout{i if i else ''}.log", clean_sram=False)
                       for i in range(k)]
        self.scout = self.scouts[0]
        self.nav = Navigator(self.main)
        self.snavs = [Navigator(e) for e in self.scouts]
        self.snav = self.snavs[0]

    def close(self) -> None:
        for e in list(getattr(self, "scouts", []) or [self.scout]) + [self.main]:
            if e is not None:
                try:
                    e.close()
                except Exception:
                    pass

    list_hash: str = ""          # set by stamp_segment_list(); "" disables the check
    allow_legacy: bool = False   # --allow-legacy: resume checkpoints from an older list anyway

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *exc):
        self.close()

    # -- checkpoints -----------------------------------------------------
    def _ckpt_paths(self, name: str):
        return CKPT_DIR / f"{self.name}_{name}.json", f"ckpt_{self.name}_{name}"

    def save_checkpoint(self, name: str) -> None:
        meta, state = self._ckpt_paths(name)
        self.main.save(state)
        s = self.main.state()
        meta.write_text(json.dumps({
            "segments": self.done, "frames": len(self.main.inputs), "state": state,
            "list_hash": self.list_hash,
            "summary": str(s), "hearts": s.hearts, "keys": s.keys, "bombs": s.bombs,
            "inputs": [",".join(b) for b in self.main.inputs]}))

    def resume(self, name: str) -> State | None:
        """Load a checkpoint into MAIN, restoring the input log prefix that produced it."""
        meta, state = self._ckpt_paths(name)
        if not meta.exists() or not (STATES_DIR / f"{state}.State").exists():
            return None
        d = json.loads(meta.read_text())
        # A checkpoint only belongs to the segment list that produced it. Resuming across a route
        # change silently keeps the old input prefix AND skips every renamed segment, and the result
        # still replays MATCH - a self-consistent hybrid of two different runs. Fail closed.
        if self.list_hash and d.get("list_hash") != self.list_hash and not self.allow_legacy:
            self.log(f"checkpoint '{name}' belongs to a different segment list "
                     f"({d.get('list_hash', 'unstamped')} != {self.list_hash}); refusing to resume")
            return None
        s = self.main.load(state)
        self.main.inputs = [tuple(b for b in l.split(",") if b) for l in d["inputs"]]
        self.done = list(d["segments"])
        # The head's phase is DERIVED from the segment list, so a resumed run picks it up from the
        # checkpoint's own record of what it finished rather than from a flag nobody wrote down.
        head.sync(self.done, self.log)
        head.announce(self.main, self.log)
        self.log(f"resumed checkpoint '{name}': {len(self.main.inputs)} frames, {d['summary']}")
        return s

    def latest_checkpoint(self, names: list[str]) -> str | None:
        for n in reversed(names):
            meta, state = self._ckpt_paths(n)
            if not (meta.exists() and (STATES_DIR / f"{state}.State").exists()):
                continue
            if self.list_hash and not self.allow_legacy:
                try:
                    if json.loads(meta.read_text()).get("list_hash") != self.list_hash:
                        continue          # belongs to an older segment list
                except (OSError, ValueError):
                    continue
            return n
        return None

    def stamp_segment_list(self, segs) -> str:
        """Fingerprint the segment list so checkpoints cannot leak across a route change."""
        # Names and order only - see the note in the commit that introduced this. Including tries or
        # the policy's identity made every routine fix invalidate hours of recorded play.
        blob = "|".join(name for name, _factory, _success, _tries in segs)
        self.list_hash = hashlib.sha1(blob.encode()).hexdigest()[:12]
        return self.list_hash

    # -- staged fights ---------------------------------------------------
    STAGED = ("make_lafight_policy", "make_clear_grab_policy", "clear_push_stairs_policy")

    def _stages(self, name, factory, start, blocked0, reset_beliefs) -> None:
        import copy
        from . import search as _search, lookahead as _look
        from .lookahead import enemy_hp_total, static_slots
        from .overworld import read_enemies
        main = self.main
        pol = factory(self.snav)
        fam = getattr(pol, "__qualname__", "").split(".")[0]
        if fam not in self.STAGED:
            return
        s0 = main.state()
        if not s0.level or s0.mode != 5:
            return
        ignore = static_slots(main)
        n_start = enemy_hp_total(main, None, ignore)[1]
        if n_start < 3:
            return
        room0 = s0.room

        def bonus(emu):
            # where the attempt ends: hits already landed on what is left (a hit is worth ~40 frames of the next
            # stage) and how far Link stands from the nearest of them (~1 frame a pixel)
            s = emu.state()
            ens = [e for e in read_enemies(emu) if _look.killable(e) and e[0] not in ignore]
            hp = sum(e[4] >> 4 for e in ens)
            d = min((abs(e[2] - s.x) + abs(e[3] - s.y) for e in ens), default=0)
            return -20.0 * hp - 0.8 * d

        for k, target in enumerate(range(n_start - 1, 0, -1), 1):
            cur = enemy_hp_total(main, None, ignore)[1]
            if cur <= target:
                continue                       # a bomb took two at once
            sname = f"{name}~k{k}"
            st = f"{self.name}_{sname}_start"
            main.save(st)
            _look.KILL_STAGE[0] = target
            _search.EXTRA_VALUE[0] = bonus

            def ok(emu, s, target=target):
                return (s.hearts > 0 and s.room == room0 and s.mode == 5
                        and getattr(emu, "stage_count", 99) <= target)
            try:
                best = parallel_search(self.scouts, self.snavs, st, factory, ok, tries=STAGE_TRIES[0],
                                       max_frames=1500, label=sname, log=self.log, setup=reset_beliefs,
                                       patience=STAGE_PATIENCE[0])
            finally:
                _look.KILL_STAGE[0] = None
                _search.EXTRA_VALUE[0] = None
                for nav in self.snavs:
                    nav.blocked = copy.deepcopy(blocked0)
            if best is None:
                self.log(f"  stage {sname}: no attempt reached {target} left; finishing the room in one piece")
                return
            for b in best.inputs:
                main.step(b, 1)
            s = main.state()
            self.log(f"[{sname}] {best.frames} frames, hearts {best.hearts} -> {enemy_hp_total(main, None, ignore)[1]} left "
                     f"(total {len(main.inputs)} frames)")
            if s.hearts <= 0 or s.room != room0 or s.mode != 5:
                return

    # -- running segments ------------------------------------------------
    def segment(self, name: str, factory, success, *, tries: int = 40, max_frames: int = 3000,
                checkpoint: bool = True, trim: bool = True) -> State:
        main, scout = self.main, self.scout
        start = f"{self.name}_{name}_start"
        main.save(start)
        s0 = main.state()
        global SEG_START
        SEG_START = s0
        main.note(f"SEGMENT {name}: room {s0.room:02X} level {s0.level}, {s0.hearts} hearts, "
                  f"{s0.keys} keys, {s0.bombs} bombs. Scout searching up to {tries} attempts")
        # Every attempt starts from the same savestate, so it must also start from the same beliefs.
        # The scout's Navigator is shared by all attempts, and a knockback in one of them (an Octorok
        # under Level 4's pier) wrote "Down is blocked" into it: every later attempt then failed to
        # plan at all - 37 of 40 "no path to the Down edge" on a path that plainly exists.
        import copy
        from . import search as _search, lookahead as _look
        blocked0 = copy.deepcopy(self.snav.blocked)

        def reset_beliefs(rec, nav=None):
            (nav or self.snav).blocked = copy.deepcopy(blocked0)

        # Per-segment context: is every heart about to be refilled (a boss, the Triforce behind it)?
        free = name in REFILL_SOON
        _search.HEARTS_FREE[0] = free
        # Per-segment "just get through this one": the first success is the win, no patience search.
        # The same behaviour as ZELDA_JUST_GET_THROUGH, scoped to names, so it can be right about one
        # segment and wrong about the next.
        #
        # 5b_bombs is here on a measurement, and the measurement is a retraction. Given 3x the search
        # budget it reached attempt 54 and the best line was still the 672 frames found at attempt 8,
        # with all 46 attempts after it cut at 672 by cutoff() and beating nothing: 25 minutes for zero
        # frames. The archived run's line for this segment is 633, so even a perfect search was chasing
        # 39 frames - 0.2% of the run - and it demonstrably is not there to be found by drawing more
        # attempts from the same distribution. 793 is what attempt 4 produced and it will do.
        _search.JUST_GET_THROUGH[0] = name in FIRST_SUCCESS
        _look.CAUTION_OVERRIDE[0] = 0.12 if free else None
        # A segment can ask to be fought at full health - because the sword beam only fires at
        # `hearts >= containers`, so one lost half-heart there is the loss of the weapon rather than a
        # cost. That reverses the usual dial: bosses are fought AGGRESSIVELY (0.12) because the
        # Triforce piece behind them refills everything, but a beam fight has to be APPROACHED
        # cautiously, or Link arrives at half a heart with no beam and no way to know it.
        _look.NEED_FULL_HEARTS[0] = name in NEED_FULL_HEARTS
        if _look.NEED_FULL_HEARTS[0]:
            _look.CAUTION_OVERRIDE[0] = 1.0
        # Phase-locked boss: the scouts divide the entry window instead of each rolling their own.
        _search.ENTER_SPREAD[0] = PHASE_SPREAD[0] if name in PHASE_LOCKED else 0
        if name in PHASE_LOCKED:
            self.log(f"  {name} is a phase-locked fight: {len(self.scouts)} scouts split "
                     f"0-{PHASE_SPREAD[0]} frames between them rather than all drawing from it")
        # "Damage is free here" stops being true at zero hearts: a Triforce piece behind the boss
        # means a lost heart costs nothing, but DEATH still ends the attempt, and `died` is what the
        # search sees. So a refill-backed fight gets a floor under its damage price rather than the
        # near-zero one it wants - 0.12 lets the planner tank straight into the fireballs, and the
        # first Gleeok attempts under it died at 2,779 and 3,118 frames with a 6,000 budget, which
        # is a death rate and not a time limit. 0.5 is still a fifth of an unrefilled fight's price,
        # so the tanking behaviour is preserved and the suicide is not.
        if name in PHASE_LOCKED:
            _look.CAUTION_OVERRIDE[0] = 0.5
        # Staged fights: a room of six Darknuts is six searches, one per kill, each starting from the best line
        # found for the kill before. The whole-room search was one draw of sixty; per kill it is sixty draws of
        # each part. Intermediate stages are played into MAIN untrimmed and are not checkpointed (a crash resumes
        # from the segment's start); the last stage is the ordinary segment.
        if SPLIT_FIGHTS[0] and not free:
            self._stages(name, factory, start, blocked0, reset_beliefs)
            start = f"{self.name}_{name}_start"      # the last stage begins where the stages left MAIN
            main.save(start)
        # Four scouts make attempts cheap, and fights vary by a factor of two between attempts: look longer.
        from .search import PATIENCE
        best = parallel_search(self.scouts, self.snavs, start, factory, success, tries=max(tries, MIN_TRIES[0]),
                               max_frames=max_frames, label=name, log=self.log, setup=reset_beliefs,
                               patience=max(1, round(PATIENCE * MORE_SEARCH.get(name, 1.0))))
        for nav in self.snavs:
            nav.blocked = copy.deepcopy(blocked0)
        if best is None:
            main.note(f"SEGMENT {name}: no success in {tries} attempts")
            raise RuntimeError(f"segment {name} failed")
        main.note(f"SEGMENT {name}: best of {tries} = {best.frames} frames, {best.hearts} hearts. Playing it")
        # Play the winner into MAIN and stop the moment the segment is genuinely finished.
        #
        # The scout and MAIN do not always agree about how long a fight takes: the planner branches
        # constantly through in-memory savestates, and replaying only its chosen moves from the start
        # state can win sooner than the live attempt did. Level 4's Gleeok is the clearest case -
        # the search recorded 6,020 frames, and the same inputs replayed here clear the room at
        # frame 2,336, leaving 3,684 frames of Link standing motionless in the finished video.
        # Measuring on MAIN is what counts, because MAIN's inputs are the run.
        #
        # Conservative: three consecutive confirmations four frames apart, because death animations
        # and the enemy table both flicker. Segments whose trailing frames are load-bearing are
        # excluded BY NAME below - stairs descents, passages, item pickups, shops and warps all keep
        # working after their success test first goes true.
        #
        # An earlier version also refused to trim while any item lay on the floor. That sounded
        # careful and was exactly wrong: a boss drops a heart container the moment it dies, so the
        # guard was true for the whole post-fight window - the only part worth trimming - and Gleeok
        # kept all 5,962 of its frames. The item belongs to the NEXT segment, which picks it up.
        from .overworld import read_room_item
        # Segments whose last frames are load-bearing: a staircase descent, a passage, an item
        # fanfare, a shop, a warp or a boss's Triforce all keep working after their success test
        # first goes true, so stopping at "true" would cut them off mid-animation.
        NO_TRIM = ("_st", "pass", "stairs", "cellar", "triforce", "done", "heart", "sword", "item",
                   "power", "zelda", "credits", "warp", "whirl", "sail", "dock", "drain", "shop",
                   "buy", "food", "cave", "bomb", "silver", "candle", "boom", "ladder", "raft",
                   "key", "grab", "recorder", "book", "ring", "map", "arrow", "bait",
                   # The Lost Hills and Lost Woods count SCREEN TRANSITIONS: walk north four
                   # times and the fourth breaks out. Trimming a crossing to the frame its
                   # success test first goes true cuts Link off at the screen edge, and the
                   # sequence then miscounts - hills_1/2/3 were the only trimmed segments in
                   # the run (222, 170 and 123 frames) and hills_4 failed all 30 attempts.
                   "hills", "woods")
        # Drop ids a fight leaves behind for itself to collect (Z_04 DropItemTable): bomb, 5 rupees,
        # rupee, key, clock, heart, fairy. Anything else lying in a room - a heart container, a
        # Triforce piece, a dungeon item - belongs to the segment that comes next.
        MINOR_DROPS = {0x00, 0x0F, 0x18, 0x19, 0x21, 0x22, 0x23}
        keep = len(best.inputs)
        if trim and not any(m in name for m in NO_TRIM):
            hits = 0
            for i, b in enumerate(best.inputs):
                main.step(b, 1)
                if i < 40 or i % 4:
                    continue
                q = main.state()
                # Ordinary drops belong to the segment that earned them - hearts, rupees, bombs,
                # keys, clocks and fairies are picked up by the fight policy itself - so trimming
                # while one lies on the floor throws the pickup away. That is exactly what went
                # wrong on the first attempt at this run: every fight stopped the instant the room
                # cleared, Link reached Level 4 on one heart of five, and l4_32 then killed him
                # sixty attempts running. A boss's heart CONTAINER is the opposite case: the next
                # segment collects it, and blocking on it left Gleeok's 61 seconds of dead air in.
                drop = read_room_item(main)
                if drop is not None and drop[0] in MINOR_DROPS:
                    hits = 0
                    continue
                if q.mode in (5, 9) and success(main, q):
                    hits += 1
                    if hits >= 3:
                        keep = i + 1
                        break
                else:
                    hits = 0
            if keep < len(best.inputs):
                # MAIN stepped only `keep` frames, so its input log already ends here - there is
                # nothing to rewind, and the dropped frames never enter the run.
                main.note(f"SEGMENT {name}: finished at frame {keep} of {best.frames}; "
                          f"dropped {best.frames - keep} frames of dead air")
                self.log(f"  trimmed {best.frames - keep} idle frames off {name}")
        else:
            for b in best.inputs:
                main.step(b, 1)
        s = main.state()
        if not success(main, s):
            raise RuntimeError(f"segment {name}: main diverged from scout ({s})")
        self.done.append(name)
        if checkpoint:
            self.save_checkpoint(name)
        head.sync(self.done, self.log)
        head.announce(main, self.log)
        self.log(f"[{name}] {best.frames} frames, hearts {best.hearts} -> {s} "
                 f"(total {len(main.inputs)} frames, {time.time()-self.t0:.0f}s wall)")
        return s

    # -- finishing -------------------------------------------------------
    def finish(self, comment: str = "", verify: bool = True):
        main = self.main
        final = main.state()
        fp = replay.fingerprint(main)
        inputs = main.save_inputs(self.name)
        main.save(f"{self.name}_end")
        self.log(f"final: {final}")
        self.log(f"frames: {len(main.inputs)}  ({len(main.inputs)/60.0988:.1f}s of game time)")
        # The head is only mentioned when this route has one, and the three cases are worth telling
        # apart: a run that never picked it up, a run that is carrying it (the story is unfinished
        # and finishing here would be a run that walked thirty-one screens to deliver nothing), and
        # a run that put it down.
        if head.TAKE in self.done:
            self.log(f"Gleeok's head: {head.phase_text()}"
                     + (f", on x={head.spot()}" if head.spot() is not None else ""))
        if not verify:
            return final, None
        # Close the playing emulators first. BizHawk flushes the game's battery save to disk when
        # it shuts down, and a SaveRAM file landing while the replay emulator is loading the ROM
        # makes the replay start from a saved game instead of a blank cartridge - which shows up
        # as a bogus "the log does not reproduce the run" failure.
        self.log("closing the emulators so their battery saves cannot leak into the replay...")
        self.close()
        self.main = self.scout = None
        self.log("verifying by replay from power-on in a fresh emulator...")
        s2, fp2 = replay.verify(inputs, fp, log=self.log)
        if fp2 != fp:
            raise RuntimeError("replay mismatch: the input log does not reproduce the run")
        movie = bk2.from_inputs_file(inputs, comment=comment or f"{self.name}: generated by the AI harness.")
        self.log(f"bk2 movie: {movie}")
        return final, movie
