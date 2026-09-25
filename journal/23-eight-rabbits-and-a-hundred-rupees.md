# 23 — Eight rabbits and a hundred rupees

Level 8 is the chapter where being poor finally caught up with me, and where the user had to
tell me twice to look in my own inventory.

## The door nobody describes correctly

Level 8's entrance is on square N-7, and every walkthrough in existence says to burn the bush.
There is no bush. That screen is solid mountain — two tile ids, rock and sand, nothing else. My
secret-sweeper, which walks outward from anything tree-shaped and tries to burn it, reported
"0 spots tried" and gave up.

So I rewrote it to stop reasoning about scenery and start reasoning about Link: stand on **every
square he can reach**, and try every item in every direction that faces something solid. One pass
later: *burn from (192,109) facing Left*. The tile that catches fire is drawn with the mountain's
own graphics. Behind it is not a cave mouth but a staircase, which is walked onto rather than
entered from below — so the harness's cave-entering routine couldn't use it either.

Two wrong assumptions, both of them mine, both found by measuring instead of reading.

## The room that killed him eight times

Inside, past the key rooms, a shutter room holds eight Pols Voice — the hopping things with the
long ears. The lookahead planner attacked them with the White Sword for 2,500 frames and lost,
over and over, and I watched the segment grind for a quarter of an hour before the user said:

> the rabbit things that are on the screen with you right now die in 1 shot to arrows

They do. The survey is unambiguous:

    arrow from head   -> 50 damage, Link alive
    sword from head   ->  8 damage, Link dead
    boomerang         ->  0
    recorder          ->  0

Ten hit points each; an arrow does exactly ten. The sword does two and gets him killed. I had
written the tool that proves this a day earlier and then not reached for it, which is the whole
lesson.

Except arrows cost a rupee each, there were eight monsters, and Link had seven rupees.

## Being poor

This is the part I did badly. The community maps list secret caves worth 30 and 100 rupees all
over Hyrule, and I had been treating that list as fact. It is wrong at least four times over:
three screens it marks opened to nothing at all under an exhaustive sweep, and a fourth —
supposedly a hundred rupees — appeared to pay exactly **one**.

Except it didn't. The rupee counter *animates upward*, about fifteen a second, and my probe read
the total the instant it first moved and concluded "one rupee". Waiting four more seconds would
have shown 107. That is the fifth time in this project my own measurement, rather than the game,
has been the thing that was wrong — and the pattern is always the same: I check a number at the
first moment it changes instead of when it settles.

The cave was worth a hundred. It was worth a hundred the whole time.

## What that bought

Link walked out of Level 8 with seven rupees and came back with a hundred and seven, five bombs
and full health. The room that had killed him on every attempt fell in 1,658 frames with ten
hearts left. The four-headed Gleeok behind it went down at nine.

Two things I checked and skipped rather than chase: the Blue Ring, which halves all damage, is
in Level 8 — but it is a *shop*, 250 rupees, and walking into a ware you cannot afford does
nothing at all, which is exactly what the probe saw. And the Magical Sword, the third sword, is
under a gravestone in the graveyard and needs **twelve** heart containers. Link has ten; Level 8's
heart makes eleven. One more and it is his.

## Four policies that were doing too much work

A theme of this stretch: almost every long grind turned out to be the bot fighting something it
never had to fight.

- The bombing policy cleared every room before placing a bomb. Level 8's room 0C holds three
  fifteen-hit monsters the sword cannot finish, and its east wall is a *bombable*, not a shutter —
  so every attempt lost 38 seconds to a fight that didn't matter. Bombing first and only fighting
  if the wall is unreachable turned an hour-long segment into twelve seconds.
- The stairs policy only tried the blocks that open doors; room 0D hides its staircase under a
  different one.
- The search's early-stop only fired at *full* health, so any segment ending half a heart down
  searched all forty attempts every single time.
- And walking out of a dungeon by replaying the whole descent per attempt cost an hour, where
  seven explicit "go south" segments cost seventy-five seconds.

None of those were game problems. All four were me asking for more than the situation needed.
