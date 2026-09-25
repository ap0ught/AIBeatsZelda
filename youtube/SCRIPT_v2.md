# Script v2 - in your voice

Written from your voice memo (how you actually talk: fast, "so" / "like" / "kind of" / "I was like...", long sentences
that run on with "and" and "but", and you get excited about the thing rather than jokey about it) and from your own
messages in our chat, quoted where they are good. Read it out loud once. Anything that doesn't sound like you, cross
out and tell me what you'd say instead - that is exactly the input I need.

Numbers are spelled out because the voice model reads them literally. `[VISUAL]` is what's on screen; it is not read.
The body is about 2,270 words, which at your pace is thirteen or fourteen minutes. Your live intro and outro bookend it.

---

## LIVE INTRO (you, on camera - your words, not a script; hit these beats in whatever order)

* You can't beat this game in under two hours. You beat it once, as a kid, thirty years ago.
* Ten days ago you typed one message to an AI: beat Zelda, no cheating, I'm not touching the controller.
* Every morning you woke up and read the journal it wrote you overnight. (Hold up the phone / screen.)
* It got there. The question is how fast, and what it took - and the whole run, uncut, is at the end.
* One honest line: the narration you're about to hear is my voice, cloned by the same computer. It read this script. I
  wrote it with the AI, from my own words.
* "So let me show you what happened."

---

## PART ONE (cloned voice)

### 1. The idea
`[VISUAL: your actual first message, September eleventh, typed out on screen as it's read]`

So here's the deal. On September eleventh I typed one message to an AI. I said, I've got this thought about creating an
AI bot that can not only figure out how to complete a classic game, but maybe hold a world record for it. The original
Zelda, on the NES. And I want it to do all the research and all the playing without my input, or at least very little
input. I'm never touching the controller.

Now, I'm not a programmer. I've been an IT guy, I've played games my whole life, and for the last year or so I've been
using AI for pretty much everything. But I honestly did not know if this was possible. I kind of figured, it's a forty
year old game, there are infinite guides out there, it's got to be super easy for an AI to figure out.

`[VISUAL: the run times ticking down: 1:42 -> 57 -> 41 -> 39 -> 37, then the journal folder with 45 entries]`

It was not easy. It took ten days, six complete runs of the game, and over fifty thousand practice attempts. And every single morning of those ten days I woke up and read the journal my computer wrote me overnight.

### 2. The rules
`[VISUAL: rules card, one line at a time]`

Before anything else, the rules, because I know what the first comment is going to be.

One. The real game, unmodified, running in an emulator. Two. Controller inputs only. No memory editing, no cheat codes,
no glitches. Three. One continuous run, from power on to Zelda. Four. It's allowed to practise with save states, but the
final run has to be one seamless playthrough that anyone can replay and verify. And five. I never touch the controller.
Not once.

Hang on to that practice part, because it's the difference between what this is and a human speedrun, and I'll come
back to it.

### 3. Day one - hands and eyes
`[VISUAL: the milestone-one footage: Link standing under the sword for eight seconds doing nothing]`

So, day one. Eight minutes after that first message I had the emulator installed and my ROM in a folder, and I said,
okay, go. And this was the first thing that surprised me. The AI doesn't play the game live. It's way too slow for that.
Zelda needs a decision sixty times a second, and this thing takes seconds to think. So instead of playing the game, it
wrote itself a player.

`[VISUAL: architecture, drawn as it's described: emulator window -> a little script inside it -> a socket -> Python]`

It put a tiny script inside the emulator that listens on a network port. And then twenty thousand lines of Python talk
to that script. Hold these buttons for this many frames. Tell me the game state. Save a bookmark. Load a bookmark. That's
it. That's the whole interface to the game.

`[VISUAL: the RAM vision capture: the real game on the left, and on the right the two thousand numbers with the ones
it reads highlighted - Link's x, Link's y, hearts, bombs, and the twelve monster slots - updating live]`

And here's the part that really got me. It never looks at the screen. Not once. Everything that matters in this game
lives in two kilobytes of memory. Two thousand and forty-eight numbers. One of them is Link's x position. One is his y.
One is how many bombs he's got. Twelve of them are where the monsters are. So it reads those numbers sixty times a
second, and it presses buttons. It has never seen a single pixel of Zelda.

`[VISUAL: milestone one again: Link walks into the cave, gets the sword, walks out. Your message "i love it." pops up]`

About fifty minutes in, I was watching Link walk into the cave and come out with the sword, played by a program that
did not exist an hour earlier. And I typed, "i love it." Which, you know. I was easily impressed at that point.

`[VISUAL: the GitHub page mock-up / the repo folder listing, then the description link]`

So when people ask me what the AI actually did here, this is the answer. The AI wrote the player. Then for ten days it
watched what its player did, read the logs, read the game's own code, and rewrote the player. Over and over and over.
And that code is going up on GitHub, link's in the description. If you've got the emulator and your own copy of the game,
you can watch your own computer do this exact run.

### 4. Day one, evening - the Darknut room
`[VISUAL: the real day-one Darknut attempts: twelve emulator windows at once, Link dying in all of them]`

