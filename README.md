# An AI plays The Legend of Zelda (NES) — the harness, the journal, and the run

This is everything behind the video: the player the AI wrote for itself, the notes it kept while writing it,
and the input file of the final run (37:02 from power-on to Zelda, no glitches, no memory editing, no human input).

**The video:** [I Gave an AI Zelda and One Rule: Don't Cheat.](https://www.youtube.com/watch?v=mBalZml520o)
(Bears Gaming Den, 2026-09-23, 48:17). Its narration is in [`TRANSCRIPT.md`](TRANSCRIPT.md), rendered from
`youtube/SCRIPT_v3.md`; the on-screen reasoning panel is `zelda/captions.py`.

**Not included, on purpose:** the game ROM (bring your own — see [`roms/README.md`](roms/README.md) for the
exact dump and its md5), and the third-party disassembly of the game that the AI read (linked below). Nothing
here can play without your own copy of the cartridge.

## Watch your own computer play the run (two minutes)

1. Install [BizHawk 2.11.1](https://tasvideos.org/BizHawk) and put the folder next to this one as `BizHawk-2.11.1-win-x64`.
2. Put your own dump of *The Legend of Zelda (USA) (Rev 1)* in that folder, named exactly
   `Legend of Zelda, The (USA) (Rev 1).nes`.
3. Open BizHawk, load the ROM, then **File → Movie → Play Movie** and choose `runs/run6/zelda_ai_run6_37m02s.bk2`.

The movie is the run: every button on every frame from power-on. `runs/run6/inputs.txt` is the same thing as plain
text (one line per frame), `runs/run6/search_log.txt` is the search log that produced it (every room's attempts), and
`runs/run6/VERIFICATION.txt` is the replay check: the same inputs in a fresh emulator reach the same 2 KB of RAM,
SHA-1 `3115e31f…`.

## Run the player yourself (hours)

```
pip install -r requirements.txt        # pillow, numpy
python3 testing/smoke_test.py          # launches BizHawk with the bridge and reads a frame
ZELDA_ROUTE=4 ZELDA_SCOUTS=4 bash run_until.sh logs/run_until.log 40
```

`fullgame.py` plays the whole game as 341 searched segments, checkpointing after each; `run_until.sh` restarts it if
the emulator dies. There is one MAIN emulator plus one per scout, so the default `ZELDA_SCOUTS=4` is five emulator
processes and wants a reasonably modern CPU; a full run takes 4–6 hours. Every run is different (the search is
seeded randomly), so expect a time near 37 minutes, not exactly this one.

**Routes.** `ZELDA_ROUTE` picks the dungeon order and now refuses anything but 3, 4 or 5 rather than falling through
to 3 — a route number is the one input where guessing wrong costs hours (`fullgame.py:2324`).

| route | order | what it is |
|---|---|---|
| 3 (default) | `3-1-4-2-5-6-7-8-9` | the order the verified 41:15 run was played in; its checkpoints, recording and captions all key on these segment names |
| 4 | `3-1-4-8-2-5-7-6-9` | run6, 37:02 |
| 5 | Gleeok (L4) before L1 | `route5.py` — 404 segments; the route behind `runs/gleeok_dragon/` |

`--until NAME` stops the loop after that segment and leaves a resumable run, so a route can be run part-way. It
refuses a name that is not in the route in force, rather than stopping at the end of the list.

## Watch a run while it is being searched

Five emulator windows, one MAIN and four scouts, on a nested X display, tiled so a whole search can be read at
once. Set up outside the repo:

```
Xephyr :1 -screen 1920x1080 -resizeable -ac -nolisten tcp
DISPLAY=:1 ZELDA_ROUTE=5 ZELDA_SCOUTS=4 bash run_until.sh logs/gleeok.log 40
```

`~/.config/i3/config` floats every window whose title contains `Legend of Zelda` or `Lua Console`, and gives
nothing a border. Two rules, both load-bearing and neither of them obvious:

- **Never resize a BizHawk window.** It draws from the bridge's `step` handler, so a window nobody is stepping
  never repaints, and a resize leaves a stale surface — black after a state load, or colours from an hour ago.
  i3 floating the windows is the mechanism: lay the mosaic out by *moving* them, never resizing.
- **Match i3 rules on `title=`, never `class=`.** These windows have no WM_CLASS at all.

That config is not in this repository. It has to exist on the machine doing the watching.

**A black MAIN window is normal.** MAIN is parked while the scouts search, and a parked window renders nothing,
so it sits black between segments and says nothing about the run. It is not a rendering bug — see
`FINDINGS.md` §11 for the measurement that settled it.

**Each window says what it is for.** `bridge.lua`'s `phase <label>` draws a right-aligned, phase-coloured label
on the HUD line, so four scouts showing the same room are still four different situations:

| window | labels | |
|---|---|---|
| scout | `BASELINE #n` | nothing found yet — every attempt is still looking for a line |
| | `POLISH #n` | we have a line and we are spending attempts trying to beat it |
| | `S<k>/<m> ` prefix | a staged fight is several searches under one segment name; `S3/5` says which kill |
| | `CONVERGED` `CAPPED` `SEARCHED` `DONE` | the four stop reasons, told apart — they used to print one line |
| MAIN | `REPLAY` `TRIM` `VERIFY` `DONE` | playing the winner in, trimming idle frames, the from-power-on check |

One caveat, measured rather than assumed: a window composites the overlay only when it renders a real frame, so
the label is reliable while a search is stepping that window and invisible once it parks. `bridge.lua` tries to
paint on set and it does not help. MAIN's labels do show, because MAIN is stepped every frame of the replay.

## The search stops polishing, and writes down what it gave up

`logs/flagged.json` is the improve-this-later list. Every segment the search stopped polishing writes an entry
naming the frames it took, the hearts it ended with, and why it stopped:

```
4a_bombs  {"frames": 543, "hearts": 3.0, "reason": "took the 543-frame line after 9 attempts (8 without improvement)", ...}
```

Without it the cost of the cap is invisible, because the run looks identical whether a segment stopped at 503
frames because nothing better exists or because we stopped asking. `logs/stuck.json` is the other half and is a
failure ledger: a segment that fails is recorded, a retry draws a different band of attempt seeds (otherwise the
wrapper's restart replays the identical search, plan for plan), and after two failures the runner rewinds **one
segment** and re-searches the decision that produced the failing state. Both files are advisory, per-run mutable
state in `logs/`, and either can be deleted without losing anything a resume needs.

Neither file is `knowledge/`: they are about this run, not about the game.

## The knobs

Set before `run_until.sh`; the ones in `logs/` and the search's stop rules are the ones worth knowing.

| variable | default | what it does |
|---|---|---|
| `ZELDA_ROUTE` | `3` | dungeon order: 3, 4 or 5; anything else is an error, not a fallback |
| `ZELDA_SCOUTS` | `4` | searchers, plus one MAIN — so five emulator processes at the default |
| `ZELDA_ACCEPT_AFTER` | `8` | attempts since the best last improved before the search takes what it has; `0` restores the old rule (never cut off) |
| `ZELDA_BACKPROP_AFTER` | `2` | failures of one segment before the runner rewinds one segment and re-searches the decision before it |
| `ZELDA_MAX_BACKPROP` | `2` | rewinds allowed per segment, ever; when it runs out a stuck segment stops the run instead of spinning |
| `ZELDA_SCOUT_RESPAWN` | `2` | emulator replacements allowed per scout per search; a respawn launches an EmuHawk and waits up to 60 s for its bridge |
| `ZELDA_SHIELD_AWARE` | `1` | offer a sword swing only where the blade is not on a knight's shield; `0` is the old "is anything killable within 36 px" |
| `ZELDA_RECORD` | on | `0` forces BizHawk's video recorder off; anything that passes `record=` dies at startup under Mono |
| `ZELDA_SEARCH_DUMP` | unset | a directory to write every attempt's inputs into, for the search-wall videos |
| `ZELDA_ALLOW_UNVERIFIED_ROM` | unset | the only override for the cartridge md5 check. Do not set it to make a problem go away |

`ZELDA_ACCEPT_AFTER` is deliberately not `patience` and not `tries`: those answer "how long may a segment search
before it has anything", this answers "how long may it keep polishing what it has". A segment whose line keeps
improving is never cut off — the counter resets on every improvement — so the cap only ever truncates the
fruitless tail.

## Two verified runs

| | `runs/run6` | `runs/gleeok_dragon` |
|---|---|---|
| route | 4 | 5 (Gleeok before Level 1) |
| frames | 136,526 | 60,589 |
| of which emulated time | 37:52 | 16:48 |
| in-game timer | 37:02 | not recorded |
| segments | 341 | 161 |
| work-RAM SHA-1 | `3115e31f…` | `575771d9…` |

Both replay from power-on in a fresh emulator to the SHA-1 in their own `VERIFICATION.txt`, and
`inputs.txt` carries `# valid_from_poweron=True`. run6 is the video's run and goes to Zelda; the dragon run
stops on its own, one segment after Gleeok's head is delivered. Emulated time is frames ÷ 60.0988 Hz and it
is not the game's clock: the two differ by 50 s on run6, whose in-game timer is what the directory name
records. The dragon run's `inputs.txt` header has no timer field, so the emulated-time figure is the only
length either file supports — do not read 16:48 as an in-game time.

**Read `runs/gleeok_dragon/VERIFICATION.txt` before citing it.** It has a section headed WHAT THIS RUN IS NOT,
and it is load-bearing: **75 of its 161 segments were taken under `ACCEPT_AFTER` and played unpolished**, so those
are the frames the run found rather than the frames that exist. It is not the whole game and not a finished
route-5 run — it stopped on `l2_sail`, whose policy wants a dock, on a Link standing inside a cave; the route was
wrong, not the segment (`FINDINGS.md` §14). Nothing in that file was written by hand; every line came out of the
run's own checkpoints.

## What is where

| path | what |
|---|---|
| `bridge.lua` | the script inside the emulator: hold buttons, read RAM, save/load a bookmark, draw the HUD and its phase label, over a socket |
| `zelda/emulator.py` | Python side of that socket; input logging; screenshots; replay; the cartridge md5 check |
| `zelda/overworld.py` | eyes and legs: the tile map from RAM, the walkable/solid knowledge base, the path planner |
| `zelda/lookahead.py` | fighting: the every-8-frames lookahead planner and its prices; `face()` (the sideways sword fix); `swing_connects` |
| `zelda/search.py` | practice: seeded attempts from a bookmark, the frames/hearts/bombs ranking, the cutoff and `ACCEPT_AFTER` |
| `zelda/runner.py` | segments, checkpoints, resume, the replay verification, `logs/stuck.json`, `respawn_scout` |
| `zelda/owmap.py`, `zelda/owroute.py`, `route_planner.py` | the overworld decoded from the ROM; the map router; the route planner |
| `zelda/boss.py`, `zelda/combat.py`, `zelda/secrets.py`, `zelda/head.py` | bosses, the plain fighter, caves and secrets, Gleeok's head |
| `fullgame.py`, `route4.py`, `route5.py` | the segment list (the route) |
| `zelda/captions.py`, `zelda/intent.py`, `render_overlay.py` | the reasoning panel in the video |
| `knowledge/` | what it learned and looked up: tiles, blocks, screens, routes, the record comparison |
| `journal/` | the AI's journal, 49 entries, written as it went |
| `testing/` | every change and every experiment as it happened: `patch_*.py`, `probe_*.py`, `test_*.py`. The `*.md` beside each is generated from the script — `python3 testing/make_doc.py --check` is a content comparison and exits non-zero on drift |
| `runs/` | the verified input logs: `run6` (the video's run) and `gleeok_dragon` |
| `youtube/` | the tools that made the documentary half of the video |

## Rules the run was made under

Unmodified game in an emulator; controller inputs only; no memory editing, no cheat codes, no glitches (no screen
scrolling, no block clips); one continuous run from power-on; practice with save states allowed, the final run one
unbroken input log replayed from power-on and compared byte for byte; no human input during the run.

It is tool-assisted, the way a TAS is. Human records (27:40, any% No Up+A) are set live on real hardware, with
glitches these rules forbid, and this run does not claim to beat one.

## Credits

The AI is Claude (Anthropic), working as a coding agent. BizHawk by the TASVideos community. The memory map and the
drop rules came from the community's disassembly of the game,
[aldonunez/zelda1-disassembly](https://github.com/aldonunez/zelda1-disassembly) — `RoomLayoutsOW` and the
overworld/dungeon table addresses in `zelda/owmap.py` and `zelda/romdata.py` are its symbols. RAM addresses come from
[Data Crystal's ROM map](https://datacrystal.tcrf.net/wiki/The_Legend_of_Zelda/ROM_map), which is Cloudflare-gated
for scripted access; a readable snapshot is at
[web.archive.org](http://web.archive.org/web/20260430090853/https://datacrystal.tcrf.net/wiki/The_Legend_of_Zelda/ROM_map).
Neither is redistributed here. Human record and category rules: speedrun.com.
