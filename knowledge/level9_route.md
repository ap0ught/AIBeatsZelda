# Level 9 (first quest) - route research, 2026-09-15

Sources: Zelda Dungeon walkthrough sections 10.2/10.3, StrategyWiki "Dungeon 9", cross-checked
against the ROM door table (zelda/romdata.py flood-fill) and the scout's live room tours.
Room ids are the 7-9 table's. VERIFIED = walked by this run. DEDUCED = text + door graph agree,
not yet walked.

## Ganon and Zelda (DEDUCED, three independent checks)
- 0x52 / 0x42 / 0x32 is a vertical stack of three rooms with NO door into the rest of the dungeon.
  - 0x52 = the Patra room "directly beneath Ganon" (north door is a shutter).
  - 0x42 = GANON. Its floor item is 0x0E, the Triforce of Power he drops. Shutters north and south.
  - 0x32 = ZELDA, a dead end.
- Check 1: both walkthroughs end with a staircase into a Patra room, Ganon above it, Zelda above him.
- Check 2: the flood-fill puts exactly these three rooms in their own component.
- Check 3: the old man's "EYES OF SKULL HAS THE SECRET" - the compass room 0x35 and 0x32 are
  mirror images across the skull-shaped map's centre line.
- Way in: the staircase under the LEFT block of 0x23. 0x23 is reached by bombing the west wall of
  0x24, and 0x24 is the open door south of 0x14.

## Already walked (VERIFIED)
0x76 entrance -> 0x66 old man (lets all-eight-Triforce holders pass) -> 0x56 key -> bomb W -> 0x55
Lanmolas, push block, passage -> 0x14 five Like Likes (arrows) -> locked E -> 0x15 -> 0x16 (the
walkthroughs' first Patra room; the run cleared it and took its bombs).
Scout tour: 0x24 five Vires, 0x25 Bubbles/Zols/Like Likes, 0x26 eight Gels,
0x36 Bubbles/Zols/Keese, 0x06 old man + two flames.

## Red Ring (DEDUCED)
0x16 -S-> 0x26 Gels -bomb E-> 0x27 Patra (map) -bomb N-> 0x17 (enemies can be ignored)
-bomb N-> 0x07 Wizzrobes: clear, push the LEFT block, stairs, Red Ring.

## Silver Arrow (DEDUCED)
0x16 -N (locked)-> 0x06 old man -bomb W-> 0x05 Wizzrobes: clear, push LEFT block -> passage.
The walkthroughs then go: Zols room -W (locked)-> Keese room -W-> Patra room (clear, push LEFT
block) -> passage -> arrive, bomb N -> Wizzrobes: clear, push the MIDDLE block on the RIGHT side
-> Silver Arrow. Door graph fit: 0x63 Zols -> 0x62 Keese -> 0x61 Patra -> passage -> 0x53 -bomb N->
0x43 (a dead end with no other door). 0x63 -N (locked)-> 0x53 may skip the 0x61 Patra; untested.

## Ganon fight
Sword him where the fireballs come from until he turns brown (StrategyWiki: 4 Magical Sword
hits; more with the White Sword), then ONE Silver Arrow. Take the Triforce of Power, go north,
sword the flames, walk to Zelda.

## Room 0x25's bomb pile cannot be reached from the east (VERIFIED 2026-09-15)
0x25 is split into three lanes by two FULL-HEIGHT columns of blocks (tile B0 at columns 6 and 9).
The bomb pile appears at (128,144) - in the MIDDLE lane - once the room is cleared. The middle lane
is sealed: blocks on both sides, and its north and south walls are bombable walls nobody has opened.
Entering through 0x26's locked west door puts Link in the RIGHT lane, the two unkillable Bubbles
stay in the LEFT lane. Tested from a cleared-room snapshot:
- the boomerang, thrown left from three heights level with the item: no pickup (it does not carry
  past the block column);
- pushing each of the seven blocks of the right-hand column: none moves.
The walkthroughs enter 0x25 by BOMBING DOWN FROM 0x15, which lands in the middle lane. So the pile
costs a bomb to reach - useless when Link arrives with none.
Clearing it: the sword-only fight timed out 50/50; arrows (bow_clear_grab_policy) clear it every time.

## Patra and Ganon - research before any strategy (2026-09-15; survey with zelda/tactics.py first)
- PATRA: the core eye cannot be hurt until every orbiting eye is dead. Each outer eye takes TWO hits
  from the Magical Sword. The Level 9 kind alternates tight and wide orbits; the elliptical kind should
  be fought from a distance, backing off whenever the core heads toward Link. Sword beams from full
  health are the safe way to thin the eyes. (Zelda Dungeon wiki "Patra"; walkthroughs.)
- GANON (room 0x42, per the deduction above): invisible for most of the fight, firing fireballs; only a
  sword hit on his invisible body lands, and each hit shows him briefly. Stunned after 15 wooden / 8 White
  / FOUR Magical Sword hits - he turns brown - and then ONE Silver Arrow must hit him before he flashes,
  vanishes and returns to full strength. The bow needs rupees (one per shot). Afterwards take the
  Triforce of Power, go north, sword the flames, walk to Zelda. (Zelda Dungeon wiki "Ganon"; StrategyWiki.)
- Neither fight has been surveyed yet. The standing rule stands: measure with tactics.survey before
  writing a policy.

## Walked 2026-09-15 (VERIFIED) - and one deduction that was wrong
- The passage under 0x05's left block (after bombing the old man's west wall in 0x06) DOES come out
  in 0x63, as deduced.
