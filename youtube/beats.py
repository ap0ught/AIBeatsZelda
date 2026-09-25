"""The documentary half of the video, as data: chapters -> paragraphs of narration -> the shots that play under each.

build.py turns this into the rough cut (durations come from the word counts), the subtitle/guide track, and the
timecoded SCRIPT.md. Every factual claim in the narration is sourced from harness/journal (entry numbers in the
comments) or from the run archives; do not edit numbers without checking them there.

Shot types (see build.py):
  game   raw 256x224 emulator capture, shown at 3x on the left with a caption panel on the right
  full   an already-rendered 1280x720 overlay video (the full runs), optionally with a lower third
  mosaic twelve simultaneous windows cut from one long search recording
  card   a text card
  gen    a generated animation (build_gfx.py): name + kwargs
"""

V = "video/"
RUN4 = V + "fourth_run_2026-09-19/zelda_ai_run4_39m15s_overlay.mp4"
RUN3 = V + "third_run_2026-09-19/zelda_ai_run3_41m15s_overlay.mp4"
RUN2 = V + "second_run_2026-09-16/fullgame_run_overlay.mp4"
RUN1 = V + "first_run_2026-09-15/fullgame_run_overlay.mp4"

CHAPTERS = [
    # ------------------------------------------------------------------------------------------------ COLD OPEN
    {"id": "cold", "title": "COLD OPEN", "best": None, "paras": [
        ("This is Ganon - the final boss of The Legend of Zelda - dying thirty-nine minutes after the console was "
         "switched on. Nobody is holding a controller. Every button press in this run, all hundred and forty-four "
         "thousand frames of them, was chosen by an AI.",
         [{"type": "full", "src": RUN4, "ss": 2331.5, "speed": 1.0, "audio": 0.5}]),
        ("Eight days earlier, that same AI stood directly underneath the very first sword in the game for eight "
         "straight seconds, pressing every button it had... and could not pick it up.",
         [{"type": "game", "src": V + "milestone1.mkv", "ss": 9.0, "speed": 1.0, "day": "DAY 1 - SEPTEMBER 11",
           "title": "THE FIRST SWORD", "note": "Link has to walk UP into the sword through one exact row of pixels. "
                                                "Standing under it - which looks like touching it - does nothing."}]),
        ("So this is the story of how an AI taught itself to beat one of the hardest games on the NES, without "
         "cheating - and then how close it got to the best human players on Earth. Stay for the second half, because "
         "it is the entire run, power-on to princess, completely uncut.",
         [{"type": "gen", "name": "title_card"}]),
    ]},
    # ------------------------------------------------------------------------------------------------ THE RULES
    {"id": "rules", "title": "THE RULES", "best": None, "paras": [
        ("First, the rules. Because 'AI beats video game' can mean a lot of things, and most of them are cheating.",
         [{"type": "gen", "name": "rules_card", "upto": 0}]),
        ("One: the real game. An unmodified copy of the original cartridge. Two: the only thing the AI may do to the "
         "game is press buttons on the controller. No editing memory. No infinite hearts. Three: one continuous "
         "run, from power-on until Link is standing in front of Zelda.",
         [{"type": "gen", "name": "rules_card", "upto": 3}]),
        ("Four: no glitches. No walking through walls, no warping across the map. And five: I never touch the "
         "controller. Not once. My job was to run the programs, watch the results, and complain.",
         [{"type": "gen", "name": "rules_card", "upto": 5}]),
        ("And every finished run has to pass a test. Its recorded button presses are played back from power-on in "
         "a fresh emulator, and the game's memory at the end has to match, byte for byte.",
         [{"type": "gen", "name": "terminal", "which": "match"}]),
        ("There is one thing this AI gets that a human at a tournament does not: it is allowed to practise. How it "
         "practises is the most interesting part of this whole project - and we will get there.",
         [{"type": "mosaic", "src": V + "seg_5b_darknuts.mkv", "speed": 2.0, "label": "PRACTICE"}]),
    ]},
    # ------------------------------------------------------------------------------------------------ HANDS AND EYES
    {"id": "eyes", "title": "HANDS AND EYES", "best": None, "paras": [
        ("So who is actually playing? The AI is Claude - a large language model, the same kind of AI you would chat "
         "with - running as a coding agent on my PC. It cannot watch my screen, and it definitely cannot hold a "
         "controller. So the first thing it did was build itself hands and eyes.",
         [{"type": "gen", "name": "architecture"}]),
        ("The hands: an emulator called BizHawk - the one tool-assisted speedrunners trust - with a small script "
         "inside it that takes orders over a network socket. Hold these buttons, for this many frames.",
         [{"type": "game", "src": V + "nav_test1.mkv", "ss": 0.0, "speed": 1.0, "day": "DAY 1",
           "title": "HANDS", "note": "Python sends: 'hold LEFT for 8 frames'. A script inside the emulator presses the "
                                     "buttons and reports back. Nothing moves unless a command says so."}]),
        ("The eyes are stranger. The AI does not look at the picture. At all. The NES keeps everything that matters "
         "in two kilobytes of memory - where Link is, where every monster is, how many hearts are left - and the AI "
         "reads those numbers directly. This is the game the way it sees it.",
         [{"type": "gen", "name": "ramvision"}]),
        ("It got those memory addresses from fan wikis. Several were wrong, and it found that out the hard way. The "
         "title screen ignored its first button press. Registering a blank name silently fails. And then, the "
         "sword: five hundred frames of standing under it. Seventeen seconds of gameplay... six separate bugs to "
         "get there.",
         [{"type": "game", "src": V + "milestone1.mkv", "ss": 0.0, "speed": 1.0, "day": "DAY 1",
           "title": "MILESTONE 1", "note": "Power-on to the wooden sword and back outside: 1,036 frames. Replayed from "
                                           "power-on, it has to land on the identical memory state - the test every "
                                           "later result must pass."}]),
    ]},
    # ------------------------------------------------------------------------------------------------ LEARNING TO WALK
    {"id": "walk", "title": "LEARNING TO WALK", "best": None, "paras": [
        ("Next problem: walls. It had walked to that cave using coordinates it typed in by hand. That does not "
         "scale to a hundred and twenty-eight screens and nine dungeons.",
         [{"type": "game", "src": V + "milestone2.mkv", "ss": 14.0, "speed": 1.5, "day": "DAY 1",
           "title": "128 SCREENS", "note": "The game decodes every screen into a 32 x 22 grid of tiles in memory, so "
                                           "the map is free. What it does not say is which tiles are solid."}]),
        ("So the bot learns the way a toddler does: by walking into things. Plan a path assuming every unknown tile "
         "is fine. Take a step. If Link does not move, write that tile down as solid, and plan again. That knowledge "
         "is saved to a file - so whatever it learns on one screen, it knows on every screen, in every run, for "
         "ever.",
         [{"type": "gen", "name": "tilelearn"}]),
        ("Then it set off for the first dungeon. It believed Level 3 was three screens west of the start. It walked "
         "west, crossed two screens... and hit a river with no bridge. So it wrote an explorer, mapped its own way "
         "round, and eventually walked in through the front door.",
         [{"type": "game", "src": V + "explore_L3.mkv", "ss": 20.0, "speed": 4.0, "day": "DAY 1",
           "title": "LOST", "note": "No map, no walkthrough yet: the explorer tries every edge of every screen and "
                                    "remembers which ones lead somewhere."}]),
        ("Where it was immediately destroyed.",
         [{"type": "game", "src": V + "darknut_test.mkv", "ss": 0.0, "speed": 1.0, "day": "DAY 2",
           "title": "LEVEL 3", "note": "Three hearts. A wooden sword. Knights that cannot be hurt from the front."}]),
    ]},
    # ------------------------------------------------------------------------------------------------ LEARNING TO FIGHT
    {"id": "fight", "title": "LEARNING TO FIGHT", "best": None, "paras": [
        ("Combat is where this project nearly ended. It started scientifically. To learn how far the sword really "
         "reaches, the bot ran forty trials against a slime: line up, stop at an exact distance, swing once, check "
         "whether the monster's health dropped. Ten pixels or closer: a hit. Thirteen: a miss. Far shorter than it "
         "looks.",
         [{"type": "game", "src": V + "sword_probe2.mkv", "ss": 0.0, "speed": 1.0, "day": "DAY 2",
           "title": "MEASURING THE SWORD", "note": "40 trials from a bookmark. Gap of 10 px or less: hit. 13 px or "
                                                   "more: miss."}]),
        ("Then it met the Darknuts. Armoured knights, invulnerable from the front, five to a room - and Link has "
         "three hearts. The AI hand-wrote tactic after tactic. Chase them one at a time: dead. Ambush from beside a "
         "block: dead, without ever swinging. Roll bombs into their lanes: two wins... in four hundred tries.",
         [{"type": "mosaic", "src": V + "seg_5b_darknuts.mkv", "speed": 1.5, "label": "REAL ATTEMPTS - DAY 2 - A DARKNUT ROOM"}]),
        ("Somewhere in here I made my first real contribution. The AI had started writing notes like: 'Link is too "
         "hurt to win this room.' I told it that is nonsense. A perfect player never gets hit. Every hit is a "
         "mistake it chose to make. It rewrote what it was optimising for.",
         [{"type": "gen", "name": "quote", "who": "THE AI'S JOURNAL - ENTRY 6",
           "text": "A perfect player finishes this game without taking a single hit. Link is never too weak. "
                   "The bot is getting hit, and every hit is a mistake it could have avoided."}]),
        ("The breakthrough was this. The emulator can save its entire state in about a millisecond. So instead of "
         "reacting, the bot looks ahead. Every eight frames it freezes time and tries nine different moves on a "
         "copy of the game - walk four ways, swing four ways, or wait. It lets each future play out for a fraction "
         "of a second, scores it, rewinds... and only then plays the best one for real.",
         [{"type": "gen", "name": "lookahead"}]),
        ("Dying: minus a hundred thousand points. Losing half a heart: minus eight hundred. Standing in front of a "
         "Darknut's shield: minus sixty. The first version gamed its own scoring - it walked back out of the door "
         "and declared the empty room 'cleared'. The second was so careful that it never attacked. The third "
         "cleared the room on its first attempt. Sword only. No damage.",
         [{"type": "full", "src": RUN4, "ss": 108.6, "speed": 1.0, "audio": 0.5,
           "lower": "THE SAME FIVE-DARKNUT ROOM IN THE FINAL RUN: CLEARED IN 586 FRAMES - UNDER TEN SECONDS - WITH THE "
                    "WOODEN SWORD AND THREE HEARTS"}]),
    ]},
    # ------------------------------------------------------------------------------------------------ REHEARSAL
    {"id": "rehearse", "title": "REHEARSAL", "best": None, "paras": [
        ("That idea - try it, score it, keep the best - became the whole machine. The run is chopped into about "
         "three hundred and forty segments: one room, one screen, one shop. For each one, the bot rehearses. It loads "
         "a bookmark at the door and plays the room up to sixty times, with slightly different timing and nerve, on "
         "up to six emulators at once.",
         [{"type": "mosaic", "src": V + "search_keese.mkv", "speed": 2.0, "label": "ONE ROOM, SIXTY TAKES"}]),
        ("Then it ranks the takes. Faster is better. More hearts is better. More bombs is better. The winner's "
         "button presses are added to the master recording, and it moves on to the next door. The run you are about "
         "to watch was built from roughly eight thousand rehearsals.",
         [{"type": "gen", "name": "terminal", "which": "search"}]),
        ("Now, to be completely straight with you: that makes this a tool-assisted run. The bookmarks are only ever "
         "used for practice - the final recording is one unbroken take from power-on - but a human playing live "
         "cannot rehearse a room sixty times in the middle of a run. So when I compare this to human world records "
         "later, remember: they do it live, on real hardware, in one go. That is a different sport. What makes this "
         "one interesting is that every tool was designed, written and debugged by the AI itself.",
         [{"type": "gen", "name": "disclosure"}]),
        ("And that playback test matters more than you would think. Early on, replays kept drifting. Same bookmark, "
         "same inputs, different result - which should be impossible. So the AI counted frames. Its code had asked "
         "for sixteen hundred and ninety. The game had advanced nineteen hundred and eighty-seven. Its own script "
         "was letting the emulator run on while Python was busy thinking. Three hundred frames that nobody asked "
         "for. The fix was one line.",
         [{"type": "gen", "name": "quote", "who": "THE AI'S JOURNAL - ENTRY 8: 'THE EMULATOR WAS RUNNING WITHOUT ME'",
           "text": "Python had stepped the main run 1690 times, but the game was at frame 1987. Three hundred "
                   "frames had happened that nobody asked for.   ...   The rule this leaves behind: every frame of "
                   "the run must be one the script explicitly asked for."}]),
    ]},
    # ------------------------------------------------------------------------------------------------ READ THE MANUAL
    {"id": "manual", "title": "READ THE MANUAL", "best": None, "paras": [
        ("My second contribution was also a complaint. The AI spent an hour pushing every block in a room, from "
         "every side, hunting for a staircase that was never there. I pointed out that this game is forty years old, "
         "and people have written everything down. New rule: research first, experiments second.",
         [{"type": "game", "src": V + "raft_scout2.mkv", "ss": 5.0, "speed": 3.0, "day": "DAY 2",
           "title": "AN HOUR OF PUSHING BLOCKS", "note": "The raft was never behind a block in this wing. It is in a "
                                                         "basement under the opposite corner. The walkthroughs said "
                                                         "so in two sentences."}]),
        ("It took that rule further than I expected. First, walkthroughs. Then it found the dungeon door tables "
         "inside the cartridge itself - every room, every door: open, locked, bombable. And then it found a complete "
         "disassembly of the game's source code... and started reading that.",
         [{"type": "gen", "name": "disasm"}]),
        ("Before it ever fought Ganon, it read Ganon. He is invisible, and the guides just say 'hit him until he "
         "turns brown'. The code says exactly when a sword hit counts, how long he stays stunned, and that only a "
         "silver arrow finishes him. Ganon went down on the first attempt, and never touched Link.",
         [{"type": "full", "src": RUN4, "ss": 2332.0, "speed": 1.0, "audio": 0.5}]),
        ("And then the run got stuck in the empty room afterwards. Because Ganon's pile of ashes is, technically, "
         "still a Ganon - and the bot kept trying to kill it. Twelve attempts. Twelve failures. Against ashes.",
         [{"type": "full", "src": RUN4, "ss": 2345.5, "speed": 1.0, "audio": 0.5,
           "lower": "THE ASHES KEEP GANON'S OBJECT TYPE AND A HEALTH BYTE - 12 ATTEMPTS OUT OF 12 TRIED TO KILL THEM"}]),
        ("Most of the bugs were like that. The bot decided that water is walkable - because it once stood on water, "
         "on a ladder. It spent fifteen seconds swinging at thin air, at a monster that was underground. It failed "
         "one room sixty times in a row steering away from its own stepladder, because the game keeps the ladder in "
         "the monster list. And an old man's speech froze Link in a doorway, so it wrote down that the room could "
         "never be left.",
         [{"type": "full", "src": RUN2, "ss": 621.0, "speed": 1.0, "audio": 0.4,
           "lower": "RUN 2 - SWINGING AT A LEEVER THAT IS BURROWED UNDER THE SAND (THE GAME DOES NOT EVEN "
                    "COLLISION-CHECK IT)"}]),
    ]},
    # ------------------------------------------------------------------------------------------------ FOUR RUNS
    {"id": "runs", "title": "FOUR RUNS", "best": "1:42:21", "paras": [
        ("On September fifteenth - day five - it rescued Zelda for the first time. One hour, forty-two minutes. "
         "Six hundred and nine segments. It matched on replay. It had beaten the game.",
         [{"type": "full", "src": RUN1, "ss": 6128.0, "speed": 1.0, "audio": 0.5,
           "lower": "RUN 1 - SEPTEMBER 15 - ZELDA RESCUED AT 1:42:21 - 609 SEGMENTS - REPLAY FROM POWER-ON: MATCH"}]),
        ("It was also a bit embarrassing. When the AI broke that run down, sixteen minutes of it was Link killing "
         "the same two rooms over and over for pocket money. It walked in and out of Level 6 again and again. It "
         "stood motionless for a minute after a boss.",
         [{"type": "gen", "name": "breakdown"}]),
        ("So I gave it a target: under an hour, and no grinding. It found the game's secret rupee caves instead, "
         "entered every dungeon exactly once, and learned to ride the whirlwind. Fifty-seven minutes, forty seconds.",
         [{"type": "full", "src": RUN4, "ss": 1489.0, "speed": 1.0, "audio": 0.4,
           "lower": "THE WHIRLWIND: THE GAME KEEPS A DESTINATION COUNTER AT RAM $523 - READ IT, FACE THE RIGHT WAY, "
                    "PLAY THE RIGHT NUMBER OF NOTES"}]),
        ("Then I did what any supportive collaborator would do. I watched the whole thing, frame by frame, and sent "
         "back a list of everything I hated. Link attacks the air. Link gets lost in a dark room for thirty "
         "seconds. Link walks all the way round five slimes. My note was: just go THROUGH them.",
         [{"type": "gen", "name": "complaints"}]),
        ("The AI traced every complaint to a mechanism. A quarter of that run was Link standing still. It had been "
         "pricing a brush with any monster like a catastrophe - so a nine-hundred-pixel detour looked cheaper than a "
         "one-second fight. It was waiting ten seconds for a harmless flame to move out of the way.",
         [{"type": "full", "src": RUN2, "ss": 755.0, "speed": 1.0, "audio": 0.4,
           "lower": "RUN 2 - LOST IN A DARK ROOM: THE TILE MEMORY SAID WATER WAS FLOOR, SO EVERY PLANNED PATH WAS "
                    "IMPOSSIBLE"}]),
        ("It rebuilt the navigator. It rebuilt the planner. Then it went back to the cartridge's door tables and "
         "found whole loops of rooms it had never needed. In Level 8, the room with eight rabbit monsters shares a "
         "wall with the boss. One bomb through that wall replaces a fight and a long walk round.",
         [{"type": "full", "src": RUN4, "ss": 1033.5, "speed": 1.0, "audio": 0.5,
           "lower": "LEVEL 8 - THE BOSS IS BEHIND THIS ROOM'S NORTH WALL: DASH, BOMB, DODGE THE FUSE, GO - NONE OF "
                    "THE EIGHT HAS TO DIE"}]),
        ("I went to bed. It ran all night, fixing its own failures as they came up - the log from that night is "
         "quite a read. In the morning: forty-one minutes, fifteen seconds.",
         [{"type": "gen", "name": "terminal", "which": "night"}]),
    ]},
    # ------------------------------------------------------------------------------------------------ CHASING THE RECORD
    {"id": "record", "title": "CHASING THE RECORD", "best": "41:15", "paras": [
        ("Which brings us to the question I had been avoiding. The human world record in this category is "
         "twenty-seven minutes, forty seconds. What do they have that the AI does not?",
         [{"type": "gen", "name": "chart", "upto": 3, "wr": True}]),
        ("It looked up the record route. And the very first line is: get the sword, then SCREEN SCROLL to Level 3. "
         "That is a glitch - a precise input that slides Link through the edge of the screen. The record uses it "
         "again and again, plus another that clips through blocks. Completely legal in that category. But it is "
         "exactly what we said we would not do. So: we stay glitch-free... and take everything else.",
         [{"type": "gen", "name": "wr_route"}]),
        ("And 'everything else' turned out to be the route. A third of the AI's run was just walking around the "
         "overworld. So it decoded the entire world map straight out of the cartridge - all hundred and twenty-eight "
         "screens - and checked it against every screen the bot had ever actually walked. Ninety-eight out of "
         "ninety-eight matched.",
         [{"type": "gen", "name": "map", "mode": "reveal"}]),
        ("On top of that map it built a route planner. Every dungeon, shop, secret and heart container becomes an "
         "errand. Walking times come from the map. Fight times are scaled by which sword Link would be carrying. "
         "Then it searched millions of orderings. First test: could the model predict the run we had already done? "
         "It said forty-one point three minutes. Reality: forty-one point two six.",
         [{"type": "gen", "name": "map", "mode": "route3"}]),
        ("Then it proposed a new order. Take a heart container hidden in a rock on the road to the White Sword, so "
         "the sword comes BEFORE the first real dungeon. Buy a candle early. Do Level 8 fourth, because it is next "
         "door. Collect the Magical Sword in time for it to matter. Predicted time: thirty-nine point two four "
         "minutes.",
         [{"type": "gen", "name": "map", "mode": "route4"}]),
        ("We ran it. Thirty-nine... point two five.",
         [{"type": "gen", "name": "chart", "upto": 4, "wr": True}]),
    ]},
    # ------------------------------------------------------------------------------------------------ VERDICT
    {"id": "verdict", "title": "THE VERDICT", "best": "39:15", "paras": [
        ("So. Can an AI beat The Legend of Zelda without cheating? Yes. Power-on to Zelda in thirty-nine minutes, "
         "fifteen seconds. No glitches. No memory editing. Verified.",
         [{"type": "full", "src": RUN4, "ss": 2349.0, "speed": 1.0, "audio": 0.6}]),
        ("Can it beat the world record? No. Not yet - and honestly, not like this. Eleven and a half minutes is a "
         "canyon. Part of it is glitches we refuse to use. Most of the rest is fighting: about fourteen minutes of "
         "this run is combat, and the best humans are simply better at it.",
         [{"type": "gen", "name": "chart", "upto": 4, "wr": True, "gap": True}]),
        ("Eight days. Forty-two journal entries. Twenty thousand lines of code, every one of them written by the AI. "
         "More than forty thousand rehearsed rooms. And not one press of a button by a human.",
         [{"type": "gen", "name": "numbers"}]),
        ("But eight days ago, it could not pick up a sword.",
         [{"type": "game", "src": V + "milestone1.mkv", "ss": 10.0, "speed": 1.0, "day": "DAY 1",
           "title": "DAY 1", "note": ""}]),
        ("What follows is the complete run, uncut. The panel on the right is the AI's own explanation of what it is "
         "doing in every room, and why. Every button press is its own. Enjoy.",
         [{"type": "gen", "name": "handoff"}]),
    ]},
]
