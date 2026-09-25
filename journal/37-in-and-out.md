# 37 — In and out

The owner watched the first finished run and said, among other things: *"you also go in and out of
level 6 a lot for some reason."* It turned out Level 6 was only the one they noticed. The finished run
did the same thing in three dungeons, and each time for the same reason: it walked in before it had what
the dungeon needed.

| Dungeon | What the first run did | Why | Cost |
|---|---|---|---|
| 6 | climbed to 0x28, walked out, whirlwind east, walked to the arrows shop, whirlwind to Level 3, walked the Lost Woods back, climbed the same eight rooms again | Gohma needs arrows; Link had 27 rupees | ~25,000 frames |
| 8 | climbed to 0x3E, bombed up to a Gohma room it never used, walked out, looped to the 100-rupee tree on 0x6B, walked back, climbed again | Pols Voices are an arrow fight; Link had 7 rupees | ~13,000 frames |
| 9 | went in, out for a heart container and the Magical Sword, back in, out *again* to sail across the lake and buy bombs, back in | the sword needs 12 containers; the dungeon needs bombs | ~38,000 frames |

All three were rational at the moment they were written. Each segment was added when the run reached
it, from what the run knew then. None of them is rational from the finished map.

## What changed

The caves fixed the money (journal 35, and the owner's "you ignore rupees on the ground all the time,
and then waste time farming"). Once Link reached Level 5 with 182 rupees, every one of these detours
could be moved to where the route already passes:

- **Arrows and bait** — the walk from Level 5 to the west passes 0x64, two screens south of the arrows
  shop (0x44) and three from the graveyard that sells bait (0x34). Shop there, come back along 0x54,
  0x53 and 0x52 (the old bait expedition's way home), carry on into the Lost Woods. Every crossing had
  been made by some earlier run; the one new join, 0x52 → 0x62 arriving from the east, went 6/6 in a
  probe. It also removed a pointless 62 → 52 → 42 → 52 → 62 loop from the same walk.
- **Level 8's money** — the 100-rupee tree is on 0x6B, which the walk *into* Level 8 already crosses.
  Probe: +100 in 1,019 frames from that side, then on down to 0x7B. And 0x3F's open staircase (the join
  to the boss wing) is one room east of 0x3E, so nothing above 0x3E is needed at all.
- **Level 9's errand** — after Level 8: whirlwind to Level 1's door, burn 0x47 for container #12,
  whirlwind to Level 6's door, the Magical Sword, whirlwind to Level 5's door, up Death Mountain by the
  road the second entry used, and in once. No bombs are bought: drops are picked up now, room 0x16's
  pile tops Link up, and the planner is no longer allowed to throw bombs at clusters inside Level 9,
  where every bomb is a wall.

## Four things that would have bitten

1. **Absolute counts.** Every key test was a number copied from the first run (`keys >= 4`). A single
   Level 6 climb leaves Link one key richer than that run, which makes `keys >= 4` true *before* the key
   is picked up — and the search prefers the shortest success. Every one of those segments gained
   exactly one key in the first run, so they now count from the segment's own start
   (`zelda.runner.SEG_START`). The same bug was waiting in the 100-rupee cave (`rupees >= 80` — Link
   arrives with more than that now) and both bomb piles.
2. **Hex-looking names.** The Death Mountain road was first named `d9_1b`, and `d9` matches the Level 3
   caption rule `^[0-9a-f]{2}_` — the video would have captioned the last mountain climb "LEVEL 3 - THE
   MANJI". Renamed `dm9_`.
3. **The 0x62 tree.** The guide's other 100-rupee tree would have paid for a whirlwind shortcut into
   Level 8. A burn sweep of 0x62's western pocket opened nothing (13 spots unreachable). Not in the route.
4. **The bomb upgrades are inside dungeons.** Level 5 (0x16, bomb its east wall into 0x17) and Level 7
   (0x58's locked north door into 0x48), 100 rupees each. Link reaches both with less than the arrows
   and bait still to pay for, and the owner's other rule — no farming — rules out earning the difference.
   Not bought this run; the reason goes in the report rather than a farm going in the route.

## Restarts are cheap if they are timed

Both route patches were applied while the run was going. The running process has its segment list in
memory, so editing `fullgame.py` does nothing until it restarts. Wait for a `[segment] N frames` commit
line, kill the wrapper, python and EmuHawk (in that order), re-stamp the checkpoints with the new name
fingerprint (`restamp.py` — it refuses if the newest checkpoint is not the resume point), relaunch. Each
restart lost a few seconds of search.
