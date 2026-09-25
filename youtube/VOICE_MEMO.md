# Voice memo - read, then react

This replaces the script. Each card has two parts:

* **What happened** - the facts, your own messages (typos and all, straight from our chat log), and what the AI wrote
  in its journal that day. Glance at it. Don't read it out loud.
* **Talk about** - a few nudges. Pick whichever one gets you going and ignore the rest.

How to record it

1. Phone voice memo is fine. Quiet room, phone a hand's width from your mouth. Camera is fine too.
2. Say the card number, then talk. "Card six..." - that is how I line your answers up afterwards.
3. Talk to one person: a friend who likes games and has never heard of this project.
4. Ramble. Go on tangents. Laugh, swear, contradict yourself. Long is good - cutting is my job.
5. If a card does nothing for you, skip it. If you want another go at one, just do it again; I will take the best.
6. Don't try to be accurate about the technical stuff. Say what you understood. I will put the exact numbers on screen.

Whole thing should take 25 to 40 minutes. Drop the audio in `harness/youtube/voice/` when you are done.

---

## PART 1 - BEFORE

### Card 1 - Why
**What happened.** September 11, late morning. Your very first message:
> "I have this thought on creating an AI bot that can not only fully figure out how to complete, but also potentially
> hold a world record for 'time to beat' a classic game like the original Zelda from NES... I want AI to do all research
> and play without my input, or at least very little input... maybe even do like pac man or something but I think zelda
> would be sick"

**Talk about**
* Where did this idea come from? What were you doing when you thought of it?
* Why Zelda? What is that game to you - when did you first play it, have you ever beaten it, how long did it take you?
* Did you actually think it would work?

### Card 2 - Who you are in this
**Talk about**
* What do you do? Are you a programmer? How much of the code in this project did you write or even read?
* Had you ever done anything like this with an AI before?
* What did you think your job was going to be? What did it turn out to be?

---

## PART 2 - THE FIRST DAY

### Card 3 - Fifty minutes
**What happened.** Eight minutes after that first message: "ok i downloaded bizhawk and my NES rom. its in the folder".
About fifty minutes in, you were watching the first video: Link being moved by a program that had not existed an hour
earlier. It did not go smoothly - the journal says "Link stood directly under it for 500 frames and nothing happened"
(the sword; it could not work out how to pick it up) - and then it did: power-on to sword and back outside in 1,036
frames. Your message: "i love it."

**Talk about**
* What did you see on your screen in that first hour? What was it like watching it go?
* What did you expect to happen when you hit enter on that first message?

### Card 4 - "What's the harness on it?"
**What happened.** That same afternoon someone who knows AI asked you how it worked, and you came back to ask me:
> "did it write an emulation and extract game state? or visual matching?"

The honest answer, in plain words: the AI never holds the controller and never looks at the screen at game speed - it
is far too slow for that. It wrote the player: about 20,000 lines of Python that read the Nintendo's memory (2,048
numbers - one is Link's X position, one is how many bombs he has) and press the buttons. Then it watched what its player
did, read logs, read the game's own code, and rewrote the player. Over and over, for days.

**Talk about**
* Explain to your friend what the AI actually did here. Your words. Get it wrong if you have to.
* Did that surprise you - that it wasn't "watching" the game at all?
* How do you describe this to people? What do they say back?

### Card 5 - The rules
**What happened.** That evening you set the terms:
> "be the best, be the quickest. use all tools available to get it done, but do not hack, or cheat. you have to actually
> play the game and play it right."

And about practice: "I want the save states to exist for learning how to maximize each thing, but i want that learning
to carry over into 1 seamless playthrough".

**Talk about**
* Why did "no cheating" matter so much to you? What would have counted as cheating?
* What is the difference, to you, between practising with save states and cheating with them?
* What would you say to someone who says "it's tool-assisted, so it doesn't count"?

### Card 6 - Coaching a Darknut fight
**What happened.** Day one, 6:30 in the evening, you are already giving it Zelda lessons:
> "darknuts will never turn 90 degrees except when exactly on a square... thats how link should take advantage. right
> now your link is a little willy nilly in movements sometimes"

