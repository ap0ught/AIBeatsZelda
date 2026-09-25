
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
Two EmuHawk processes is correct: MAIN plays the real input log, SCOUT searches from copies.

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
