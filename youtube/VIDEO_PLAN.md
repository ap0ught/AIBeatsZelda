# Video plan - "Can AI beat The Legend of Zelda without cheating?"

Two halves, one upload:

| | length | what it is |
|---|---|---|
| **Part one** | ~16 min | the story: how the AI built its own hands and eyes, learned the game, and went from 1:42 to 39:15 |
| **Part two** | 40:05 | the verified 39:15 run, completely uncut, with the AI's reasoning panel |

Everything in part one is real project material: the early test recordings, the four full runs, the AI's journal, the
run logs, the game's disassembly, and graphics drawn from the project's own data (the lookahead branches are the real
ones, the map is the one decoded from the cartridge, the log lines are copied from the logs).

## Files (all in `harness/youtube/`)

| file | use |
|---|---|
| `SCRIPT.md` | the narration, paragraph by paragraph, with timecodes and what is on screen |
| `out/part1_guide.mp4` | part one with the script burned in as subtitles - **record your voice-over while watching this** |
| `out/part1_clean.mp4` | the same cut without subtitles - this is the one that goes in the final video |
| `out/part1.srt` | the script as timed captions (upload to YouTube after you adjust it to your read) |
| `out/zelda_ai_full_video.mp4` | part one + the full run, joined without re-encoding the run |
| `out/youtube_description.txt` | description, the disclosure paragraph, and chapter timestamps for both halves |
| `clips/` | every shot as its own file (numbered in order) if you would rather cut it yourself |
| `beats.py`, `gfx.py`, `build.py` | the source: change a line of narration or a shot, run `python youtube/build.py`, and only what changed re-renders |

The cut is paced to the script at ~147 words a minute with a breath after every paragraph. If your natural read is
faster or slower, tell me your words-per-minute (or send the recorded voice-over) and I will re-time the picture to it:
it is one number in `build.py` (`WPS`).

## Cadence - why it is ordered this way

Retention is lost in three places: the first 30 seconds, every time the picture stops changing, and the moment the
viewer thinks they have got the point. The structure answers each.

**0:00 Cold open (55 s).** Open on the payoff - Ganon dying at 39 minutes with nobody holding the controller - then cut
hard to day one, where the same AI cannot pick up the first sword. That contrast is the whole video in fifteen seconds,
and it plants the question. The title card comes *after* the hook, and the promise ("the second half is the entire run,
uncut") gives people a reason to stay and a reason to trust it.

**0:55 The rules (75 s).** Short, numbered, on screen. It sets the stakes and pre-empts the first comment everyone would
otherwise write. It ends on an open loop - "it is allowed to practise, and we will get there" - which is paid off in
chapter 5.

**Chapters 2-4: hands and eyes, learning to walk, learning to fight (~6 min).** Each chapter is one problem, one
failure that is funny to look at, and one idea that fixes it. Visual type changes every paragraph: diagram, game
footage, memory overlay, journal quote, twelve-window mosaic, the nine-futures animation. The Darknut room is the
emotional low ("two wins in four hundred tries") and the lookahead is the first big win.

**Chapter 5: rehearsal (~2 min).** The core mechanism, and the honest part. Saying plainly that this is tool-assisted
- and why a human record is a different sport - costs nothing and buys credibility for every claim after it. The
"emulator was running without me" story shows the verification standard is real.

**Chapter 6: read the manual (~2 min).** The comedy chapter: Ganon's ashes, walkable water, swinging at a buried monster,
the stepladder in the monster list. It is also where the AI reading the game's source code lands - the most surprising
fact in the video.

**Chapter 7: four runs (~3.5 min).** The progress bar the viewer has been waiting for: 1:42 -> 57:40 -> 41:15. Your
review list is the turn - the human pushing the AI - and the overnight log is the AI answering.

**Chapter 8: chasing the record (~2.5 min).** Highest stakes, latest. The record route's first line is a glitch; the
decision to stay clean; the map decoded from the cartridge; and the prediction beat - the planner says 39.24, the run
comes in at 39.25 - which is the single best moment in the story and is held until here on purpose.

**Chapter 9: the verdict (~50 s).** Answer both questions honestly (yes; and no, not yet), call back to the sword, hand
off to the run. People who came for the gameplay get it immediately; people who stayed for the story know what they are
watching.

**Part two.** Uncut, with chapters per dungeon in the description so viewers can jump around. The on-screen panel
already explains every room, so it needs no narration - but a few sparse comments at the big moments (the hidden road,
Level 8's wall bomb, the Magical Sword, Ganon) would help if you want them.

## Titles (pick one; A/B the rest)
1. **Can AI Beat The Legend of Zelda Without Cheating?**  <- the honest one, and the answer is yes
2. I Let an AI Speedrun Zelda. It Read the Game's Source Code.
3. An AI Taught Itself Zelda in 8 Days. Here's Its Fastest Run.
4. AI vs. the Zelda World Record (No Glitches, No Cheats)

Avoid "AI beats the world record": it does not, and the video says so.

## Thumbnail ideas
* Left: Link under the sword, "DAY 1: can't pick it up". Right: Ganon exploding, "DAY 8: 39:15". Big arrow between.
* The memory-overlay frame (red boxes on the monsters, green on Link) with "IT NEVER SEES THE SCREEN".
* The bar chart: 1:42 -> 57 -> 41 -> 39 with the red record line and "HOW CLOSE?".

## Pinned comment (suggested)
> Rules recap: unmodified game, controller inputs only, one continuous run from power-on, no memory editing, no glitches,
> no human input. It IS tool-assisted - the AI rehearsed every room from bookmarks and kept the best take - but the final
> run is a single unbroken recording, replayed from power-on and verified byte-for-byte. Human records (27:40) are set
> live on real hardware. Full run starts at [timestamp].

## Accuracy notes for the read
* "Eight days": first code September 11, the 39:15 run September 19.
* Run times are power-on to the Zelda trigger: 1:42:21, 57:40, 41:15, 39:15. By speedrun.com's clock (first control to
  Zelda) the last one is 39:10.6. The record quoted is any% No Up+A, 27:40 (Schicksal, February 2026).
* "Roughly eight thousand rehearsals" is the final run's own search log (about 8,500 attempts over 341 segments).
* The AI is Claude (Anthropic), running as a coding agent; say "the AI" throughout if you would rather not name it.