- 0x63 -N (locked)-> 0x53 -bomb N-> 0x43 works, but **0x43 is NOT the Silver Arrow room**: it is an
  old man's hint room, "PATRA HAS THE MAP", with no blocks at all. The deduction that the dead end
  above 0x53 was the Wizzrobe room was wrong. The Silver Arrow Wizzrobe room is at the far end of the
  passage under the Patra room 0x61's LEFT block, per both walkthroughs - to be walked, not deduced.
- An old man's text freezes Link for several hundred frames after he enters; any move before it
  finishes fails ("the Down door did not open: Link is stuck").
- 0x53 holds two Like Likes that park on its SOUTH doorway, plus a Blue Wizzrobe and a Bubble.
  Walking out got Link stuck against them and cost three hearts; clear them with arrows.
- Resources on reaching 0x43: 10/13 hearts, 4 bombs, 1 key, 29 rupees. The key goes on 0x63's west door.

## Patra in room 0x61 - MEASURED with tactics.survey (2026-09-15)
Object table on arrival: core type 0x47 (hp 11) at (128,110), eight eyes type 0x25 (hp 6 each)
orbiting it, one effect 0x68. Total health 59. tactics.survey had to be told these ids (types=) -
its default 0x30-0x4F range would not have counted the eyes.
- SWORD is the only thing that hurts it: from the right 16, from above 8, from the left 4, from far
  left 4 (beams, when they fire). From below 0.
- Bombs, arrows, boomerang, recorder: 0 damage from every angle. Do not spend rupees on arrows here.
- Standing at an aim point and swinging killed Link in almost every trial: the eye ring sweeps through.
  Link had 11/13 hearts, so no sword beams - full health would add a ranged attack.
Plan: the damage-aware lookahead with the sword (validating), then push 0x61's LEFT block for the passage.

## The Patra and where its passage goes (VERIFIED 2026-09-15)
- 0x61 PATRA: the damage-aware lookahead with the sword killed it in 413 frames with no damage.
  Pushing for the staircase then took 264 frames.
- That passage surfaces in **0x20**, the dungeon map's upper-left corner (StrategyWiki: "you will
  arrive by the upper left corner"). 0x20 and 0x10 form a sealed two-room pocket - the {10, 20}
  component of the flood-fill - with no door to the rest of Level 9, which is why deducing from the
  main body's door graph never found it.
