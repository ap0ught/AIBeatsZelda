# Transcript — the narration script

**Video:** [I Gave an AI Zelda and One Rule: Don't Cheat.](https://www.youtube.com/watch?v=mBalZml520o)
Channel: Bears Gaming Den - published 2026-09-23 - 48:17 (2,897 s)

The harness in this repository is what made that video. This file is its
**narration script**, rendered from `youtube/SCRIPT_v3.md` by
`script_to_transcript.py` so the two cannot drift apart.

## Read this before treating it as a transcript

It is the script, not a transcript of the finished video, and the difference
matters:

* The published narration was **read aloud** and then transcribed with
  faster-whisper by `youtube/transcribe_cut.py`, which also cuts the flubs and
  long gaps and stamps the section timings. Its output -
  `youtube/voice/narration_transcript.txt` and `narration.srt` - is **not in this
  repository**; `youtube/voice/` holds the author's own recordings and was never
  committed. So the words as actually spoken, after the flubs were cut, cannot be
  recovered from here. What follows is what was *written to be read*.
* The **live intro and live outro are not here at all.** They were filmed on
  camera in unscripted words and exist only in the video.
* One line in the script's intro bullets claims the narration is the author's
  voice "cloned by the same computer". The tooling contradicts that -
  `transcribe_cut.py` describes "the owner's narration" and the section headings
  "he read aloud" - so treat the cloned-voice line as unconfirmed and the tooling
  as the better evidence.

## What the markers mean

* `> [visual]` entries are shot directions. They were never spoken. They name real
  footage or real artefacts - emulator windows, log files, the journal, the
  cartridge - and paths in them are relative to `youtube/`.
* The **on-screen reasoning panel** burned into the footage during the run is a
  separate track and is not here. It lives in `zelda/captions.py`: one entry per
  segment, giving the objective and the reason, for every segment of the verified
  37:02 run.

If you want the intro, the outro, or the as-spoken wording, the video exposes an
automatic caption track (`en-orig`). It is speech-to-text rather than an authored
transcript, and it is the only place the unscripted sections exist as text:

```
yt-dlp --write-auto-subs --sub-lang en-orig --skip-download "https://www.youtube.com/watch?v=mBalZml520o"
```

The run itself is in this repository and is better than any description of it.
`runs/run6/inputs.txt` replays from power-on to the ending, byte-exact, in about
three minutes - see `README.md`.

---


## PART ONE

### 0. Three in the morning

> [visual] the real overnight screen: six emulator windows grinding the same room, the log scrolling under them, a clock in the corner

This is what the computer was doing at three in the morning. Six copies of Zelda, all in the same room, all trying the same fight, over and over. The window underneath is the log. Every line is an attempt: how many frames it took, how many hearts it had left, whether it won. Ten days of this, and at the end of it a run of the whole game that is faster than most humans will ever play it. So let's go through how it actually works, from the very first hour.

### 1. It doesn't play the game. It built a player.

> [visual] architecture, drawn piece by piece as it's described: the emulator window, a tiny Lua script inside it, a socket, the Python side; then the four commands typed out

First thing. The AI never plays the game live. It can't. Zelda wants a decision sixty times a second and a language model takes seconds to think. So on day one it built itself a set of hands. A tiny script that lives inside the emulator and listens on a network port. And on the other side, Python, sending it four kinds of message. Hold these buttons for this many frames. Tell me the game state. Save a bookmark. Load a bookmark. That's the entire interface. Everything you're about to see is built out of those four things.

> [visual] the file tree growing over ten days, line count ticking up to twenty thousand; the journal folder beside it

Then for ten days it wrote the player, watched what the player did, read the logs, and rewrote it. Twenty thousand lines of Python by the end. And it kept a journal. Forty-five entries. Every one of them is a problem, what it tried, what went wrong, and what it changed. A lot of this video is just reading that journal back with the footage next to it.

### 2. Eyes

> [visual] the game on the left; on the right the object X, Y, type and health rows of memory as hex, updating live, and the decoded list: Link (x,y,hearts), each Stalfos (x,y,hp)

It never looks at the screen. Not a pixel. Everything that matters in this game lives in two kilobytes of memory. Two thousand and forty-eight bytes. One of them is Link's x. One is his y. One is hearts, one is keys, one is bombs. Twelve of them are where the monsters are and twelve more are what they are. So it reads those, sixty times a second.

> [visual] the journal entry from day one about the memory maps being wrong; the wiki table with two values swapped

The addresses came from fan-made memory maps. And several of them were wrong. The journal from day one: the wiki's table of game modes has two values swapped, and the code was waiting for the wrong number. It found that by testing. That is going to be a theme. It reads the guides, and then it checks them against the machine, and the machine wins.

> [visual] an overworld screen from run 6 with the thirty-two by twenty-two tile grid from memory over it, walkable green, solid red, unknown grey, and the evidence lines from tiles.json

The map is in memory too. Every screen is a grid of tiles, thirty-two across, twenty-two down, and the game keeps that grid decoded. What the grid doesn't say is which tiles Link can walk on. So it measured that. It walked Link into things. Walk up a column until he stops, note which tile stopped him, do it again for every tile type. Two facts came out of that. Link's collision box is sixteen by sixteen and starts three pixels below the y value the game stores, which explains every stopping position. And collision is per eight by eight tile, so the shadow at the bottom of a tree is ground even though it's drawn as tree.

> [visual] the knowledge file, tiles.json, scrolling: tile ids, walkable or solid, and the evidence line for each - "walked onto it at (96,157) in room 66"

All of that goes in a file. Tile numbers it knows are walkable, tile numbers it knows are solid, and for each one the evidence: where it learned it. Anything else is unknown. When a planned step fails and exactly one of the tiles it would have entered was unknown, that tile is now solid, forever, on every screen, in every future run.

### 3. Legs

> [visual] the navigator's plan drawn on the real screen: the eight-pixel grid, the path from Link to the door, a monster with a red halo of cost around it; the path bending; every two steps it re-plans

Walking is a path search. Dijkstra over eight-pixel steps, unknown tiles assumed walkable until proven otherwise, and every monster on the screen adds a cost to the squares around it, so the path bends away from the ones that hit hard. With monsters around it only walks two steps before it looks again. And if something killable is standing in the lane, it doesn't wait. It swings, twelve frames, and keeps walking.

> [visual] day two: Link standing in the doorway of the Zol room for sixteen seconds; then your message; then the journal entry "Passive is losing"

That last part was a rule that had to be learned. On day two it stood in a doorway for sixteen seconds because a slime was in its lane. I said, you don't have to kill the slimes, but you have to make progress. That night's journal is called "Passive is losing", and the rule that came out of it is still in the code: standing still is never safety. Detour, or kill what's in the way.

> [visual] the real day-one exploration trace drawn as a map graph: screens lighting up as they are entered, walks as edges, bookmark jumps as dashed returns, the seven-screen route in green at the end

Nobody gave it the world map. To find Level Three it explored. Stand on a screen, read the grid, work out which edges you could walk to, save a bookmark, walk out one exit, note where you land, jump back, try the next. Twenty screens later it had a route: west, north, west three times, south, east. Up and around the river.

### 4. Practice

> [visual] the search wall: forty-eight real attempts at Level 8's six-Darknut room playing at once at game speed, a leaderboard filling as they finish, the winner gold; then the winning take fills the screen

Here is the mechanism the whole thing runs on, and it's the honest part. Bookmarks. The emulator can save its entire state in about a millisecond. So the game is cut into three hundred and forty-one segments, roughly one per room, and every segment is a search. Load the bookmark at the door. Try the room with a different random seed. Log how many frames it took and how many hearts came out. Do that sixty times, or ninety, across six emulators at once. Keep the best. Bookmark the end of it. Next room.

> [visual] the ranking, as a formula on screen: frames count against you; a heart is worth hundreds of frames when you're low and almost nothing when you're full; a bomb in hand is worth two hundred and twenty; and an attempt that can no longer beat the best is cut off mid-run

To pick the best attempt it needs one number per attempt, so everything gets converted into one currency: frames. Time is the thing being minimised, so a frame costs one point. Then everything else that matters gets a price in frames. A heart is worth hundreds of frames when Link is low and next to nothing when he's full, because a run that arrives at a boss on one heart dies at the boss. A bomb in hand is worth two hundred and twenty frames, because it opens a wall later that would otherwise cost a detour. Those prices were guesses at first, and every one of them got changed when the footage disagreed with it. And any attempt that can no longer beat the best one gets cut off in the middle, so the emulators don't waste time finishing losers.

> [visual] the verify log: "replayed 136526 frames ... ram sha1 3115e31f ... MATCH"

Then the final run is stitched from those best takes, and this is where the rule about cheating is enforced. The whole input log, every button on every frame from power on, is played back in a fresh emulator with no bookmarks, and the memory at the end is hashed and compared. If one byte differs, the run doesn't count. So yes, it's tool assisted, the way a tool-assisted speedrun is. A human record is set live in one sitting, and that is a different sport. But nobody edited this. The game played every frame.

### 4b. Things that broke

> [visual] a twelve-window wall, each window a real failure clip with its title under it: "The emulator was running without me" (the desync), "Four ways to break your own run", "Zero bombs" (Level Nine with none), "The raft that hadn't landed", "The detector that could not see", "Which way Link faces", "A Goriya who wants dinner", "The bomb a Wizzrobe owed me", the sword pickup (500 frames of nothing), the stepladder as a monster, the empty room it declared cleared, the Ganon-room door it couldn't find. All twelve play at once; then one is pulled forward

Not everything went forward. Of the forty-five journal entries, about a third are about something breaking, and they're the best ones. Day one, late, the run kept desyncing: same bookmark, same inputs, different result, which should be impossible in a deterministic emulator. It tested the emulator four ways before it counted frames and found three hundred that nobody had asked for: the emulator had been running on its own between commands. The rule that came out of it is still the first rule of the harness: every frame of the run is one the script explicitly asked for. Day five, it reached the last dungeon with thirteen hearts, the best sword in the game, and zero bombs, in a dungeon made of bombable walls. Day six, it optimised a health bonus and cost itself a heart a room, then broke its own run three more ways in one afternoon and wrote all four down. Every one of those is a clip, and every one has a fix behind it.

### 5. Fighting: one second ahead

> [visual] the day-one Darknut mosaic: twelve real attempts, Link dying in all of them; the journal line: "two wins in four hundred tries, both at one heart"

Fighting is where the first approach died. Level Three has a room with five Darknuts, and the hand-written reaction code lost it hundreds of times. The journal's frame trace found why: the "get out of its way" logic and the "get behind it" logic disagreed every single frame, so Link jittered in place until a Darknut walked into him.

> [visual] mind's eye through the whole five-Darknut fight of run 6 (the planner re-run on the kept take, frame-identical): boxes read from memory around Link and every monster with facing and hp, the walking-distance heat map, ghost Links at the end of every candidate future coloured by score, and the ranked list

The fix is the thing I think is the coolest part of the whole build. It stopped reacting and started looking ahead. Every eight frames it takes a snapshot of the game. Then it tries nine moves on the snapshot. Walk up, down, left, right. Swing up, down, left, right. Or wait. For each one it lets the game run a few more frames to see what happens.

Now it has nine possible futures and it has to pick one, so each future gets turned into a number, the same way the attempts did: a list of things that matter, each with a price, added up. Time costs half a point a frame. Dying is minus a hundred thousand, which just means never. Losing half a heart costs hundreds, and more when Link is already low. Taking a hit point off an enemy is plus sixty, and a kill is plus a hundred and fifty. Standing in front of a Darknut's shield is minus sixty, and it knows which way the shield faces because that's a byte in memory too. And there's a gentle pull toward the one place a sword hit can happen: beside or behind the nearest enemy, one sword length away. Highest number wins. It plays that move for real, and does the whole thing again. Seven times a second, a couple of hundred frames of the future for every eight frames of the present.

Those prices are the player's entire personality, and they were all set by hand and then argued with. Price damage too high and Link won't leave the doorway. Price distance too high and he never attacks. Both of those happened. And the rule that fixed the standing around is a price too: the longer a fight drags on, the more expensive every frame gets.

> [visual] the first lookahead attempt at the gauntlet: five Darknuts down in eight hundred and ninety frames, three hearts intact; the log line

The five-Darknut room fell on the first try. Eight hundred and ninety frames, sword only, all three hearts intact. Two earlier versions of the prices are worth keeping on tape: the first one walked back out the door and declared the empty room cleared, because leaving the room wasn't priced, and the second was so careful about distance that it never attacked. Both were fixed by changing a number, which is the difference between a bug in a rule and a bug in a reflex.

### 6. Measuring the monsters

> [visual] a quick reel: Gohma's eye opening and one arrow going in; Dodongo eating a bomb; a Gleeok head coming off and still flying; Patra's eight eyes; the stepladder in the monster list; Link swinging at a buried Leever

Every boss got the same treatment: measure, don't assume. Patra: bombs, arrows and the boomerang all tested at zero damage, so it's the sword, and the core can't be touched until all eight eyes are gone. Gohma: only an arrow, and only while the eye is open. Dodongo eats bombs, two of them. Gleeok's heads have to die one at a time and a loose head keeps flying and spitting after its neck is gone. And two things in the enemy table that weren't enemies: its own stepladder, which the game spawns as an object, so for a while every water crossing looked dangerous exactly when Link reached it. And a Leever underground, which it attacked for fifteen seconds because the table said it was there.

### 7. Reading the cartridge

> [visual] the journal entry "Read the manual"; then real assembly from the disassembly scrolling, with the labels

On day two I told it it was testing things it could look up. The journal entry is called "Read the manual", and the rule that came out of it is research first, experiment second. So it read the walkthroughs. And then it went one step further than any walkthrough: it read the game's own code. There's a complete disassembly of Zelda, every instruction on the cartridge, labelled, and it read the parts that mattered.

> [visual] run 6, Level 4's dark room: HandleMonsterDied from the disassembly on the right, lines lighting as the counter in memory climbs 7, 8, 9; the bomb placed; the tenth kill by the bomb; HelpDropValue flips to 1; bombs 1 -> 5

Like how the game decides what a monster drops. There's a counter. Every kill without getting hit adds one, and the tenth kill in a row is a guaranteed drop: five rupees, or, if the killing blow was a bomb, bombs. So the planner counts. On the ninth kill it holds the sword back, pulls a bomb, and takes the tenth with it. Free bombs, from a rule that was on the cartridge the whole time.

> [visual] the level info blocks: hex on the left, and on the right the dungeon map with the stair destinations drawn in; then the Level Four shortcut: the ring room, two bomb walls, three rooms skipped

It read where every staircase in every dungeon comes out, which is a table in the cartridge, not something you have to walk. It read the door tables and audited its own dungeon routes against them, and found a shortcut in Level Four: round the moat, two bombs through two walls, three rooms and a boss skipped.

> [visual] the overworld decoded from the cartridge, all one hundred and twenty-eight screens drawn tile by tile, with the caves, shops and secrets labelled; "98 of 98 walked screens match exactly"

And then it decoded the entire overworld map straight out of the ROM. All one hundred and twenty-eight screens, every tile, every cave, every shop and what it sells, every secret and what opens it. It checked the decoding against the ninety-eight screens it had actually walked, and all ninety-eight matched exactly. So now it had the whole map, without having walked it.

### 8. Routing

> [visual] the route planner: errands as cards - dungeons, swords, shops, hearts, secrets - being shuffled; the predicted time dropping; the two routes drawn on the decoded map side by side

With the whole map, it could plan the whole game. It built a router that walks any leg of the map the way Link actually walks, with the raft, the ladder, the two mazes, the hidden road, and the whirlwind, which the cartridge says sets Link down on the left edge of a finished dungeon's screen. Then it calibrated that on a real run: a screen change costs a hundred and thirty-five frames sideways and a hundred and six up or down, on top of the walking. The model reproduced the forty-one minute run to within four seconds.

> [visual] 39.24 and 39.25 side by side

Then it shuffled the order of everything. Which dungeon first, when to fetch the White Sword, which of three candle shops, which of the hundred-rupee caves, when to ride the wind. The best order it found was predicted at thirty-nine point two four minutes. The run came in at thirty-nine point two five. It predicted its own run to within a second, from a map it read out of a file.

### 9. The sword that went sideways

> [visual] run four: Link circling two Darknuts that are each one sword length away, sides exposed; then the audit table: twenty-three minutes of play, fourteen in fights, eight of those positioning, hit thirty-six times all run

But that run still had a smell. I watched it and said, it's pathing around things instead of killing them and walking through, and it sits there and thinks. So it measured. Twenty-three minutes of actual play in a forty minute run. Fourteen of those in rooms with fighting. Eight of the fourteen was positioning: circling, backing off, waiting. And Link got hit thirty-six times in the whole run, which for a speedrun is almost nothing.

> [visual] the A/B: damage priced at a quarter, at a twentieth, "reckless" - rooms zero to twelve percent faster, reckless slower

Its first theory was cowardice: it had priced a half heart at up to thirteen seconds, so Link would burn hundreds of frames dodging one bump. It tested that. It made damage nearly free. The worst rooms got zero to twelve percent faster, and the reckless setting was slower, because a hit is a knockback and a knockback is time. Wrong theory. Cleanly disproved, in about an hour.

> [visual] the printed decisions: a wall of log lines, frame by frame, Link's position, the Darknuts' positions and facing, and every swing scored as a miss; one hundred and sixty frames highlighted

So it printed every decision of one fight and read them. And for a hundred and sixty frames Link zig-zagged between two Darknuts that were each exactly one sword length away with their sides exposed, and every swing it simulated at them came back a miss.

> [visual] same room, same frame, same buttons. Left: the old swing, the sword goes LEFT, facing byte 2. Right: the fix, the sword goes up, facing byte 8. The grid line at x=128 drawn on both

Here's why. Zelda moves Link on an eight-pixel grid and only turns him when he's on a line. Off the line, pressing up slides him sideways to the line first, still facing sideways, and turns him after. The sword command was: press the direction for one frame, then attack. So for ten days, about half of every perpendicular swing, every bomb and every arrow went out sideways. And nothing ever broke, because the search only kept the takes that worked. The planner just learned that attacking from the side mostly fails, and circled.

> [visual] the fix: face() - hold the direction until the facing byte agrees; then the table: six Darknuts 2,342 -> 1,306, Level 8 key room 2,121 -> 1,363, Gohma 1,508 / 629 / one failure -> 245 / 245 / 267

One fix: turn until the facing byte says you're facing it, then swing. A single unrehearsed try at the six-Darknut room went from twenty-three hundred frames to thirteen hundred, better than what fifty rehearsals used to find. Gohma went from a coin flip to three clean kills in a row, because half her arrows had been leaving sideways too.

### 10. Six runs

> [visual] the same room, Level 3's five Darknuts, from runs 1, 2, 4, 5 and 6 side by side, synced at the door, each freezing with its time (run 3's take is identical to run 4's, so it is not shown twice); then the chart

Six complete runs. One hour forty-two: the first finish, six hundred and nine segments, ten minutes of it farming rupees. Fifty-seven forty: the route rewritten, no farming, money from secret caves. Forty-one fifteen: one night, sixteen minutes, mostly from going through monsters instead of around them. Thirty-nine fifteen: the planner's route. Thirty-seven nineteen: the sword. Thirty-seven oh-two: a wider search, ninety attempts a room instead of sixty.

### 11. Where it stands

> [visual] the leaderboard: 27:40; a record run's first screen scrolling through a wall; then our time pie: sixteen and a half minutes of scrolls, menus and fanfares; twelve of fighting; seven and a half of walking

The human record is twenty-seven forty, and the record route walks through a wall on its first screen. That's legal in that category and those runners are incredible at it; it is not legal here. Of our thirty-seven minutes, sixteen and a half are screen scrolls, menus and item fanfares that only a shorter route could touch, twelve are fights the glitchless route can't skip, and seven and a half are walking. That's the gap, and that's what it is.

> [visual] the journal's last entry; then the repo; then the run's first frame

Everything you just saw is in the journal, and the code and the input file are in the description. If you have the emulator and your own copy of the game, your computer can play this exact run, frame for frame, and check it byte for byte. What follows is thirty-seven minutes of a machine playing Zelda, uncut, and the panel on the right is it telling you what it's thinking.

Here's the run.

---

## PART TWO

The verified run, uncut, with the reasoning panel. Chapters per dungeon in the description.