By that evening it had walked into Level Three and hit a wall. A room with five Darknuts. If you've played Zelda you
know these guys, the knights with the shields. And the AI could not get through them. It just walked in and died.
Hundreds of times.

`[VISUAL: your message, verbatim, typed on screen]`

And I'm sitting there giving it Zelda lessons. I literally typed: "darknuts will never turn ninety degrees except when
exactly on a square... right now your link is a little willy nilly in movements sometimes." Willy nilly. That was my
technical feedback.

`[VISUAL: the search wall: twenty-four attempts at the same room playing at once, each with a live score; the ones that
die go red, the winner goes gold and fills the screen]`

Here's the thing that made this whole project work though, and it's the honest part of the video. The emulator can save
its entire state in about a millisecond. So the AI practises. It bookmarks the door of a room, tries the room sixty
different ways, keeps the best one, and moves on to the next door. Six copies of the emulator running at the same time,
all grinding the same room. That's what my computer was doing all night, every night.

`[VISUAL: the verify log: "replayed 136526 frames -> MATCH"]`

Then the final run is stitched together from all those best takes, played back from power on as one unbroken recording,
and checked byte for byte against a fresh emulator. So yes, it's tool assisted. A human world record is set live, on
real hardware, in one sitting. That is a different sport, and I'm not pretending otherwise. But nobody edited this run.
The game played every frame of it.

### 5. Day two - "you just sat there"
`[VISUAL: the Zol room clip: Link standing in a doorway for sixteen seconds while a slime sits in his lane]`

Day two, first thing in the morning, I'm watching the overnight footage and Link is just standing there. There's a
slime in his lane and he will not move. Sixteen seconds. So I typed: "on the room with the slimes, you just sat there
not moving for a while. while you dont HAVE to kill the slimes, you should have to make progress to that next door."

`[VISUAL: the journal entry "Passive is losing", the actual text]`

And the journal that night is titled "Passive is losing." Because the night before, I had told it a hit you don't take on
purpose is a mistake. And it took that and turned it into a Link who was scared of slimes. I want you to remember that,
because I ended up telling it "stop being so careful" on day two, day three, day seven, and day eleven. It kept drifting
back.

`[VISUAL: mind's eye, running: the game on the left; on the right, what the AI sees - boxes read from memory around
Link and every monster, a heat map of walking distance across the room, and nine little futures re-scored every eighth
of a second]`

The fix for the standing around is the thing I think is the coolest part of the whole build. Before every single
decision, the AI plays the next twenty frames forward in the emulator, nine different ways. Hold up, hold down, hold
left, hold right, swing the sword in four directions, or wait. Then it scores every one of those futures. Did I get hit?
Did I land a hit? Am I closer to the door? And it picks the best one, presses it for real, and does the whole thing
again. Seven times a second. Playing a couple hundred frames of the future to decide the next eight.

### 6. Day three - read the manual
`[VISUAL: the boss clips: Ganon's ashes with the sword still swinging; Link swinging at empty water; the stepladder in
the monster list]`

Not everything was smart. I've got a whole folder of it doing dumb stuff. It killed a boss and kept swinging at the
ashes. It spent fifteen seconds attacking a monster that was buried underground. At one point it found its own stepladder
in the enemy list and wouldn't go near the water because it thought the ladder was a monster.

`[VISUAL: the disassembly on the left, real assembly with the labels; the kill counter in memory on the right]`

So on day three I told it: you're testing whether blocks can be pushed, that's great, but you could look this up.
And it did something I did not expect. It went and read the game's source code. There's a full disassembly of Zelda
online, every instruction on the cartridge, and it read the parts that mattered. Like, how the game decides what a
monster drops when it dies.

`[VISUAL: the tenth kill: the counter ticking one, two, three... ten; the tenth kill is made with a bomb, and four
bombs fall out]`

And that's a real thing in this game. There's a counter. Every kill you make without getting hit adds one, and on the
tenth kill in a row the game guarantees a drop. Five rupees, or, if the killing blow was a bomb, bombs. So the AI
started counting its kills, and on the ninth one it would hold the sword back, pull out a bomb, and make the tenth kill
with the bomb. Free bombs. I've been playing this game for thirty years and I did not know that.

### 7. Days five to nine - it finishes, then it gets fast
`[VISUAL: run one's rescue at 1:42:21; the journal entry "The end"; your reply typed out]`

Day five, it beat the game. One hour, forty-two minutes, twenty-one seconds. And I typed "great job on beating it,
that's very impressive," and then a list of everything wrong with it. It bought bombs in a shop while monsters were
dropping them for free. It walked in and out of Level Six a bunch of times for no reason anyone could see. It beat a boss and stood in
the empty room for a minute doing nothing.

`[VISUAL: your review message from September seventeenth scrolling: "at frame 3776... link sits there attacking the
air for about 15 seconds..." with the frames cut to as they're mentioned]`

