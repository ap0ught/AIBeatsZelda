# 49 - Five windows and a black one

2026-10-02

**Cartridge:** `Legend of Zelda, The (USA) (Rev 1).nes` — md5 `614fb3085826e62f3be3a3fe0b931689`, the
verified dump. Re-hashed while writing this: `md5sum roms/*.nes` returns that value and nothing else, which
is worth stating because §3.3 of FINDINGS is a session that did not get that far.

**Goal.** Make a run watchable *while it is still being searched*, and then work out what the windows were
actually saying. Five emulator windows on a nested X display, tiled; `bridge.lua` grew a `phase` command so
each window says what it is for rather than which room it is in. Both are small changes. What they turned up
is not: watching five searches at once is what produced FINDINGS.md §9–§18, and this entry is the part that
is not in there — the display, the two rules about it that nothing in the tree had written down, and the one
mechanism that made every strange window explainable at once.

## The display

```
Xephyr :1 -screen 1920x1080 -resizeable -ac -nolisten tcp
```

Five windows: one MAIN playing the input log, four scouts searching from copies of its checkpoints.
`ZELDA_SCOUTS` defaults to 4 (`zelda/runner.py:218`), so five is the default mosaic. i3 tiles the workspace;
`~/.config/i3/config` floats anything whose title contains `Legend of Zelda` or `Lua Console`. Two rules,
and neither was written down anywhere before today:

1. **Never resize a BizHawk window.** They draw from the bridge's `step` handler, so a window nobody is
   stepping never repaints and a resize leaves a stale surface. i3 floating them is the mechanism, not a
   preference: layout is done by *moving* windows, never resizing.
2. **They have no WM_CLASS at all**, so a `class=` rule never fires and the rules match on `title=`. The
   `for_window [class=".*"] border none` line in that config sits above the two title rules and *does* match,
   which is misleading — something matched, and it was not the class.

**Neither of these two things is in this repository, and that is the finding.** The i3 config lives at
`~/.config/i3/config` — outside the tree, untracked, and named by no file in `src/`; the Xephyr command line
appears nowhere in the tree at all. FINDINGS.md §11 knows that i3 exists and that it floats the windows, and
that is as far as it goes. So the two facts that make watching a run possible existed only in a file git does
not track, and a fresh clone gets neither. They are now in `README.md` and `SETUP-LINUX.md` for that reason.

## The black window, and what it was actually measuring

`bridge.lua:439-440` is the whole explanation:

```lua
-- Block for commands. Yielding while idle lets the emulator free-run (frames advanced with no
-- input from us and broke replay determinism), so the script holds the main thread instead.
conn:settimeout(nil)
while true do
  local line, e = conn:receive("*l")
```

The bridge blocks on `conn:receive`, so there is no idle frame loop to draw from, and `hud()` is called from
the `step` handler (`bridge.lua:342-343`, with `gui.clearGraphics()` first). **An emulator nobody is stepping
does not repaint at all.** Three separate beliefs collapse into that one line, and FINDINGS §11 is the
correction:

- MAIN's window is black between segments because nothing is stepping it, not because Mono or EGL or the GTK
  driver is failing. It is normal, and it says nothing about the run.
- The "resizing corrupts the surface" theory was never corruption. A resize leaves whatever the surface held
  — black after a state load, yesterday's colours after an hour idle — until the next step.
- The greyscale scout that "healed on the next round trip" was not healing. It was stepping.

The generalisation is worth more than the three cases: **a window that renders nothing shows you nothing, and
in this harness "nothing" is a picture with a shape.** Anything inferred from an idle emulator's pixels was
inferred from a stale buffer.

## What the windows say

`bridge.lua` draws a right-aligned, phase-coloured label on the HUD line: capped at 14 cells
(`rest:sub(1, 14)`), coloured by its *first word* so a numbered or staged label still colours by what it is.

