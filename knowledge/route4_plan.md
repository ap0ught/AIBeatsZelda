# Route 4 plan (2026-09-19) - glitchless, target: well under 40 minutes, stretch 35-36

Source: route_planner.py (reproduces run 3 at 41.33 vs 41.26 real), plan_legs.py, dungeon_paths.py,
knowledge/wr_route_comparison.md, journal 41. Dungeon order 3-1-4-8-2-5-7-6-9.

## Errand order (planner variant A: 39.24 min in the model, 42 rupees spare after the shops)
L3 -> heart rock 0x2C (bomb) -> +100 at 0x0F (hidden road from 0x1F) -> BLUE CANDLE at 0x0C -> WHITE SWORD 0x0A
(5 hearts = 3 + L3 + heart rock) -> L1 -> heart tree 0x47 (burn) -> L4 (ring shortcut) -> +100 at 0x6B (burn) ->
L8 -> L2 -> L5 -> whirlwind to L3's door -> arrows 0x44 -> bait 0x34 -> L7 (no candle cellar) -> MAGICAL SWORD 0x21
(12 hearts = 3 + seven dungeons + two) -> L6 -> whirlwind to L5's door -> L9.

## Legs (router; "D1F@128" = leave Down into 0x1F at x=128; use make_cross_at_policy(at=...))
start      -> L3            1783 frames,  7 screens: L76@141 U66@192 L65@189 L64@141 L63@141 D73@208 R74@141
L3         -> h_2C          3896 frames, 15 screens: L73@133 U63@208 R64@141 R65@141 U55@112 R56@141 U46@112 R47@141 R48@141 U38@112 U28@112 R29@173 R2A@173 R2B@173 R2C@173
h_2C       -> r100_0F       1344 frames,  5 screens: R2D@141 U1D@112 R1E@141 R1F@125 U0F@128
r100_0F    -> candle_0C     1365 frames,  5 screens: D1F@128 L1E@93 L1D@141 U0D@208 L0C@157
candle_0C  -> WS            1186 frames,  4 screens: D1C@80 L1B@141 L1A@141 U0A@208
WS         -> L1            2262 frames,  8 screens: D1A@208 L19@149 L18@149 L17@149 D27@160 R28@141 D38@112 L37@141
L1         -> h_47           771 frames,  3 screens: R38@141 D48@112 L47@141
h_47       -> L4            1088 frames,  4 screens: L46@157 D56@112 L55@141 U45@128
L4         -> r100_6B       2268 frames,  8 screens: D55@128 R56@141 R57@157 R58@157 D68@48 R69@141 R6A@173 R6B@173
r100_6B    -> L8            1133 frames,  4 screens: U5B@192 R5C@93 R5D@157 D6D@192
L8         -> L2             976 frames,  4 screens: U5D@192 U4D@192 L4C@141 U3C@112
L2         -> L5            2809 frames,  8 screens: D4C@112 R4D@125 U3D@48 U2D@112 L2C@189 U1C@48 L1B@141 U0B@112
L5         -> arrows_44  (wind to L3 first)    1089 frames,  5 screens: L73@125 U63@208 U53@208 R54@125 U44@112
arrows_44  -> bait_34        271 frames,  1 screens: U34@128
bait_34    -> L7            1244 frames,  5 screens: D44@128 D54@112 L53@125 L52@93 U42@112
L7         -> MS            2879 frames,  9 screens: D52@112 L51@125 D61@160 L60@125 U50@208 U40@224 R41@93 U31@32 U21@32
MS         -> L6             688 frames,  3 screens: D31@208 R32@141 U22@112
L6         -> L9         (wind to L5 first)    2302 frames,  8 screens: D1B@112 L1A@141 L19@141 L18@141 L17@141 U07@64 L06@141 L05@141

## How to build it (route4.py)
* Reuse route 3's segment tuples by NAME for every dungeon block (enter_Lx .. Lx_done) and for start..L3_done.
* Generate overworld connectors from the router path with exit coordinates (lanes!). Special screens:
  Lost Woods west-bound = the N,W,S,W sequence (woods_0..3); Lost Hills north = Up x4 (hills_1..4); 0x1F->0x0F =
  hold_through_policy(nav, 128, "Up", 0x0F) and back; raft = dock_policy; whirlwind = whirl_to_policy(nav, door).
* New errand segments: heart rock 0x2C = hc_cave_policy(nav, (144,173), "Up", "bomb") [check the method exists];
  candle shop 0x0C = shop_policy(nav, ram.CANDLE?) + cave_exit_policy; +100 0x6B = burn cave (was in run 2:
  knowledge says (128,141) facing Down); heart tree 0x47 = existing hc_cave_policy(nav,(176,157),"Down","burn").
* Level 4: after the ladder 32 -> 31 -> 30 -> N(locked) 20 -> E 21 (outer ring) -> dash-bomb N -> 11 (dark) ->
  dash-bomb E -> 12 -> 13. Probe l4_ring: 20->21 395 frames, 21->11 590-830. Needs 2 bombs in hand at room 20.
* Level 7: drop l7_1a_st and l7_candle (blue candle already owned). Level 8's door burns with the blue candle
  (one flame per screen: if it misses, leave the screen and come back).
* Level 2: drop the 3F bombs detour only if the bomb budget allows.
* KEYS and BOMBS must be re-budgeted for the order 3-1-4-8-2-5-7-6-9 (run 3's per-dungeon entry/exit counts are
  in the checkpoints: fullgame_enter_Lx / Lx_done -> keys, bombs). Level 8 early nets +2 keys.
* Bomb supply: read the consecutive-kill counter from RAM and make the 10th kill with a bomb when bombs are low
  (forced bomb drop); success tests should refuse to commit a dungeon-leaving segment below the next need.
