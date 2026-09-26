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
from .ram import MODE_NORMAL
from . import replay, bk2

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
        self.event_index: list[dict] = []     # filled by watch_events(); see _watch
        self._tracker = None
        self._spans = 0                        # step() calls that advanced more than one frame
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
    # -- event checkpoints -----------------------------------------------
    # A savestate on its own is NOT a resume point. resume() below shows why, and it is
    # the whole ballgame: it loads the state AND restores the input prefix that produced it.
    # Resume from a savestate alone and the continued run's log is a suffix, so
    # replay.verify() from power-on produces a different fingerprint and the run stops being
    # a run. Every checkpoint here is therefore the same record save_checkpoint already
    # writes, with a finer key and a reason - which also inherits the list_hash guard, so an
    # event checkpoint cannot leak across a route change either.
    def watch_events(self) -> None:
        """Checkpoint at every major acquisition, so a later attempt can start from one.

        Detection is zelda.pickups.Tracker - the same pass pickup_scan.py uses, one
        contiguous RAM read per step - so the two can never disagree about what a run picked
        up. Off unless called; a run that never calls it behaves exactly as before.

        Consumables are excluded on purpose. A rupee, a small key or a bomb refill is a
        budget problem, not a change in what is possible, and checkpointing them would mean
        hundreds of 17.9 KB states nobody would resume from.
        """
        from .pickups import Tracker
        if self._tracker is not None:
            return
        self._tracker = Tracker()
        self.main.on_step = self._watch
        self.log(f"watching for major acquisitions; checkpoints named ckpt_{self.name}_ev*")

    def _watch(self, emu: BizHawk, buttons, frames: int, s: State) -> None:
        """Per-step observer. Only acquisitions are checkpointed, never losses."""
        tr = self._tracker
        if frames > 1:
            self._spans += 1
        # Arm on the first frame the game is genuinely in play. At power-on the item bytes
        # are 0xFF and the game clearing them to 0 reads as everything being lost at once;
        # and a run resumed from a checkpoint must not report everything the run already had
        # as newly acquired.
        if not tr.armed and s.mode == MODE_NORMAL:
            tr.arm()
        if not tr.armed:
            return
        for p in tr.acquired(emu.ram, len(emu.inputs)):
            if p.kind in ("consumed", "lost") or "LOST" in p.name:
                continue
            self._checkpoint_event(p, frames, s)

    def _checkpoint_event(self, p, span: int, s: State) -> None:
        n = len(self.event_index) + 1
        slug = "".join(c if c.isalnum() else "_" for c in p.name.lower()).strip("_")[:40]
        key = f"ev{n:02d}_{slug}"
        self.save_checkpoint(key, reason=p.name)
        frame = len(self.main.inputs)
        self.event_index.append({
            "key": key, "name": p.name, "kind": p.kind, "detail": p.detail,
            "frame": frame, "span": span,
            # A multi-frame step() means the change happened somewhere inside the batch, so
            # the frame above is the END of the batch, not the pickup frame. Recorded rather
            # than hidden, because the checkpoint stays valid either way - the savestate and
            # the input prefix agree - but the label is only exact when span == 1.
            "approximate": span > 1,
            "summary": str(s), "hearts": s.hearts, "keys": s.keys, "bombs": s.bombs,
            "rupees": s.rupees, "level": s.level, "room": s.room,
            "list_hash": self.list_hash,
        })
        self._write_event_index()
        self.main.note(f"EVENT {p.name}")
        self.log(f"  [event] {p.name} at frame {frame} -> {key}"
                 + ("  (approximate: the step spanned a batch)" if span > 1 else ""))

    def _write_event_index(self) -> None:
        """Rewritten on every event, so a crashed run still leaves its index behind.

        The index exists to outlive the run, so it is written eagerly rather than in
        finish(). Small: one line per major acquisition.
        """
        from .emulator import ROM, rom_md5
        (LOGS_DIR / f"{self.name}.checkpoints.json").write_text(json.dumps({
            "run": self.name, "list_hash": self.list_hash,
            # Which cartridge these checkpoints belong to. A savestate means nothing without
            # the bytes it was made from - the same reasoning that put the hash check in
            # emulator.py applies here, and it costs one line.
            "cartridge_md5": rom_md5(ROM),
            "events": self.event_index,
        }, indent=1))

    def load_event_index(self) -> list[dict]:
        """A previous run's index, so --from-event can name a key without re-running."""
        p = LOGS_DIR / f"{self.name}.checkpoints.json"
        return json.loads(p.read_text()).get("events", []) if p.exists() else []

    def resume_event(self, key: str) -> State | None:
        """Resume from an event checkpoint by its index key, e.g. ev07_map_for_level_3.

        Identical guarantees to resume(), because it is the same record: the list_hash guard
        and the input-prefix restore both apply unchanged.
        """
        entry = next((e for e in self.event_index if e["key"] == key), None)
        if entry is None:
            self.log(f"no event checkpoint named '{key}' in the index")
            return None
        s = self.resume(key)
        if s is not None:
            self.log(f"  ({entry['name']} was acquired at frame {entry['frame']}"
                     + (", approximate frame" if entry.get("approximate") else "") + ")")
        return s

    def _ckpt_paths(self, name: str):
        return CKPT_DIR / f"{self.name}_{name}.json", f"ckpt_{self.name}_{name}"

    def save_checkpoint(self, name: str, reason: str = "") -> None:
        """Write a resume point: the savestate PLUS the input prefix that produced it.

        `reason` is for the reader - a segment name for a segment checkpoint, the item
        name for an event one. It carries no weight in resume(); the list_hash does.
        """
        meta, state = self._ckpt_paths(name)
        self.main.save(state)
        s = self.main.state()
        meta.write_text(json.dumps({
            "segments": self.done, "frames": len(self.main.inputs), "state": state,
            "list_hash": self.list_hash, "reason": reason,
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
        _look.CAUTION_OVERRIDE[0] = 0.12 if free else None
        # Staged fights: a room of six Darknuts is six searches, one per kill, each starting from the best line
        # found for the kill before. The whole-room search was one draw of sixty; per kill it is sixty draws of
        # each part. Intermediate stages are played into MAIN untrimmed and are not checkpointed (a crash resumes
        # from the segment's start); the last stage is the ordinary segment.
        if SPLIT_FIGHTS[0] and not free:
            self._stages(name, factory, start, blocked0, reset_beliefs)
            start = f"{self.name}_{name}_start"      # the last stage begins where the stages left MAIN
            main.save(start)
        # Four scouts make attempts cheap, and fights vary by a factor of two between attempts: look longer.
        best = parallel_search(self.scouts, self.snavs, start, factory, success, tries=max(tries, MIN_TRIES[0]),
                               max_frames=max_frames, label=name, log=self.log, setup=reset_beliefs)
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
