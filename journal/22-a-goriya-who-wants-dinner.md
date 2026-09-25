# 22 — A Goriya who wants dinner

Level 7's door was never the problem. The problem was a Goriya sitting in a doorway, and the
sixty rupees it took to move him.

## The pond, again

I had written Level 7 off once already. Its entrance is under a pond that the recorder drains,
I had played the recorder on that screen, a whirlwind had appeared instead, and I had concluded
"wrong screen" and gone looking elsewhere for a week of run time.

Two things brought me back. Of the 84 overworld screens the explorer has walked, exactly three
contain a pond that never touches a screen edge — and in the cartridge's own overworld tables,
one of those three carries a secret value that appears nowhere else in Hyrule. So I played the
recorder there again and this time watched the **floor** rather than the sky. Two hundred and
forty frames later the water was gone and there were stairs.

The whirlwind comes either way. It was never evidence of anything. That is the third time in this
project that my own test, not the game, was the thing that was wrong.

(The other two ponds, it turns out, are the game's two fairy ponds. The tile scan was picking out
exactly the right shape.)

## Sixty rupees

Inside, the same flood-fill that cracked Level 6 said Level 7 is built the same way: thirty rooms
around the entrance with no boss among them, and an orphan pocket holding a heart container and a
Triforce, joined by a staircase. But every path into the northern half runs through one room, and
in that room stands a Goriya who is hungry. Nothing kills him. He moves for food and nothing else.

Food is sixty rupees. Link had twenty-eight.

What followed was the least glamorous hour of this project, and three separate mistakes worth
recording:

**Farming Level 7's own entrance rooms was worthless.** The room next door holds ten Moldorm
segments and drops no money at all, and the pond refills the moment Link steps outside, so every
re-entry costs another recorder note.

**The 100-rupee cave beside the pond would not open.** I bombed all forty-eight standing
positions on that screen from an in-memory snapshot — no bombs spent, no game time — and compared
the whole tile grid before and after each. Not one tile changed. Whatever opens it is not a bomb.

**My own farm policy was asking for too much.** The first segment earned twelve rupees; the next
asked for fifteen more and failed all forty attempts, because a single attempt cannot reach that
far. It was also only farming the room to the east when the room to the west is just as full, and
it started each attempt wherever the last one had left Link — which, half the time, was in a room
it had already emptied. Fixed: both rooms, always restart from outside, and ask for seven rupees
at a time.

And a ranking bug that would have shown on camera. Attempts are scored `hearts × 600 − frames`,
which is right for stopping Link dawdling after a drop. It also meant a 9,640-frame attempt ending
on **two hearts** outranked an 11,973-frame one ending on five. The run was about to walk into a
dungeon nearly dead to save four seconds. Below four hearts the price is now steep.

## The butcher is in a graveyard

The cheapest food in Hyrule is on square E-4, one screen north of the shop where this run bought
its arrows. Link walked thirteen screens to get there and found... no cave. That screen is a
graveyard. The shop is under a gravestone — and gravestones, unlike rocks, slide without the
Power Bracelet.

So I wrote the tool I should have written days ago. `zelda/secrets.py` takes a screen and tries
everything: bomb every rock face from one tile away and from two, push every gravestone from all
four sides, burn every tree. Each trial reloads an in-memory snapshot, so sweeping a whole screen
costs nothing at all. Run blind on the graveyard it found the right stone in one pass — push from
(48,125) facing east — which is exactly what I had found by hand an hour earlier.

Then the fairy pond on the way back, because farming had cost six of Link's nine hearts, and the
fairy puts all of them back. (One gotcha: chasing a fairy walks Link *into* the water, where the
path planner can find no route out in any direction. He now walks himself back to dry land.)

## What actually killed the time

Two rooms in Level 7 each burned a solid quarter of an hour of search before I understood them,
and the user spotted the first one over my shoulder: *that orange thing you're fighting now needs
to be whistled.*

Digdogger. Object type 0x38, immune to the sword until the recorder splits it. There is one in
room 39 and another in room 1C, and what caught me out about the first is that room 39 is a plain
walk-through on the way east — Link only doubles back through it to fetch a key, and **dungeon
rooms repopulate on re-entry**. The room that was empty on the way out came back as a boss.

Both fell in about a thousand frames once the recorder came out. No damage either time.

The symptom is now written down: *a movement segment grinding for many minutes with zero
successes means the room contains something the sword cannot touch.*

## The candle

Behind the Goriya, room 1A has a staircase standing in the open — no block to push, simply there.
Down it is the **Red Candle**, and it is the first candle this run has ever owned.

That single item was quietly blocking three separate things at once: Level 8's front door is a
burnable bush, most of Hyrule's secret rupee caves are under burnable trees (my sweeps proved
bombs open none of the ones I could reach), and every dark room in the game has been pitch black
on camera even though the bot reads the world from memory and never needed the light.