| window | labels | |
|---|---|---|
| scout | `BASELINE #n` | nothing found yet — every attempt still looking for a line (green) |
| | `POLISH #n` | we have a line and are spending attempts trying to beat it (amber) |
| | `S<k>/<m> ` prefix | a staged fight is several searches under one segment name; "S3/5" says which kill |
| | `CONVERGED` `CAPPED` `SEARCHED` `DONE` | the four stop reasons, told apart (grey) |
| MAIN | `REPLAY` `TRIM` `VERIFY` `DONE` | playing the winner in / trimming idle frames / the from-power-on check (blue) |

`CONVERGED`, `CAPPED` and `SEARCHED` are three different decisions that used to print the same line. Why a
search stopped is the most useful single thing about it, and the window is the only place it is visible while
the search is happening.

*FINDINGS.md §11 has a table with three of these rows and no `TRIM` or `VERIFY`, because it was written
2026-10-01, a day before those three arrived. It is a record of the state that day, not of the vocabulary
now; this table is the one to read today.*

**What the label can and cannot do, and the code already argues with itself about it.** `bridge.lua:384-388`
tries to paint on set:

```lua
    -- Draw it now rather than waiting for the next `step`. ... A status light that
    -- only lights up when something else happens is not a status light.
    pcall(function() gui.clearGraphics(); hud() end)
```

That intent is right and it does not work. Measured, in a parked window on a real checkpoint (FINDINGS §11):

| after | phase visible |
|---|---|
| `step 40` (game painted) | no label set yet |
| `phase polish`, zero frames | no |
| `phase done` + `step 0` | no |
| one real frame (`step 1`) | **DONE**, in grey |

So a label is reliable while a search is stepping its window and invisible once it parks — which is also
why MAIN's labels *do* show (MAIN is stepped every frame of the replay) and why `announce()` sends the stop
reason from inside the search rather than after the threads join, while attempts are still in flight
(`zelda/search.py:397-408`).

## The search stopped polishing forever, and started saying so

Three of today's findings are the harness's own stop rules and they are in FINDINGS §9, §13 and §16; what
follows is the evidence that they are running, from a file that is not those findings.

`logs/flagged.json`, read at 14:58Z while a run was live: **24 entries, all from run `gleeok`**, frames 154
to 1813, hearts 2.0 to 3.5. **23 of the 24 stopped at exactly 8 non-improving attempts.** The one that did
not is the interesting one:

```
  white_sword  "took the 1813-frame line after 31 attempts (16 without improvement)"
```

16, not 8, because a segment that has failed before gets one more polish round per failure —
`accept_after=ACCEPT_AFTER[0] + 2 * fails` (`zelda/runner.py:568`). The cap is not a constant in practice.

`ow1_38` is in the same file at **212 frames, 3.5 hearts, after 13 attempts** — the identical number FINDINGS
§16's heart-floor A/B reports as "floor on". That is the same measurement seen twice rather than two
measurements that agree: it is one run, written down once by the search and once by the runner. What it does
establish is that the flag file is being written the way the code says, which is worth more than it sounds,
because a flag file that is silently empty would look exactly like a run with nothing left on the table.

`logs/stuck.json` is empty. Nothing has needed `NeedsBackprop` yet, which means the ledger is not load-bearing
evidence for anything; it is insurance that has not been claimed.

## A scout that dies is replaced

FINDINGS §13: eight scout deaths in one session, a worker thread that used to return from the middle and
leave the slot dead until the process exited. `Run.respawn_scout(k)` (`zelda/runner.py:226`) builds a fresh
`EmuHawk` and `Navigator` *in place* — `parallel_search` holds the same list objects, so it re-binds its
locals and rebuilds the policy that closed over the dead Navigator. Capped at `ZELDA_SCOUT_RESPAWN` (2 per
scout per search), because a respawn waits up to 60 s for a bridge and a dead *display* is four minutes of
hanging. The half nobody could see: a death inside `emu.load()` was outside the error handling entirely, so it
killed the thread outright — no log line, no counter, no replacement.

Watching five windows is what surfaced this. You cannot see four scouts from a log line that says "4 scouts"
when three of the four are dead.

## The swing that could not land

