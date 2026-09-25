# 29 — The raft that hadn't landed

**Where we are:** eight bombs bought, back inside Level 9, standing in the doorway of a Patra's room.

## The shopping trip
One whirlwind note facing left took Link to Level 4's island. From there it's a raft ride to the
shore, a walk round the lake, and a shop that sells four bombs for 20 rupees.

It fell apart at the raft. The AI decided Link had "arrived" the moment the screen changed — but the
raft was still sailing. Its next move was planned from the middle of the lake: "no path." Or it
pressed Up, and the raft carried Link straight back to the island.

Fixed: wait until the raft has actually docked. Then a new problem. An Octorok patrols the shore
right under the pier. Step down, get hit, get knocked back onto the dock — and sail back to the
island again.

## One bad memory
Worse, the search *learned* from that. After one knockback it wrote down "you can't walk down off
this pier" — and every later attempt believed it. Thirty-seven of forty failures came from that
single wrong memory, on a path that plainly exists.

Now every attempt starts from the same clean slate, the same way it starts from the same saved game.
With that, Link dashed off the pier past the Octorok first try.

He bought bombs twice (40 of his 77 rupees), rode the whirlwind back, walked the mountain road and went
back into Level 9 through the door he'd blown open weeks ago.

## The wrong room
The AI had worked out where the Silver Arrow room should be from the dungeon's map data. It bombed its
way in and found... an old man. "PATRA HAS THE MAP." No blocks, no stairs. Forty attempts to push a
block that wasn't there.

The old man also froze Link while his words typed out — which the AI first read as Link being stuck.

So it stopped deducing and walked the walkthrough's route instead: back down, arrows for two Like
Likes parked in a doorway, through the last locked door, and into the Patra's room.

## Next
Measure the Patra — every weapon, every angle, from a saved copy — before deciding how to fight it.