- 0x20: the staircase sits inside a diamond of eight blocks at tiles (3,8) (4,7) (4,9) (5,6) (5,10)
  (6,7) (6,9) (7,8); three Blue Wizzrobes (0x23, hp 10) and two Red (0x24, hp 4). The ROM's only door
  is a BOMBABLE wall to the north. Per the walkthroughs: bomb north into 0x10 (Wizzrobes; push the
  middle block on the right for the Silver Arrow), and on the way back clear 0x20's Wizzrobes so the
  block ring around the staircase will move.
- Verified run to 0x20: 357,487 frames, replay MATCH. Link 11/13 hearts, 4 bombs, 16 rupees.

## GANON - from the game's own code (aldonunez/zelda1-disassembly; read 2026-09-15)
Source: src/Z_04.asm UpdateGanon (line ~10284), Ganon_UpdateBrownState (~10457), Ganon_Dying (~10486),
Ganon_CheckCollisions (~10802); src/Z_07.asm UpdateObject_JumpTable/InitObject_JumpTable entry 62.
- OBJECT TYPE 0x3E. Per-slot RAM: ObjState $AC+slot, ObjTimer $28+slot, ObjHP $485+slot, x $70+slot,
  y $84+slot. Ganon_ObjPhase $42C+slot, Ganon_ScenePhase $445, Ganon_ObjAnimationFrame $46B,
  Ganon_ObjCloudDist $478. Immunity mask $FA: vulnerable ONLY to sword and arrows. He is 32x32; his
  midpoint is (x+16, y+16).
- $445 scene phase: 0 = dark room, Link lifts the Triforce (halted); 1 = lit, still lifting; 2 = FIGHT.
- BLUE (ObjState = 0): while his timer is 0 he is invisible, moves like a teleporting Blue Wizzrobe and
  fires a fireball (object 0x56) every $40 frames. A sword hit ONLY lands while the timer is 0; a hit
  sets the timer to $40 (visible, cannot be hurt). When the timer ticks to 1 he jumps to Y=$A0,
  X=$30 or $B0 (by the frame counter).
- STUN: when sword hits take his HP to 0 (four with the Magical Sword), HP is restored to $F0 and
  ObjState becomes $FF - BROWN. He stays put. ObjState decrements every other frame (~510 frames):
  drawn solid while >= $30, flickering below. At 0: blue again, new random spot, full strength.
- KILL: only while brown, only if InvArrow $0659 = 2 (silver), only with an arrow in flight (object
  slot $12 state $10) that hits him. That increments Ganon_ObjPhase (dying). The phase then rises every
  frame; at $50 the burst and ashes; at $A0 the Triforce of Power becomes the room item at his ashes.

## The passage from 0x30 surfaces in 0x04 - with NO bombs (VERIFIED 2026-09-15, 364,758 frames, MATCH)
- g9_30 bombed 0x31's west wall; 0x30's blade-trap room hides the staircase; the passage comes up in
  **0x04** (top of the map). 0x04 is a copy of 0x20: a diamond of eight blocks around the staircase,
  four blade traps in the corners, two Blue Wizzrobes (0x23) and two Red Wizzrobes (0x24).
- ROM doors: 0x04 has ONE way on, a BOMBABLE west wall into 0x03 (whose only door is that wall).
- Link arrives with 11.5/13 hearts, 1 key, 16 rupees and **0 bombs**: the eight bought at the lake
  went on 0x06/0x05, the old-man dead end 0x43 (wasted), 0x20->0x10, 0x31->0x30 and lookahead fights.

## Monster drops - from the game's code (Z_04 SetUpDroppedItem, Z_07 UpdateMetaObjectEnd, Z_01 Link_BeHarmed)
- WorldKillCycle $52A steps 0..9 on every kill (not child Gels, Red Keese, $5D) BEFORE the drop is
  picked, and is the drop table's column. It is never reset.