The AI was losing to one room of five Darknuts. Hundreds of attempts. A handful of wins.

**Talk about**
* How do you know that about Darknuts? How much of this game is just in your hands?
* What was it like watching something smart be that bad at a room you could clear yourself?
* "Willy nilly" - describe how it moved in those first days.

---

## PART 3 - THE GRIND

### Card 7 - The morning routine
**What happened.** Look at the times on your messages and there is a pattern: 7 to 9 in the morning, almost every day.
"keep going with your testing and run. i do have a couple thoughts though." "do you ahve the latest video created?"
"how did we end up". The AI kept a journal because you told it to - 42 entries by the end.

**Talk about**
* Walk me through a morning. You wake up, and then what? What are you checking first?
* What was the computer doing all night? What did the room sound like? Did it get in the way of using your own PC?
* Did you read the journal? Anything in it stick with you?

### Card 8 - "You just sat there"
**What happened.** Day two:
> "on the room with the slimes, you just sat there not moving for a while. while you dont HAVE to kill the slimes, you
> should have to make progress to that next door"

The AI's journal that day is titled *Passive is losing*: Link had stood still for sixteen seconds because a Zol was
standing in his lane. The night before, the same journal had said: "every hit is a mistake it could have avoided."
It had taken your advice about not getting hit and turned it into a Link who was scared of slimes.

**Talk about**
* What does it feel like watching Link just stand there?
* You have now told it some version of "stop being so careful" on day 2, day 3, day 7 and day 11. Why do you think it
  keeps drifting back to careful? Is that funny or is it maddening?

### Card 9 - "Be honest"
**What happened.** Day three, 8:40 at night: "are you stuck? youve been doing the same thing for a long time". Next morning:
> "ok how are you doing right now, be honest. looks like you're struggling"

Three minutes later: "you should just try new things if the old things dont work. that seems pretty basic
troubleshooting". Forty minutes after that: "looks like you cleared it but are just wandering around swinging at
nothing now".

**Talk about**
* Tell me about the low point. Was there a day you thought this wasn't going to happen?
* What is it like to tell an AI to "be honest"? Did you believe the answer?
* The swinging-at-nothing thing. Describe it. What did you think was going on in its head?

### Card 10 - "Maybe I can help"
**What happened.** Day five, and it is grinding on the last stretch of the game. The journal from that day: inside
Level 9 - Death Mountain - with thirteen hearts, the Magical Sword and zero bombs, in a dungeon made of bombable walls.
That morning, you:
> "can you show me where you're having a problem in the emulator? maybe i can help"

**Talk about**
* You had said "without my input". What made you offer?
* Were you tempted to just pick up the controller and do that one room yourself? Why didn't you?

---

## PART 4 - IT FINISHES. THEN IT GETS FAST.

### Card 11 - The first finish: 1 hour 43 minutes
**What happened.** September 15. The journal entry is called *The end*: 372,090 frames, 609 rooms rehearsed, replayed
from power-on and matched byte for byte. One hour forty-three. Your reply that night:
> "great job on beating it. that's very impressive."
...followed immediately by a list of everything that was wrong with it. "you do some things very very well, just some
things really silly." "id love to see you complete the whole game in under an hour." And: "dont ask me any questions,
just go. im away from the computer for a while".

**Talk about**
* Where were you when you found out it had beaten Ganon? What did you do?
* Be honest: was 1:43 impressive or embarrassing? Both?
* Why "under an hour"? Did you think it could?

### Card 12 - The silly stuff
**What happened.** From your notes on that run: it bought bombs in a shop while monsters were dropping them for free.
It beat a boss and then stood in the empty room doing nothing "for a very long time". It walked in and out of Level 6
"a lot for some reason". It bombed skeletons.

**Talk about**
* What was the dumbest thing you watched it do? Tell it like a story.
* What was the first thing it did that made you think "oh - that's actually clever"?

### Card 13 - Under the hour: 57:40
**What happened.** A day later: 57:40. But first, from the journal: "The re-run reached Level 4 and stopped there for
five hours. Every blocker was mine, not the game's." It had broken its own run four different ways trying to make it
faster.

