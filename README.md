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
python smoke_test.py                   # launches BizHawk with the bridge and reads a frame
ZELDA_ROUTE=4 ZELDA_SCOUTS=6 bash run_until.sh logs/run_until.log 40
```

`fullgame.py` plays the whole game as 341 searched segments, checkpointing after each; `run_until.sh` restarts it if
the emulator dies. Six emulator instances need a reasonably modern CPU; a full run takes 4–6 hours. Every run is
different (the search is seeded randomly), so expect a time near 37 minutes, not exactly this one.

## What is where

| path | what |
|---|---|
| `bridge.lua` | the script inside the emulator: hold buttons, read RAM, save/load a bookmark, over a socket |
| `zelda/emulator.py` | Python side of that socket; input logging; screenshots; replay |
| `zelda/overworld.py` | eyes and legs: the tile map from RAM, the walkable/solid knowledge base, the path planner |
| `zelda/lookahead.py` | fighting: the every-8-frames lookahead planner and its prices; `face()` (the sideways sword fix) |
| `zelda/search.py` | practice: seeded attempts from a bookmark, the frames/hearts/bombs ranking, the cutoff |
| `zelda/runner.py` | segments, checkpoints, resume, the replay verification |
| `zelda/owmap.py`, `zelda/owroute.py`, `route_planner.py` | the overworld decoded from the ROM; the map router; the route planner |
| `zelda/boss.py`, `zelda/combat.py`, `zelda/secrets.py` | bosses, the plain fighter, caves and secrets |
| `fullgame.py`, `route4.py` | the segment list (the route) |
| `zelda/captions.py`, `zelda/intent.py`, `render_overlay.py` | the reasoning panel in the video |
| `knowledge/` | what it learned and looked up: tiles, blocks, screens, routes, the record comparison |
| `journal/` | the AI's journal, 46 entries, written as it went |
| `patch_*.py`, `probe_*.py` | the history: every change and every experiment, as it happened |
| `youtube/` | the tools that made the documentary half of the video |

## Rules the run was made under

Unmodified game in an emulator; controller inputs only; no memory editing, no cheat codes, no glitches (no screen
scrolling, no block clips); one continuous run from power-on; practice with save states allowed, the final run one
unbroken input log replayed from power-on and compared byte for byte; no human input during the run.

It is tool-assisted, the way a TAS is. Human records (27:40, any% No Up+A) are set live on real hardware, with
glitches these rules forbid, and this run does not claim to beat one.

## Credits

The AI is Claude (Anthropic), working as a coding agent. BizHawk by the TASVideos community. The memory map and the
drop rules came from the community's disassembly of the game (link: [add]). Human record and category rules:
speedrun.com.