So that became my job. I'd watch the run like game tape and send it notes with frame numbers. Frame thirty-seven
seventy-six, Link sits there attacking the air for fifteen seconds. Level four, the dark room, nearly thirty seconds
when it should take five. And it would go fix them. And every time I told it "dont ask me any questions, just go," it
just went.

`[VISUAL: the overnight log as a time-lapse against a clock, ending on the morning's journal entry and the number]`

Fifty-seven forty the next day. Then I left it running overnight, and in the morning the log said forty-one fifteen.
Sixteen minutes gone in one night, while I was asleep. I remember reading that number and being like, okay. This is
actually happening.

### 8. The record
`[VISUAL: the speedrun.com leaderboard: 27:40 at the top]`

And then I looked at the leaderboard. The world record for this game is twenty-seven forty. Twenty-seven minutes. And we
were at forty-one. So I asked it, straight up: what are you missing?

`[VISUAL: a record run's first screen: Link scrolls through a wall. Then the word GLITCH]`

And the answer was kind of humbling. Part of it is the route. But the biggest part is that the record route uses glitches.
On the very first screen, the runner scrolls the screen and walks through a wall. That's legal in that category, and
those runners are incredible at it. But our rules say no glitches. So we were never going to get twenty-seven. I asked if
we could get to thirty-three, thirty-five, and it told me, honestly, probably thirty-seven or thirty-eight without the
glitches.

`[VISUAL: the overworld map decoded from the cartridge, drawn tile by tile; then the route planner shuffling the
order of the whole game, the number dropping]`

Then it did the thing that still kind of blows my mind. It decoded the entire overworld map out of the cartridge, all
one hundred and twenty-eight screens, built a planner, and had the planner shuffle the order of the whole game. Which
dungeon first, which cave, which shop, when to grab the sword. The planner said the best order it could find would take
thirty-nine point two four minutes.

`[VISUAL: 39.24 and 39.25 side by side]`

The run came in at thirty-nine fifteen. Which is thirty-nine point two five. It predicted its own run to within one
second, from a map it read out of a ROM file.

### 9. The sword that went sideways
`[VISUAL: run four footage: Link circling two Darknuts instead of hitting them]`

But I watched that run, and something was bugging me. Link was still pathing around monsters instead of just killing
them and walking through. He'd get right next to something and kind of circle it. And he'd stand there and think. And
it adds up. So I told it that. And the AI's first theory was that it had made Link too scared of getting hurt. Which
made sense to me, because that's what it looked like. So it tested that.

`[VISUAL: the A/B table: damage made cheap, rooms zero to twelve percent faster; "reckless" slower]`

And it was wrong. Making damage cheap barely changed anything. So it did the thing I've come to really respect about
it. It printed out every single decision from one fight and read them. And for a hundred and sixty frames Link was
zig-zagging between two Darknuts that were each one sword length away, with their sides exposed, and every swing the AI
simulated at them came back as a miss.

`[VISUAL: the sideways sword capture: same room, same frame. Left: press up and attack, the sword goes LEFT. Right: the
fixed version, the sword goes up. Then the grid overlay explaining why]`

Here's why. Zelda moves Link on an eight pixel grid, and he can only turn when he's on a grid line. If he's between
lines and you press up, the game slides him sideways to the line first, still facing sideways, and turns him after. The
AI's sword command was: press the direction for one frame, then attack. So about half of every sword swing, every bomb,
and every arrow it had thrown in ten days went out sideways. And it never noticed, because it only kept the takes that
worked. It just learned that attacking from the side mostly doesn't work, and circled.

`[VISUAL: the before/after table per room: 2,342 -> 1,306 and so on; then run five's time]`

One fix. Turn until you're actually facing the thing, then swing. A first try at the six Darknut room went from
twenty-three hundred frames to thirteen hundred, which is better than what fifty rehearsals used to find. The next run
came in at thirty-seven nineteen, and the one after it, thirty-seven oh-two.

### 10. So, can it?
`[VISUAL: the chart: 1:42 -> 57:40 -> 41:15 -> 39:15 -> 37:19 -> 37:02 with the red 27:40 line]`

So. Can AI beat The Legend of Zelda without cheating? Yes. Six times now, and you're about to watch the fastest one,
uncut. Can it beat the world record? Not like this. Not without the glitches, and I'm not doing the glitches. What's left
between thirty-seven and the record is the route, and the route is the rules.

`[VISUAL: Link under the sword on day one, cut to Link in front of Ganon on day ten]`

Ten days ago this thing could not pick up the sword. I'm not a programmer. I typed messages into a chat window and read
a journal every morning. If you want to try it yourself, the code and the run are in the description. What you're about to
see is thirty-seven minutes of a computer playing Zelda, every frame of it real, and the panel on the right is it telling
you what it's thinking.

Here's the run.

---

## PART TWO
The verified run, uncut, with the reasoning panel. No narration. Chapters per dungeon in the description.

## LIVE OUTRO (you, on camera)
* What surprised you most (your call - the journal? the sideways sword? that it read the source code?).
* What's next - Pac-Man came up on day one.
* The comment you'd like: a room where a human would've done something smarter.
* "The code's in the description. Go make it faster than me."
