
## Where things stand (checked 2026-10-02)

This file is standing goals and operating rules, not a status page. For current state read
`README.md` (how to run and watch one), `FINDINGS.md` §9–§18 (what the last session measured),
`journal/` (49 entries, newest at the end), and `runs/*/VERIFICATION.txt`.

Two verified runs, not one: `runs/run6` is the video's run (37:02, route 4). `runs/gleeok_dragon`
is a from-power-on route-5 run through the dragon, 60,589 frames and 161 segments — read its
VERIFICATION.txt first, because 75 of those segments were taken unpolished under `ACCEPT_AFTER`
and the route itself is wrong one segment past the end.

The DONE entry at the bottom is dated 2026-09-15 and describes route 3 as it stood then. The
segment list has been reorganised since; route 3 is now 351 segments, not 609, and the frame
count it quotes (372,090, corroborated by `knowledge/baseline_milestones.tsv`) has not changed.

## 13. Standing goals added 2026-09-14 (user)

- **Try the inventory.** When something will not die, do not grind the sword at it - run
  `zelda/tactics.py survey()` and let it tell you which item works. Measured examples: Pols Voice
  (the rabbit-eared hoppers) take exactly one ARROW each and the sword gets Link killed; Digdogger
  ignores everything until the RECORDER splits it; Gohma only takes an arrow fired from below.
- **The Magical Sword is a target.** It is the third sword, under a gravestone on overworld room
  0x40 (the graveyard: reach it through the Lost Woods - north, west, south, west - then north
  twice). It needs **12 heart containers**; Link has 10 and Level 8's Gleeok makes 11. Get it as
  soon as the twelfth heart exists.
- **Money is a solved problem now, so stop being poor.** Link owns a candle, and the secret caves
  are almost all burnable. `zelda/secrets.py sweep()` finds a screen's secret by standing on every
  square and trying every item in every direction, off an in-memory snapshot, for no game time.
  Sweep screens on the route and bank what they hold. Known: 100 rupees on 0x6B (burn from
  (128,141) facing Down).
- **Record the struggles.** The failures are the video. Keep making run recordings as milestones
  land, not only at the end.

### Operating the run (learned the hard way, twice)

`run_until.sh` holds `/tmp/zelda_run.lock` and records its own PID inside it. It clears a stale
lock by itself when the holder is gone. **Never `rm -rf` that lock before launching** - doing so
is how two and three runs ended up alive at once, six emulators fighting for the CPU and writing
the same checkpoints, with every search crawling. To stop a run, kill the `run_until.sh` bash
wrapper FIRST (killing python alone just makes the wrapper restart it), then python and EmuHawk.
Two roles are always right, whatever the scout count: MAIN plays the real input log, SCOUTs search
from copies of its checkpoints. One MAIN plus `ZELDA_SCOUTS` (default 4) EmuHawk processes is a normal
run; five is what the watching setup in `README.md` tiles.

### Recording (learned 2026-09-15)

Never run `record_run.py` while a run is active. The first recording of the Magical Sword milestone
died halfway (frame 166,509 of 329,529) with a run going alongside it - three EmuHawk instances -
and the run's SCOUT lost its bridge five times in the same nine minutes. Windows logged no crash for
either process. Retried with nothing else running, the recording finished in about ten minutes.
`render_overlay.py` is not an emulator and can share the machine (about 3,900 frames per minute).

## DONE - 2026-09-15: the game is beaten
Power-on to the ending in one verified input log: **372,090 frames** (1h43m of game time), 609
segments, replay from power-on MATCH, Link finished on 10/13 hearts with the Magical Sword.
Ganon fell to four Magical Sword hits and one Silver Arrow. Remaining work is the video only:
`python record_run.py fullgame` (ALONE - never while a run holds /tmp/zelda_run.lock), then
`python render_overlay.py fullgame`.

*(Written 2026-09-15, when that was true of route 3. Both jobs are since done and the video is
published. The 609 is the segment count of route 3 as it stood that day; route 3 is 351 segments
now and its checkpoints and segment names have changed since. The 372,090 frames still stand -
`knowledge/baseline_milestones.tsv` has it at `g9_credits`.)*
