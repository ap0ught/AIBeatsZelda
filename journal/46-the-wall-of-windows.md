# 46 - The wall of windows

2026-09-22

The owner's brief for the documentary, after two rejected scripts: the process, not him; dive straight into the
technical; lots of things happening on screen at once; the struggle before every fix; Ganon once. He is recording the
narration himself from SCRIPT_v3. Today the visuals, all from real data:

* **The search wall** (`wall_r8_3f.mp4`). A real search of Level 8's six-Darknut room from run 6's bookmark, every
  attempt's inputs dumped (`ZELDA_SEARCH_DUMP`), each replayed and filmed from the same bookmark: forty-eight windows at
  game speed, a leaderboard filling as they finish (1,161 to 2,076 frames), the winner gold, then the winner's take
  full-screen. None of the forty-eight died; the cutoff never fired because the ranking's optimistic bound (full hearts,
  four more bombs) leaves room. The script's line about the slow ones "going grey" is now "falling behind".
* **The mind's eye** (`mind_59_fight.mp4`). The planner re-run on the kept take of run 6's five-Darknut fight with the
  same seed (1053, attempt 54) and a decision log hook in plan_fight: 714 frames, identical to the run byte for byte,
  45 decisions, every candidate future with its score, the strike-spot distance field, monster facing and hp. Drawn over
  the game: boxes, the heat map, ghost Links where each future ends, the ranked list. Calibrated: a sprite's centre sits
  at (x+8, y) of its RAM position.
* **The tenth kill** (`tenth_kill.mp4`). Found by scanning run 6 for streak endings and checking bombs afterwards: five
  bomb-made tenth kills in the run; the clean one is Level 4's dark room, frames 45128-45265: streak 7, 8, 9, a bomb
  placed with the sword held back, the tenth kill by the bomb, HelpDropValue = 1, bombs 1 -> 5. Shown with the real
  HandleMonsterDied assembly, lines lighting as memory changes.
* **The sideways sword** (`sideways.mp4`), the failure wall (`broke_wall.mp4`, twelve real failure clips with their
  titles), the day-one exploration graph from the real trace (`explore_graph.mp4`), RAM vision and tile learning
  recaptured from run 6, the architecture card, the decoded map, and the five-run race of the same room (runs 1, 2, 4,
  5, 6; run 3's take is run 4's, frame for frame, because run 4 resumed from its checkpoints).

Two mistakes worth writing down. The first tenth-kill scan found nothing because the replay emulator kept its battery
save (`clean_sram=False`) and so never left the title screen the way the recording had - every replay from power-on
must start from a wiped save. And the first cut of the failure wall put run 2's frame numbers on run 1's footage.

**Later the same day.** The owner recorded the whole script himself - forty-one minutes, "i mess up speaking a lot, so
good luck with editing it" - and the pipeline for that is in place: `transcribe_cut.py` (word timestamps, the section
headings he read aloud as cut markers, restarted sentences detected as a three-word phrase repeated within six seconds
with the LAST reading kept, gaps over 0.9 s shortened to 0.55 s, a review file of every cut, a cleaned narration and a
separate .srt), `build_v3.py` (each section's clips fitted to the length of his read - trimmed or held on the last frame -
then a stream-copy join with his audio), `beats_v3.py` (section -> clips), `describe_v3.py` (chapters for both halves).
Added today for the two sections that had no picture: a reel of the bosses from run 6 with what was measured about
each, and the chart of six runs against the record with run 6's time budget.

**Evening: the cut against his read.** His recording is forty-one minutes; the cleaned narration is 19.4 minutes plus a
28-second outro he ad-libbed at the end (he said on tape he won't do one on camera, so it goes after the run). The
cleanup is script-guided: restarts pruned on the raw stream first (the last reading of a repeated phrase wins), then a
word alignment to the script, then his own markers - "oh god let me just redo this whole thing", "scrub that whole part"
- found and honoured by locating the re-read. Two mistakes on the way: aligning the raw stream matched the abandoned
first reading of a sentence and threw the good one away as a stumble; and a fallback that walked back to the previous
full stop walked back 4,000 words, because whisper's word stream has almost no full stops.

The picture: every section gets its built visual first, then real footage of the run - with the AI's panel - for the
stretch it talks about, so no section holds on a frozen frame for long and no clip appears twice. New for that: the
day-one Darknut mosaic (twelve real attempts from the 71-minute test recording), the printed decisions of one fight
scrolling as a terminal, the overnight log as it was, and fifteen cuts of run 6 by segment name.

**His two notes on the first assembly.** "The intro is quite boring with the script lines" - so the cold open is now
real day-one footage of the bot playing badly, one window, then two, then twelve, each stamped with the clock time of
the test recording it comes from (5:22 PM, 5:43 PM, 6:40 PM...), a fast-forward flicker counting the days, then run 6
clearing the six-Darknut room full screen at double speed with a stopwatch: 16 seconds. And "the voice cut-up is quite
bad... I'll start a sentence, it will chop, and then I'll restart the same words." The alignment had been matching the
abandoned first start of a sentence and discarding the complete re-read as a stumble. It now prefers the LAST reading
of every script word (a longest-common-subsequence on the reversed sequences), joins sit in the middle of the silence
around each kept span with fifteen-millisecond fades, and the audio is assembled in one pass. A three-word restart rule
added along the way ate "with one heart dies at the boss" because "at the boss" occurs twice in one sentence; removed.
