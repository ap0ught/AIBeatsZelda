# CAN AI BEAT THE LEGEND OF ZELDA WITHOUT CHEATING? - narration script

Part one (the documentary half) runs **16:32** at a relaxed 147 words a minute; part two is the unedited 39:15 run. Timecodes match `out/part1_clean.mp4` / `out/part1_guide.mp4` (the guide cut has this script burned in as subtitles so you can read along while recording).

Every number below is sourced from the project's journal and run archives. Square brackets are direction, not narration.


## 0:00  COLD OPEN

**[0:00 - 0:19]**  
This is Ganon - the final boss of The Legend of Zelda - dying thirty-nine minutes after the console was switched on. Nobody is holding a controller. Every button press in this run, all hundred and forty-four thousand frames of them, was chosen by an AI.  
*[ON SCREEN: run 4 (39:15) at 38:51]*

**[0:19 - 0:33]**  
Eight days earlier, that same AI stood directly underneath the very first sword in the game for eight straight seconds, pressing every button it had... and could not pick it up.  
*[ON SCREEN: early test footage `milestone1.mkv` - THE FIRST SWORD]*

**[0:33 - 0:55]**  
So this is the story of how an AI taught itself to beat one of the hardest games on the NES, without cheating - and then how close it got to the best human players on Earth. Stay for the second half, because it is the entire run, power-on to princess, completely uncut.  
*[ON SCREEN: title card]*


## 0:55  THE RULES

**[0:58 - 1:07]**  
First, the rules. Because 'AI beats video game' can mean a lot of things, and most of them are cheating.  
*[ON SCREEN: the rules, revealed line by line]*

**[1:07 - 1:27]**  
One: the real game. An unmodified copy of the original cartridge. Two: the only thing the AI may do to the game is press buttons on the controller. No editing memory. No infinite hearts. Three: one continuous run, from power-on until Link is standing in front of Zelda.  
*[ON SCREEN: the rules, revealed line by line]*

**[1:27 - 1:42]**  
Four: no glitches. No walking through walls, no warping across the map. And five: I never touch the controller. Not once. My job was to run the programs, watch the results, and complain.  
*[ON SCREEN: the rules, revealed line by line]*

**[1:42 - 1:57]**  
And every finished run has to pass a test. Its recorded button presses are played back from power-on in a fresh emulator, and the game's memory at the end has to match, byte for byte.  
*[ON SCREEN: real log lines in a terminal]*

**[1:57 - 2:13]**  
There is one thing this AI gets that a human at a tournament does not: it is allowed to practise. How it practises is the most interesting part of this whole project - and we will get there.  
*[ON SCREEN: 12-window mosaic of `seg_5b_darknuts.mkv` - PRACTICE]*


## 2:13  HANDS AND EYES

**[2:16 - 2:39]**  
So who is actually playing? The AI is Claude - a large language model, the same kind of AI you would chat with - running as a coding agent on my PC. It cannot watch my screen, and it definitely cannot hold a controller. So the first thing it did was build itself hands and eyes.  
*[ON SCREEN: diagram: Claude -> Python -> bridge -> emulator]*

**[2:39 - 2:54]**  
The hands: an emulator called BizHawk - the one tool-assisted speedrunners trust - with a small script inside it that takes orders over a network socket. Hold these buttons, for this many frames.  
*[ON SCREEN: early test footage `nav_test1.mkv` - HANDS]*