**Talk about**
* Did you know it was breaking its own stuff? What is it like when the thing you are relying on is confidently wrong?
* How much did you trust it by this point - more or less than on day one?

### Card 14 - Game tape
**What happened.** September 17, 8:52 in the morning. You send almost twenty notes with frame numbers, like a coach
going through film:
> "at frame 3776. around the 10:20 mark in the video, link sits there attacking the air for about 15 seconds"
> "you should generally just go through them and kill them if they get in the way rather than avoid them"
> "human world records are under 30 minutes. i dont expect you to be able to beat that, but it would be amazing if you
> were in the realm of that"

**Talk about**
* How long did that review take you? Were you watching the whole hour with a notepad?
* At what point did "finish the game" turn into "chase the record" in your head?
* What is your job title on this project? Coach? Producer? Boss? Something else?

### Card 15 - The overnight: 41:15
**What happened.** Two days of fixes from your notes, then you left it running overnight. In the morning: 41:15,
verified. Sixteen minutes faster than the run before. Your message: "very well done... watching you play it, it seems 95% perfect, but the WR holders are sub 30 minutes."

**Talk about**
* Tell me about that morning.
* 95% perfect - and still eleven minutes off the record. Where did you think the eleven minutes were hiding?

### Card 16 - The leaderboard
**What happened.** You sent a screenshot of the speedrun.com leaderboard, on a tab called "Extreme Rules", hoping it
meant glitchless. It is glitchless - and also no sword and no extra hearts, which is a different sport. "i was just
hoping htat was glitchless." The 27:40 record is in a category that allows glitches (scrolling the screen to skip
across the map, clipping through blocks), and the runners use them. Your rules don't.
Then you said: "if you could get to 33-35 minutes. that woudl be incredible".

**Talk about**
* Glitches were on the table. They are legal in that category. Why did you stay clean?
* Where did 33 to 35 come from? Gut feeling?

### Card 17 - 39.24
**What happened.** The AI decoded the entire overworld map out of the cartridge, built a planner, and had it shuffle
the order of the whole game. The planner said the best route it could find would take 39.24 minutes. The run came in
at 39:15 - which is 39.25. And then the AI told you, more or less: 36, maybe. 35 without glitches - I won't promise it.

**Talk about**
* When you saw those two numbers next to each other, what did you think?
* How did it feel to be told "probably not" by your own AI?
* Eight days: 1:43, 57:40, 41:15, 39:15. Which jump impressed you most?

---

## PART 5 - NOW

### Card 18 - "No one talks like that"
**What happened.** September 21. The AI made the first cut of this video, script and all. You watched the whole thing
and wrote: "the scripting is very dry, and very 'AI'. No one talks like that."

**Talk about**
* What was it like hearing your own project explained back to you by the thing that built it?
* What did it get wrong about the story? What did it leave out that only you know?

### Card 19 - Trust
**What happened.** Every run is replayed from power-on on a fresh emulator and the memory is compared byte for byte.
The final run is an input file: every button press for all 144,551 frames. Anyone with the emulator and their own copy
of the game can play that file back and watch their own computer do the run.

**Talk about**
* How do YOU know it didn't cheat? What convinced you?
* What do you want to say to the person typing "fake" in the comments?

### Card 20 - What it was like
**Talk about** - finish these out loud, as many times as you like:
* "The weirdest part of working with an AI for ten days was..."
* "The thing nobody tells you about this is..."
* "I thought it would be like ___, and it was actually like ___."
* "If it were a person, it would be the kind of coworker who..."

### Card 21 - The verdict
**Talk about**
* Can AI beat Zelda without cheating? Answer it like someone just asked you at a barbecue.
* Can it beat the world record? What is your honest guess at where this ends up?
* What did this cost you - time, money, sleep? Worth it?
* What is next? (You did mention Pac-Man on day one.)

---

## PART 6 - FIRST LINES (for the on-camera open - try each a few ways, in your own words)

### Card 22
* Start a sentence with: "Every morning for ten days, I woke up and..."
* Start one with: "I can't beat Zelda in under two hours. But..."
* Start one with: "A week and a half ago I typed one message to an AI..."
* Then just tell me, in fifteen seconds, what this video is. Do it three times.
