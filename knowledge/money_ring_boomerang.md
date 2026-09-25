# Money, the Blue Ring, the boomerang and the bomb upgrade — settled 2026-09-16

The owner asked (mid-run, Level 6): get the 100- and 30-rupee caves; consider the 250-rupee ring that halves
damage "if it makes sense"; "our main goal is to win quickly"; and "those orange and blue ghosts ... get stunned
if you hit them with a boomerang im pretty sure". A 10-agent workflow read the zelda1 disassembly
(github.com/aldonunez/zelda1-disassembly) and decoded the Rev 1 ROM directly, cross-checked guides, re-ranked
the logged attempts of the first run, and had skeptics re-derive the key claims. Probes confirmed the rest.

## The ghosts are Wizzrobes, and the boomerang goes straight through them
- Red Wizzrobe 0x24 (orange) and Blue Wizzrobe 0x23 run their own collision routine
  (Wizzrobe_DrawAndCheckCollisions, Rev 1 file 0x12050): mask $F6, checks sword slot $0D, sword/rod shot $0E,
  bomb/fire $10/$11, then Link. Never the boomerang ($0F) or arrows ($12). Attr $81 skips the generic check.
  Two independent reads of the disassembly against the ROM bytes agree.
- Only the sword, sword beams and bombs hurt them. HP: red $40 (2 White Sword hits, 1 Magical, 1 bomb),
  blue $A0 (5 White, 3 Magical, 3 bombs).
- The boomerang DOES stun (~150-160 frames, 0 damage, harmless by touch while stunned): Like Like 0x17,
  Vire 0x12 (and it does not split), Zol 0x13 (no split), Gibdo 0x30, Goriya, Lynel, Moblin, Octorok,
  Tektite, Wallmaster, surfaced Leever, landed Peahat, ground Ghini. It KILLS Keese 0x1B-0x1D and Gels
  0x14/0x15 (HP 0). NO effect: Darknuts (clink), Pols Voice, Gohma, Patra and eyes, Gleeok, Manhandla,
  Aquamentus, Dodongo, Ganon, Bubbles, big Digdogger, blade traps. A stun does not free Link once a Like Like
  has already grabbed him.
- Not added to the planner: a stun is not a kill, the winners in those rooms already finish near full hearts,
  and it would be new planner code in a live run.

## The Blue Ring
- Sold ONLY at overworld 0x34 (E-4, the graveyard shop the run already uses for bait): Key 80 (x=88),
  BLUE RING 250 (x=120), Bait 60 (x=152). Cave type 0x20; no other screen sells item 0x12. Overworld 0x7C is
  a money-making game, not a shop (the old "7C" note meant something else).
- Effect (Link_BeHarmed, file 0x73CF): damage shifted right once per ring level - halves ALL health damage
  (Red Ring quarters). Knockback, shield-eating and grabs unchanged.
- Worth in frames: re-ranking the first run's logged attempts with halved damage saves ~0 frames at the only
  point Link could afford it (after heart container #12, with a second +100 cave), ceiling ~450. Cost
  ~5,000-9,300 frames (detour to 0x34, extra caves, arrow money after). REJECTED for speed.

## Bomb capacity upgrades
- Two in the first quest, 100 rupees each, +4 cap, and the purchase REFILLS bombs to the new cap
  (Z_01.asm: LDA MaxBombs / ADC #4 / STA MaxBombs / STA InvBombs). Person type 0x4F.
  Level 5 room 0x17 (bomb 0x16's east wall; 0x16 reached from 0x06 through a locked door). Level 7 room 0x48
  (0x58's locked north door; 0x58 is open to 0x59). Buy by standing at x=120, y 147-157; ~220-frame text freeze.
- Level 5's is behind the run; Level 7's needs 100 rupees at 0x59 (Link ~87) and costs ~1,500-2,000 frames plus
  a key. REJECTED for speed.

## Money on the rest of the route
- Only arrows remain to pay for: Gohma 2, Pols Voices 8-10, Level 9 room 0x14 Like Likes 13-27, Ganon a few.
  ganon_policy gives up at 0 rupees.
- So cave_6b (+100, ~1,200 frames) now runs only when the purse is under ARROW_PURSE = 60
  (fullgame.purse_or_cave_policy); otherwise it is a 2-frame segment.
- Probes (probe_l9_14_dash.py, probe_l8_pols.py): a damage-aware dash cannot cross 0x14's Like Likes (3/3
  timeouts) and the sword cannot beat 8 Pols Voices in 4,000 frames (3/3); the bow fights stay.

## Secret money caves, first quest (ROM decode + RPGClassics + Mariner FAQ + in-game)
| Room | Rupees | Opens with | Spot |
|---|---|---|---|
| 0x0F | 100 | walk-in | hold Up at x=128 from 0x1F (TAKEN this run) |
| 0x62 | 100 | candle | tree (128,96); burn ONLY from (96,93) facing Right or (160,93) facing Left - (112,93)/(144,93) miss by 16 px. Exit (96,125) is in the west half. Probe probe_cave_62b.py: +100 from the west pocket |
| 0x6B | 100 | candle | (128,141) facing Down (verified) |
| 0x3D | 30 | touch right Armos | (144,109) facing Down (TAKEN) |
| 0x67 | 30 | bomb | (112,93) Up (TAKEN) |
| 0x28 | 30 | candle | (208,141) Down (verified earlier) |
| 0x48 | 30 | candle | ONLY from (176,93)/(176,109) facing Right |
| 0x2D | 30 | bomb | (80,93) facing Up (the old (112,77) spot was 16 px off) |
| 0x71 | 30 | bomb | (80,93) Up. NOT 0x70 (a pay-me hint cave). Reached from 0x62 west half -> 0x72 -> 0x71; back up into 0x61 |
| 0x13 | 30 | bomb | wall (32,80): the guide's "NE of Level 6"; 0x22 has no north exit, ~6 screens on foot |
| 0x4E | 10 | touch right Armos | (160,109) |
| 0x51, 0x56, 0x5B | 10 | candle | lone trees |
| 0x53 | 100? | ? | ROM cave type 0x22 lead, unverified |
Also: 0x6F is a shop (Magical Shield 130, Bombs 20, Arrows 80), contradicting an old route comment.