**[2:54 - 3:17]**  
The eyes are stranger. The AI does not look at the picture. At all. The NES keeps everything that matters in two kilobytes of memory - where Link is, where every monster is, how many hearts are left - and the AI reads those numbers directly. This is the game the way it sees it.  
*[ON SCREEN: the game with the AI's memory reads overlaid]*

**[3:17 - 3:40]**  
It got those memory addresses from fan wikis. Several were wrong, and it found that out the hard way. The title screen ignored its first button press. Registering a blank name silently fails. And then, the sword: five hundred frames of standing under it. Seventeen seconds of gameplay... six separate bugs to get there.  
*[ON SCREEN: early test footage `milestone1.mkv` - MILESTONE 1]*


## 3:40  LEARNING TO WALK

**[3:42 - 3:55]**  
Next problem: walls. It had walked to that cave using coordinates it typed in by hand. That does not scale to a hundred and twenty-eight screens and nine dungeons.  
*[ON SCREEN: early test footage `milestone2.mkv` - 128 SCREENS]*

**[3:55 - 4:22]**  
So the bot learns the way a toddler does: by walking into things. Plan a path assuming every unknown tile is fine. Take a step. If Link does not move, write that tile down as solid, and plan again. That knowledge is saved to a file - so whatever it learns on one screen, it knows on every screen, in every run, for ever.  
*[ON SCREEN: tile grid overlay + the bot's real tile notes]*

**[4:22 - 4:43]**  
Then it set off for the first dungeon. It believed Level 3 was three screens west of the start. It walked west, crossed two screens... and hit a river with no bridge. So it wrote an explorer, mapped its own way round, and eventually walked in through the front door.  
*[ON SCREEN: early test footage `explore_L3.mkv` - LOST]*

**[4:43 - 4:47]**  
Where it was immediately destroyed.  
*[ON SCREEN: early test footage `darknut_test.mkv` - LEVEL 3]*


## 4:47  LEARNING TO FIGHT

**[4:49 - 5:13]**  
Combat is where this project nearly ended. It started scientifically. To learn how far the sword really reaches, the bot ran forty trials against a slime: line up, stop at an exact distance, swing once, check whether the monster's health dropped. Ten pixels or closer: a hit. Thirteen: a miss. Far shorter than it looks.  
*[ON SCREEN: early test footage `sword_probe2.mkv` - MEASURING THE SWORD]*

**[5:13 - 5:36]**  
Then it met the Darknuts. Armoured knights, invulnerable from the front, five to a room - and Link has three hearts. The AI hand-wrote tactic after tactic. Chase them one at a time: dead. Ambush from beside a block: dead, without ever swinging. Roll bombs into their lanes: two wins... in four hundred tries.  
*[ON SCREEN: 12-window mosaic of `seg_5b_darknuts.mkv` - REAL ATTEMPTS - DAY 2 - A DARKNUT ROOM]*

**[5:36 - 5:58]**  
Somewhere in here I made my first real contribution. The AI had started writing notes like: 'Link is too hurt to win this room.' I told it that is nonsense. A perfect player never gets hit. Every hit is a mistake it chose to make. It rewrote what it was optimising for.  
*[ON SCREEN: quote from the AI's journal]*

**[5:58 - 6:28]**  
The breakthrough was this. The emulator can save its entire state in about a millisecond. So instead of reacting, the bot looks ahead. Every eight frames it freezes time and tries nine different moves on a copy of the game - walk four ways, swing four ways, or wait. It lets each future play out for a fraction of a second, scores it, rewinds... and only then plays the best one for real.  
*[ON SCREEN: the nine futures and their scores (real branches)]*

**[6:28 - 6:56]**  
Dying: minus a hundred thousand points. Losing half a heart: minus eight hundred. Standing in front of a Darknut's shield: minus sixty. The first version gamed its own scoring - it walked back out of the door and declared the empty room 'cleared'. The second was so careful that it never attacked. The third cleared the room on its first attempt. Sword only. No damage.  
*[ON SCREEN: run 4 (39:15) at 1:48 - lower third: THE SAME FIVE-DARKNUT ROOM IN THE FINAL RUN: CLEARED IN 586 ...]*


## 6:56  REHEARSAL

**[6:58 - 7:26]**  
That idea - try it, score it, keep the best - became the whole machine. The run is chopped into about three hundred and forty segments: one room, one screen, one shop. For each one, the bot rehearses. It loads a bookmark at the door and plays the room up to sixty times, with slightly different timing and nerve, on up to six emulators at once.  
*[ON SCREEN: 12-window mosaic of `search_keese.mkv` - ONE ROOM, SIXTY TAKES]*

**[7:26 - 7:47]**  
Then it ranks the takes. Faster is better. More hearts is better. More bombs is better. The winner's button presses are added to the master recording, and it moves on to the next door. The run you are about to watch was built from roughly eight thousand rehearsals.  
*[ON SCREEN: real log lines in a terminal]*

**[7:47 - 8:26]**  
Now, to be completely straight with you: that makes this a tool-assisted run. The bookmarks are only ever used for practice - the final recording is one unbroken take from power-on - but a human playing live cannot rehearse a room sixty times in the middle of a run. So when I compare this to human world records later, remember: they do it live, on real hardware, in one go. That is a different sport. What makes this one interesting is that every tool was designed, written and debugged by the AI itself.  
*[ON SCREEN: practice vs final-run card]*

**[8:26 - 8:57]**  
And that playback test matters more than you would think. Early on, replays kept drifting. Same bookmark, same inputs, different result - which should be impossible. So the AI counted frames. Its code had asked for sixteen hundred and ninety. The game had advanced nineteen hundred and eighty-seven. Its own script was letting the emulator run on while Python was busy thinking. Three hundred frames that nobody asked for. The fix was one line.  
*[ON SCREEN: quote from the AI's journal]*


## 8:57  READ THE MANUAL

**[8:59 - 9:21]**  
My second contribution was also a complaint. The AI spent an hour pushing every block in a room, from every side, hunting for a staircase that was never there. I pointed out that this game is forty years old, and people have written everything down. New rule: research first, experiments second.  
*[ON SCREEN: early test footage `raft_scout2.mkv` - AN HOUR OF PUSHING BLOCKS]*

**[9:21 - 9:40]**  
It took that rule further than I expected. First, walkthroughs. Then it found the dungeon door tables inside the cartridge itself - every room, every door: open, locked, bombable. And then it found a complete disassembly of the game's source code... and started reading that.  
*[ON SCREEN: scrolling disassembly of the game]*

**[9:40 - 10:03]**  
Before it ever fought Ganon, it read Ganon. He is invisible, and the guides just say 'hit him until he turns brown'. The code says exactly when a sword hit counts, how long he stays stunned, and that only a silver arrow finishes him. Ganon went down on the first attempt, and never touched Link.  
*[ON SCREEN: run 4 (39:15) at 38:52]*

**[10:03 - 10:19]**  
And then the run got stuck in the empty room afterwards. Because Ganon's pile of ashes is, technically, still a Ganon - and the bot kept trying to kill it. Twelve attempts. Twelve failures. Against ashes.  
*[ON SCREEN: run 4 (39:15) at 39:05 - lower third: THE ASHES KEEP GANON'S OBJECT TYPE AND A HEALTH BYTE - 12 AT...]*

**[10:19 - 10:54]**  
Most of the bugs were like that. The bot decided that water is walkable - because it once stood on water, on a ladder. It spent fifteen seconds swinging at thin air, at a monster that was underground. It failed one room sixty times in a row steering away from its own stepladder, because the game keeps the ladder in the monster list. And an old man's speech froze Link in a doorway, so it wrote down that the room could never be left.  
*[ON SCREEN: run 2 (57:40) at 10:21 - lower third: RUN 2 - SWINGING AT A LEEVER THAT IS BURROWED UNDER THE SAND...]*


## 10:54  FOUR RUNS

**[10:57 - 11:10]**  
On September fifteenth - day five - it rescued Zelda for the first time. One hour, forty-two minutes. Six hundred and nine segments. It matched on replay. It had beaten the game.  
*[ON SCREEN: run 1 (1:42) at 102:08 - lower third: RUN 1 - SEPTEMBER 15 - ZELDA RESCUED AT 1:42:21 - 609 SEGMEN...]*

**[11:10 - 11:32]**  
It was also a bit embarrassing. When the AI broke that run down, sixteen minutes of it was Link killing the same two rooms over and over for pocket money. It walked in and out of Level 6 again and again. It stood motionless for a minute after a boss.  
*[ON SCREEN: run 1 time breakdown bars]*

**[11:32 - 11:47]**  
So I gave it a target: under an hour, and no grinding. It found the game's secret rupee caves instead, entered every dungeon exactly once, and learned to ride the whirlwind. Fifty-seven minutes, forty seconds.  
*[ON SCREEN: run 4 (39:15) at 24:49 - lower third: THE WHIRLWIND: THE GAME KEEPS A DESTINATION COUNTER AT RAM $...]*

**[11:47 - 12:10]**  
Then I did what any supportive collaborator would do. I watched the whole thing, frame by frame, and sent back a list of everything I hated. Link attacks the air. Link gets lost in a dark room for thirty seconds. Link walks all the way round five slimes. My note was: just go THROUGH them.  
*[ON SCREEN: my review notes, typed out]*

**[12:10 - 12:34]**  
The AI traced every complaint to a mechanism. A quarter of that run was Link standing still. It had been pricing a brush with any monster like a catastrophe - so a nine-hundred-pixel detour looked cheaper than a one-second fight. It was waiting ten seconds for a harmless flame to move out of the way.  
*[ON SCREEN: run 2 (57:40) at 12:35 - lower third: RUN 2 - LOST IN A DARK ROOM: THE TILE MEMORY SAID WATER WAS ...]*

**[12:34 - 12:57]**  
It rebuilt the navigator. It rebuilt the planner. Then it went back to the cartridge's door tables and found whole loops of rooms it had never needed. In Level 8, the room with eight rabbit monsters shares a wall with the boss. One bomb through that wall replaces a fight and a long walk round.  
*[ON SCREEN: run 4 (39:15) at 17:13 - lower third: LEVEL 8 - THE BOSS IS BEHIND THIS ROOM'S NORTH WALL: DASH, B...]*

**[12:57 - 13:11]**  
I went to bed. It ran all night, fixing its own failures as they came up - the log from that night is quite a read. In the morning: forty-one minutes, fifteen seconds.  
*[ON SCREEN: real log lines in a terminal]*


## 13:11  CHASING THE RECORD

**[13:14 - 13:27]**  
Which brings us to the question I had been avoiding. The human world record in this category is twenty-seven minutes, forty seconds. What do they have that the AI does not?  
*[ON SCREEN: run times vs the world record]*

**[13:27 - 13:59]**  
It looked up the record route. And the very first line is: get the sword, then SCREEN SCROLL to Level 3. That is a glitch - a precise input that slides Link through the edge of the screen. The record uses it again and again, plus another that clips through blocks. Completely legal in that category. But it is exactly what we said we would not do. So: we stay glitch-free... and take everything else.  
*[ON SCREEN: the record route with its glitches marked]*

**[13:59 - 14:23]**  
And 'everything else' turned out to be the route. A third of the AI's run was just walking around the overworld. So it decoded the entire world map straight out of the cartridge - all hundred and twenty-eight screens - and checked it against every screen the bot had ever actually walked. Ninety-eight out of ninety-eight matched.  
*[ON SCREEN: the overworld decoded from the ROM, route drawn on it]*

**[14:23 - 14:51]**  
On top of that map it built a route planner. Every dungeon, shop, secret and heart container becomes an errand. Walking times come from the map. Fight times are scaled by which sword Link would be carrying. Then it searched millions of orderings. First test: could the model predict the run we had already done? It said forty-one point three minutes. Reality: forty-one point two six.  
*[ON SCREEN: the overworld decoded from the ROM, route drawn on it]*

**[14:51 - 15:16]**  
Then it proposed a new order. Take a heart container hidden in a rock on the road to the White Sword, so the sword comes BEFORE the first real dungeon. Buy a candle early. Do Level 8 fourth, because it is next door. Collect the Magical Sword in time for it to matter. Predicted time: thirty-nine point two four minutes.  
*[ON SCREEN: the overworld decoded from the ROM, route drawn on it]*

**[15:16 - 15:20]**  
We ran it. Thirty-nine... point two five.  
*[ON SCREEN: run times vs the world record]*


## 15:20  THE VERDICT

**[15:22 - 15:34]**  
So. Can an AI beat The Legend of Zelda without cheating? Yes. Power-on to Zelda in thirty-nine minutes, fifteen seconds. No glitches. No memory editing. Verified.  
*[ON SCREEN: run 4 (39:15) at 39:09]*

**[15:34 - 15:57]**  
Can it beat the world record? No. Not yet - and honestly, not like this. Eleven and a half minutes is a canyon. Part of it is glitches we refuse to use. Most of the rest is fighting: about fourteen minutes of this run is combat, and the best humans are simply better at it.  
*[ON SCREEN: run times vs the world record]*

**[15:57 - 16:12]**  
Eight days. Forty-two journal entries. Twenty thousand lines of code, every one of them written by the AI. More than forty thousand rehearsed rooms. And not one press of a button by a human.  
*[ON SCREEN: what it took: the project by the numbers]*

**[16:12 - 16:17]**  
But eight days ago, it could not pick up a sword.  
*[ON SCREEN: early test footage `milestone1.mkv` - DAY 1]*

**[16:17 - 16:32]**  
What follows is the complete run, uncut. The panel on the right is the AI's own explanation of what it is doing in every room, and why. Every button press is its own. Enjoy.  
*[ON SCREEN: PART TWO card]*


---
2272 words of narration. Then the hand-off card, and the full run plays uncut.
