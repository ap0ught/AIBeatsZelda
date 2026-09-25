# 38 — Under the hour

**210,964 frames. Zelda rescued at frame 207,962 — 57 minutes 40 seconds of game time. Credits done at 58:30.
Replayed from power-on in a fresh emulator: MATCH (RAM sha1 63a6abe5…).** The first finished run was 372,090
frames, 1 hour 43 minutes.

The owner's brief was "id love to see you complete the whole game in under an hour", with no farming and no
buying bombs. Here is where the 161,000 frames went.

| Milestone | First run | This run | Δ |
|---|---:|---:|---:|
| enter Level 5 | 80,664 | 75,552 | −5,112 |
| Level 5 done | 97,594 | 93,636 | −3,958 |
| Gohma | 188,105 | 125,653 | −62,452 |
| Level 6 done | 188,974 | 126,539 | −62,435 |
| Level 7 done | 248,177 | 148,958 | −99,219 |
| enter Level 8 | 256,496 | 155,409 | −101,087 |
| Level 8 done | 287,066 | 172,386 | −114,680 |
| enter Level 9 | 299,811 | 183,761 | −116,050 |
| Magical Sword | 320,222 | 179,045 | (now fetched before Level 9) |
| Silver Arrow | 360,119 | 197,546 | −162,573 |
| Ganon dead | 368,491 | 207,361 | −161,130 |
| credits | 372,090 | 210,964 | −161,126 |

## Where it came from

1. **No farming** (journal 35): secret caves on 0x3D and 0x0F paid for the arrows and the bait; the bot now picks
   up the drops it used to walk past.
2. **Every dungeon entered once** (journal 37): arrows and bait bought on the walk west; Level 6 climbed once;
   Level 8's detour removed; Level 9's heart container and sword fetched first, no bomb-buying trip.
3. **Money only where it buys time.** Mid-run the owner asked about the other 100/30 caves, the 250-rupee Blue
   Ring and the boomerang (knowledge/money_ring_boomerang.md). A ten-agent workflow decoded the ROM and the
   disassembly: the Blue Ring is only at 0x34 and was worth ~0 frames for ~5,000-9,300 of cost; the orange and
   blue "ghosts" are Wizzrobes and the boomerang flies through them; only arrows remained to pay for, so even the
   planned 0x6B cave became a 2-frame segment.
4. **The whirlwind to Level 2's door** instead of the 21-screen walk to Level 8 (switched mid-walk at 0x67):
   2,957 frames from 0x67 into Level 8's screen instead of ~4,900, and the wind's counter was then known, so the
   later ride to Level 1's door took 651 frames instead of ~2,800.
5. **Two rollbacks in Level 9, both measured first.**
   - s9_10 bombed 0x20's north wall with three Blue and two Red Wizzrobes alive: every success lost 7-10 of 11.5
     hearts and left Link at 1.5 hearts with Ganon ahead. From the same state, fight-first went 4/4 at 11.5-12
     hearts in 780-918 frames; walk-and-bomb went 1.5 / died / 1.5 / 4.5. Rolled back five segments; the replay
     played s9_10 in 816 frames at 12 hearts and the Silver Arrow came 768 frames sooner with 8.5 more hearts.
   - g9_41 crossed a room of six Like Likes: one success in 18 tries, 4,081 frames. Probe: dash 2/3 at 1,018,
     sword 3/3 at 1,207-2,073. Rolled back three segments; the dash committed at 1,047 frames.
6. **Smaller things that compounded:** Gleeok's dead air trimmed, narrower lead-in jitter, success tests counted
   from each segment's own start (the single Level 6 climb had made "keys >= 4" true before the key was taken).

## Restarting a live run safely

`restart_run.sh` waits for a commit line, kills wrapper → python → EmuHawk, clears the lock and re-stamps the
checkpoint fingerprint; rollbacks back up and delete the checkpoints after the resume point first. Policy and
success-test changes behind an unchanged segment name do not change the fingerprint; names do. Seven restarts
and two rollbacks in this run, and the final replay still matched from power-on — the inputs are the only thing
that counts.