FINDINGS §10: `combat.shield_side` had always known a swing along a knight's facing is stopped by its shield,
and `lookahead.killable` had always known a Darknut is killable. Nobody asked whether *this* swing would land,
so `plan_reach` offered a swing in all four directions whenever anything killable was within 36 px. A swing
into a shield earns no kill credit but still moves Link, and movement is most of what the score is made of.

`lookahead.swing_connects` asks the missing question with the fact that already existed;
`ZELDA_SHIELD_AWARE=0` restores the old one. Four seeds a side on the real room:

| | passes | deaths | sword frames per attempt |
|---|---|---|---|
| blind | 3/4 | 1 | 46, 26, 36, 18 |
| shield-aware | 2/4 | **0** | 0, 2, 0, 0 |
| `transit=True` | 1/4 | 2 | 0 |

`transit=True` — "never offer the sword, just run past them", which is what the route's own caption for that
room says — is the worst of the three: dead at 176 and 323 frames. The caption is an argument about the
route, not about the planner. Eight Darknuts is not a corridor; `transit` deletes the damage term along with
the swing and a Darknut hurts from every side. Kept, with the measurement in the docstring, because it is
right for a leg that is only a journey.

Four seeds cannot rank 2/4 against 3/4. They can rank the deaths and the sword, and those are not close.

## The dragon run, and what it is

`runs/gleeok_dragon/` — route 5 (Gleeok before Level 1), from power-on, **60,589 frames** (16m48s of emulated
time at 60.0988 Hz), **161 segments**, replayed in a fresh emulator to work-RAM SHA-1
`575771d9bd7ca936b157d6c6f5d9ae43aa5e9331`:

```
replayed 60589 frames -> f60589 mode=0b/00 L0 room=0a pos=(120,141) dir=8 hp=6.0/7 rup=48 sword=2 lag=10947
  ram sha1 575771d9bd7ca936b157d6c6f5d9ae43aa5e9331
  MATCH
```

Gleeok dead at f43620 (segment 101/161), the head taken at f43830, delivered at f60589. `inputs.txt` says
`# frames=60589 valid_from_poweron=True`.

One thing in that block that is worth knowing before comparing it with run6's. `replay.verify` prints
`replayed {len(frames)} frames -> {state}`, and run6's file reads `replayed 136526 frames -> f136527` — the state
index is one *past* the frame count. This file reads `replayed 60589 frames -> f60589`, one *level*. The sha1 is
the number to compare in both cases and it is the number `verify()` returns and the code checks; the frame index
in the prose is not load-bearing. I did not chase the difference, and the file's own header says every line in it
came out of the run's checkpoints rather than out of a fresh replay's state read, which is the most likely reason
but is a guess.

Its `VERIFICATION.txt` has a section headed **WHAT THIS RUN IS NOT**, and that section is the reason to cite
the file rather than the run:

- **75 of its 161 segments were taken under `ACCEPT_AFTER` and written to `logs/flagged.json` unpolished.**
  These are the frames the run found, not the frames that exist.
- It stopped at the segment *after* `deliver`, on `l2_sail` — `dock_policy` on a Link standing inside a cave,
  58 of 60 attempts reading `fail: no dock on this screen @ room 0A L0`. The route was wrong, not the segment
  (FINDINGS §14).
- Nothing in the file was written by hand; every line came out of the run's own checkpoints.

So: a verified from-power-on run through the dragon, on a route that is wrong one segment later. That is the
whole claim, and it is not "the game is beaten" — run6 is that.

## The rule left behind

*An emulator that renders nothing will show you a stale buffer and let you read a theory into it.* Every
strange window today had one cause, and it was in the bridge's main loop. Painting on demand does not fix a
window nobody steps; labelling the window fixes what a person can conclude from it.

And the smaller one: **if a thing makes a workflow possible, it belongs in the repository, not in `$HOME`.**
The i3 config and the Xephyr command line are the two facts that made today possible, and neither was in the
tree. They are now in `README.md` and `SETUP-LINUX.md`, which is the only reason a future session has them.