- Rows: row 0 = types 07 08 0E 04 0F 23 (Blue Wizzrobe); row 1 = 21 22 0D 10 13 28 2A 27 16;
  row 2 = 09 0A 03 01 12 06 0B 24 30 (Red Wizzrobe, Gibdo); row 3 = everything else.
  No drops at all: 5D 14 15 1B 1C 1D 17.
- Table (ids: 00 bomb, 0F 5 rupees, 18 rupee, 21 clock, 22 heart, 23 fairy):
  row 0: 22 18 22 18 23 18 22 22 18 18  (drop if random < $50, 31%)
  row 1: 0F 18 22 18 0F 22 21 18 18 18  (< $98, 59%)
  row 2: 22 00 18 21 18 22 00 18 00 22  (< $68, 41%)  <- the ONLY row with bombs: columns 1, 6, 8
  row 3: 22 22 23 18 22 23 22 22 22 18  (< $68, 41%)
- WorldKillCount $627 = 16 gives a fairy. HelpDropCount $50 reaching 10 forces a drop: 5 rupees, or a
  bomb only if the tenth kill was by a bomb ($51). Any hit on Link zeroes $627/$50/$51.
- A drop is NOT the room item: the dead monster's slot becomes object type $60 with the id in $AC+slot.
- At the 0x04 checkpoint the kill cycle is 0, so the next kill uses column 1: a Red Wizzrobe killed
  first drops a bomb 41% of the time. fullgame.bomb_drop_policy fights only the red ones.

## 0x04 -> 0x03 (VERIFIED 2026-09-15, 365,605 frames, MATCH)
- g9_04_bomb (fullgame.bomb_drop_policy): the first kill in 0x04 was a Red Wizzrobe at kill-cycle
  column 1 and it dropped a bomb - 98 frames, no damage; 3 of 15 probe attempts, 3 of 23 in the run.
  The pickup gave 4 bombs.
- g9_03: bombing 0x04's west wall and crossing cost 3 hearts (8.5/13 on arrival; 3 bombs left).
- 0x03: the same diamond of eight blocks around a staircase at tile (5,8); two Bubbles (0x2B), two
  Keese (0x13), two Zols (0x17). Its only door is the wall from 0x04, so the staircase is the way on
  (expected: the passage to the Patra room 0x52 under Ganon).

## 0x03 -> 0x52 -> Ganon's room 0x42 (VERIFIED 2026-09-15, 367,554 frames, MATCH)
- g9_03_st: clearing 0x03 and pushing a ring block opened the staircase (754 frames).
- g9_pass_03: the passage DOES surface in 0x52, the Patra room under Ganon - the deduction held.
- g9_52_patra: make_lafight_policy (damage-aware lookahead, sword) killed it in 541 frames, no damage.
- g9_42: north through the opened shutter into Ganon's room: Link 10/13 hearts, 16 rupees, 3 bombs,
  silver arrows. Checkpoint ckpt_fullgame_g9_42 is where Ganon gets surveyed (probe_ganon.py).

## After Ganon - from the game's code (Z_01 TakeItem, Z_04 InitZelda/UpdateGuardFire/UpdateZelda, Z_02 mode $13)
- Ganon's probe: the room is dark 77 frames, lit, the fight starts 269 frames in; he starts blue with
  HP $F0 and timer 0. ganon_policy won 2/6 probe attempts (best 937 frames, no damage); the run's
  g9_ganon search won on the same attempts.
- TRIFORCE OF POWER: item 0x0E, the room item at Ganon's ashes (measured at (60,165) - NOT on Link's
  8-pixel walking grid, and the ashes are still an object of Ganon's type 0x3E sitting on it, so the
  generic grab policy gave up 12/12 times; walk straight at it instead: fullgame.take_triforce_policy).
  Taking it sets NO inventory byte - a diff of all 2KB of RAM across the pickup shows Items+$1B ($0672)
  never changes. Z_01 TakePowerTriforce only raises TriforceFanfareActive ($509) and halts Link $C0
  frames. "Taken" = the room item is gone.
- ZELDA'S ROOM 0x32: Zelda = object type $37 in slot 1 at ($78,$88); four GUARD FIRES type $3F in slots
  2-5 at ($60,$B5) ($70,$9D) ($80,$9D) ($90,$B5). They take sword hits like monsters (CheckMonsterCollisions).
- THE TRIGGER: Link X in $70..$80 and Y exactly $95. Link is halted, set to ($88,$88) facing left, the
  fanfare plays, $80 frames later GameMode $12 = $13 (the ending). The two inner fires at Y $9D stand
  just under the trigger spot.
- THE ENDING, mode $13: curtain, "THANKS LINK, YOU'RE THE HERO OF HYRULE", flashes, peace text,
  credits; submode 4 = the Triforce over Ganon's ashes, waiting for Start. Start there saves and
  switches to the SECOND QUEST - the run ends on that screen without pressing it.

## Two navigator bugs that only Ganon's room could show (VERIFIED 2026-09-15)
1. exit_screen refused to use an OPEN shutter. Its rule was "shutter + something alive + room not
   flagged clear -> clear the room first", and Ganon's ASH PILE keeps his own object type (0x3E) and a
   health byte, so Link was sent to kill a heap of ashes: 12/12 attempts failed with "couldn't clear
   the room for the Up shutter". Fixed in zelda/overworld.py: skip the clearing when _door_open(d).
2. nav.go() cannot cross Ganon's room at all ("gave up reaching the Up door", 12/12) - its floor is
   drawn with the doorway-style tiles (0x24), which the walkability map does not treat as floor.
   Both alternatives work and are what fullgame.walk_out_policy does: plan_reach to the doorway
   (120,85) then hold Up, or simply walk to x=120 and hold Up. Measured: room 0x42 -> 0x32 in ~110
   frames from the spot where the Triforce is taken.

## THE RUN IS COMPLETE (2026-09-15)
0x42 Ganon -> take the Triforce of Power (walk straight at it) -> 0x32 north (walk_out_policy) ->
guard fires -> stand at X $70..$80 / Y $95 -> mode $13 -> credits to submode 4, no Start pressed.
Final: 372,090 frames, 10/13 hearts, 15 rupees, replay from power-on MATCH.

## GLEEOK, from the object jump table (2026-09-16) - and why the fight could not finish

Source: src/Z_07.asm UpdateObject_JumpTable, entries 42-46.

    42 UpdateGleeok      43 UpdateGleeok      44 UpdateGleeok      45 UpdateGleeok
    46 UpdateGleeokHead

So there are FOUR Gleeok body types (one per head count), and a fifth object - 0x46 - which is the
head that comes loose when its neck is cut and goes on flying and spitting fireballs.

zelda/boss.py knew only (0x43, 0x44). Two consequences, both measured with harness/probe_gleeok_diag.py:
- the tracker aims at one slot chosen from the BODY's slots 1-6, so a loose head sitting in another
  slot was never aimed at;
- the room-cleared flag $034D only latches when everything in the room is dead, so while a loose head
  lives the segment can never succeed, whatever the frame budget.

The evidence: at a 6,000-frame budget six attempts timed out with the body on 10, 8, 2, 10, 10, 10
health; at 10,000 they timed out with the body on 4-8 and Link down to 0.5-2.5 hearts - and nearly
every one of them left a 0x46 at FULL health (15). More time bought more damage taken, never a kill.

Fixed by teaching the tracker about loose heads anywhere in the object table (and chasing the nearest
one once the body's slots are empty), and by listing all five types in GLEEOK_TYPES.
