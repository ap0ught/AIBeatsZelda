"""ROUTE 5 - route 4 with the Level 1 and Level 4 blocks transposed: GLEEOKE FIRST, then Level 1.

    L3 -> heart rock 0x2C -> +100 at 0x0F -> BLUE CANDLE 0x0C -> WHITE SWORD (five hearts, before either) ->
    heart tree 0x47 (burn) -> L4 (outer-ring bomb shortcut) -> L1 -> +100 at 0x6B -> L8 -> L2 -> L5 -> wind,
    arrows, bait -> L7 (no candle cellar) -> MAGICAL SWORD (twelve hearts) -> L6 -> wind -> L9.

Legal because Gleeok needs the White Sword and NOT the bow, and five hearts are reachable without Level 1
(3 + L3 + heart rock 0x2C). The candle is bought before the sword, so 0x47 can burn on the way to L4 too.

The swap costs 14 seconds on the whole game (route_planner: 39.24 -> 39.48 min) and puts Gleeok on the table at
**11:23 in-game** instead of 13:42, with Level 1 done by 14:03 - ~1.6 h of search for a run route 4 cannot reach
at that stop. That is the whole reason this file exists: it is the cheapest genuinely NEW run.

Two legs are new and neither is proven by a frame: White Sword -> L4's door and L4 -> L1's door. Both were priced
by the router and both sets of lane coordinates were then CHECKED against the map, tile by tile, before being
written here - every `lane()` below asserts nothing, but zelda/owroute.free() was asked directly whether both
ends of the seam are walkable on the 8 px lattice. See the docstring on each lane group. A wrong coordinate does
not fail: _lane() falls back to "leave wherever you can", so the symptom would be a mysteriously slow search
rather than an error - which is exactly why they were verified here instead of trusted.

The third leg, L1 -> 0x6B, deliberately does NOT take the router's own shortest way. The router wants
0x58 -> 0x59 -> down the ladder hole into 0x69 (1850 frames), and route 5 walks 0x58 -> 0x68 -> 0x69 -> 0x6A ->
0x6B instead (1893 frames, +43). The router's road depends on a ladder seam that a fall can trap Link in, and
0x68 -> 0x69 -> 0x6A -> 0x6B is the road run6 actually walked. 43 frames is not worth the risk.

Everything else is route 4 or route 3's own segments, reused by name. No policy is rewritten here: the dungeon
blocks are the tested ones, and the only segments with new policies are the heart-tree burn and the errand shops,
which route 5 inherits unchanged."""
from __future__ import annotations

from zelda import ram
from zelda.segments import make_cross_policy, make_cross_at_policy


def _lane(d: str, at: int):
    """Leave by the router's lane; if the navigator cannot pin it (an enemy parked there, a tile it reads
    differently), leave wherever it can - the search still sees both outcomes."""
    def factory(nav):
        pinned, free = make_cross_at_policy(nav, d, at=at), make_cross_policy(nav, d)

        def policy(emu, rec, rng, max_frames):
            out = pinned(emu, rec, rng, max_frames)
            if isinstance(out, str) and out.startswith("nav:") and emu.state().mode == 5:
                out = free(emu, rec, rng, max_frames)
            return out
        return policy
    return factory


def build(base: list, fg) -> list:
    by = {s[0]: s for s in base}
    names = [s[0] for s in base]

    def block(first: str, last: str, drop=()) -> list:
        i, j = names.index(first), names.index(last)
        return [s for s in base[i:j + 1] if s[0] not in drop]

    def take(*ns) -> list:
        return [by[n] for n in ns]

    def ok(room):
        return lambda emu, s: s.room == room and s.mode == 5 and s.hearts > 0 and s.level == 0

    def dok(room, level):
        return lambda emu, s: s.room == room and s.mode == 5 and s.hearts > 0 and s.level == level

    def started():
        from zelda import runner as zrunner
        return zrunner.SEG_START

    def lane(name, d, room, at, tries=40):
        return (name, _lane(d, at), ok(room), tries)

    S = []
    # ---- power-on, Level 3 --------------------------------------------------------------------------------
    S += block("start", "warp_L3")
    # ---- north-east: heart rock, the hidden hundred, the candle, the White Sword ---------------------------
    # Identical to route 4 up to and including the White Sword. This is the shared prefix both orders start from.
    S += take("ow1_73", "ow1_63", "ow1_64", "ow1_65", "ow1_66", "ow1_67", "ow1_68", "ow1_58", "ow1_48", "ow1_38",
              "ws_28", "ws_29", "ws_2a", "ws_2b", "ws_2c")
    # HEART ROCK: the fifth heart is what the White Sword asks for, and this one is on the road to it.
    S.append(("h2c_heart", lambda nav: fg.hc_cave_policy(nav, (144, 173), "Up", "bomb"),
              lambda emu, s: (s.containers >= started().containers + 1 and s.level == 0 and s.mode == 5
                              and s.hearts > 0 and s.room == 0x2C), 40))
    S.append(lane("h2c_2d", "Right", 0x2D, 141))
    S += take("c0f_1d", "c0f_1e", "c0f_1f", "c0f_0f")
    S.append(("cave_0f", lambda nav: fg.secret_cave_policy(nav, None, "Up", "walk", want=100),
              lambda emu, s: (s.hearts > 0 and s.room == 0x0F and s.level == 0 and s.mode == 5
                              and emu.byte(0x66D) >= started().rupees + 95), 30))
    S += take("c0f_b1f", "c0f_b1e", "c0f_b1d")
    S.append(lane("cdl_0d", "Up", 0x0D, 208))
    S.append(lane("cdl_0c", "Left", 0x0C, 157))
    # THE BLUE CANDLE, 60 rupees, the right-hand ware (the other two would eat the hundred: walk into that one only)
    S.append(("buy_candle", lambda nav: fg.shop_policy(nav, ram.CANDLE, xs=(152,)),
              lambda emu, s: s.hearts > 0 and emu.byte(ram.CANDLE) > 0, 25))
    S.append(("candle_leave", lambda nav: fg.cave_exit_policy(nav),
              lambda emu, s: s.mode == 5 and s.level == 0 and s.hearts > 0, 20))
    S.append(lane("cdl_1c", "Down", 0x1C, 80))
    S += take("ws_1b", "ws_1a", "ws_0a", "white_sword")
    # ---- NEW LEG 1 of 2: the White Sword -> the heart tree at 0x47 (route 4 walked L1's door here) ----------
    # Router, 2443 frames, 9 screens: D1A@208 L19@149 L18@149 L17@149 D27@160 R28@141 D38@112 D48@112 L47@141
    # The first seven crossings are route 3's own segments for the White Sword -> Level 1 door walk, reused
    # verbatim; route 4 pinned 0x19 by hand because the third run doubled back through 0x1B. Only the last two
    # differ from route 4's road, and both are route 3 segments the L1 -> 0x47 leg already proved in run6.
    S += take("l4w00_1a")
    S.append(lane("ws_19", "Left", 0x19, 149))
    S += take("l4w04_18", "l4w05_17", "l4w06_27", "l4w07_28", "l4w08_38", "l4w09_48", "l4w10_47")
    S.append(("h47_heart", lambda nav: fg.hc_cave_policy(nav, (176, 157), "Down", "burn"),
              lambda emu, s: (s.containers >= started().containers + 1 and s.level == 0 and s.mode == 5
                              and s.hearts > 0), 40))
    # ---- Level 4, reached exactly as route 4 reaches it: west, south, and the raft off the island -----------
    S += take("l4w11_46", "l4w12_56", "l4w13_55", "l4_sail")
    S += block("enter_L4", "l4_20")
    # THE OUTER RING. 20's east door is open; 21 is a moat with an island, and the ring outside the moat runs round
    # to the north wall, which is bombable, as is 11's east wall. Two bombs for three rooms, a fight, an old man's
    # speech and the ladder room (probe l4_ring: 395 + 590-830 frames).
    # It takes TWO bombs, and bombs are whatever the drops gave - which in route 5 is a different set again, because
    # Level 1 has not been walked yet. So both roads are in the list and each segment only acts when Link is
    # standing where it starts: with two bombs in room 20 the ring, otherwise the third run's road round the top
    # (10, 00, 01, 02). A segment that does not apply passes in two frames. This is the same guard route 4 uses,
    # and it is the reason the transposed order is safe at all: Level 4 degrades to the bombless road on its own.
    def when(cond, seg):
        name, factory, success, tries = seg

        def fac(nav):
            pol = factory(nav)

            def policy(emu, rec, rng, max_frames):
                if not cond(emu.state()):
                    rec.step((), 2)
                    return "not this road"
                return pol(emu, rec, rng, max_frames)
            return policy

        def good(emu, s):
            if not cond(started()):
                return s.hearts > 0 and s.mode == 5
            return success(emu, s)
        return (name, fac, good, tries)

    in4 = lambda room: (lambda q: q.level == 4 and q.room == room)
    S.append(when(lambda q: q.level == 4 and q.room == 0x20 and q.bombs >= 2,
                  ("l4_21", lambda nav: make_cross_policy(nav, "Right"), dok(0x21, 4), 50)))
    S.append(when(in4(0x21), ("l4_11", lambda nav: fg.dash_bomb_policy(nav, "Up", 0x11), dok(0x11, 4), 60)))
    S.append(when(in4(0x11), ("l4_12r", lambda nav: fg.dash_bomb_policy(nav, "Right", 0x12), dok(0x12, 4), 60)))
    for n, room in (("l4_10", 0x20), ("l4_00", 0x10), ("l4_01", 0x00), ("l4_02", 0x01), ("l4_12", 0x02)):
        S.append(when(in4(room), by[n]))
    S += block("l4_13", "warp_L4")
    # ---- NEW LEG 2 of 2: L4 -> Level 1's door (route 4 walked L2's door here) --------------------------------
    # Router, 1859 frames, 7 screens: D55@128 R56@141 U46@112 R47@141 R48@141 U38@112 L37@141
    # Every lane below was checked against zelda/owroute.free() before it was written: both ends of every seam are
    # walkable on the 8 px lattice. 0x46's own left edge is NOT walkable at y=112 or y=141, so the approach has to
    # come from 0x56 above rather than straight across from the island - which is what the router says, and is why
    # the raft ride back is not optional.
    S += take("l2_sail")
    S.append(lane("r5_56_46", "Up", 0x46, 112))
    S.append(lane("r5_46_47", "Right", 0x47, 141))
    S.append(lane("r5_47_48", "Right", 0x48, 141))
    S.append(lane("r5_48_38", "Up", 0x38, 112))
    S.append(lane("r5_38_37", "Left", 0x37, 141))
    # ---- Level 1, entered with the White Sword already in hand --------------------------------------------------
    S += block("enter_L1", "warp_L1")
    # ---- Level 1 -> the second hundred at 0x6B, on run6's road ------------------------------------------------
    # 0x37 -> 0x38 -> 0x48 -> 0x58 -> 0x68 -> 0x69 -> 0x6A -> 0x6B. ws_38 is route 3's own crossing into 0x38;
    # r5_38_48 and r5_58 are the two new ones; the four r6b_* lanes are run6's, reused verbatim. Note this leg's
    # 0x38 -> 0x48 is the SAME seam route 4 crossed as l4w09_48, so it cannot reuse that name - a segment name may
    # appear once per run, and run.segment() keys checkpoints and the recorded input log on it.
    S += take("ws_38")
    S.append(lane("r5_38_48", "Down", 0x48, 112))
    S.append(lane("r5_58", "Down", 0x58, 112))
    S.append(lane("r6b_68", "Down", 0x68, 48))
    S.append(lane("r6b_69", "Right", 0x69, 141))
    S.append(lane("r6b_6a", "Right", 0x6A, 173))
    S.append(lane("r6b_6b", "Right", 0x6B, 173))
    S.append(("cave_6b", lambda nav: fg.burn_cave_policy(nav, (128, 141), "Down"),
              lambda emu, s: (s.hearts > 0 and s.level == 0 and s.mode == 5
                              and emu.byte(0x66D) >= started().rupees + 95), 40))
    S.append(lane("l8a_5b", "Up", 0x5B, 192))
    # pinned: 0x5C is split into lanes, and the bottom one (where an unpinned crossing from here lands) is a dead end
    S.append(lane("l8a_5c", "Right", 0x5C, 93))
    S.append(lane("l8a_5d", "Right", 0x5D, 157))
    S.append(lane("l8a_6d", "Down", 0x6D, 192))
    S += block("enter_L8", "warp_L8")
    # ---- from here on, route 5 IS route 4 ---------------------------------------------------------------------
    # The Triforce warp sets Link down LEFT of Level 8's stairs, at (96,93) - and the only way east from there is
    # over the stairs, back into the dungeon (sixty attempts did exactly that). North by the x=48 lane instead.
    S.append(lane("l2b_5d", "Up", 0x5D, 48))
    S.append(lane("l2b_4d", "Up", 0x4D, 48))
    S.append(lane("l2b_4c", "Left", 0x4C, 141))
    S.append(lane("l2b_3c", "Up", 0x3C, 112))
    S += block("enter_L2", "warp_L2")
    # ---- Level 5 -------------------------------------------------------------------------------------------
    S += take("l5w00_4c", "l5w01_4d", "l5w02_3d", "l5w03_2d", "l5w04_2c", "l5w05_1c", "l5w06_1b",
              "hills_1", "hills_2", "hills_3", "hills_4")
    S += block("enter_L5", "warp_L5")
    # ---- the wind to the shops, Level 7 ---------------------------------------------------------------------
    S += block("sw_w45", "food_leave")
    # the router's lanes from the bait shop to the pond: 0x52 is two canyons that never meet
    S.append(lane("p7b_44", "Down", 0x44, 128))
    S.append(lane("p7b_54", "Down", 0x54, 112))
    S.append(lane("p7b_53", "Left", 0x53, 125))
    S.append(lane("p7b_52", "Left", 0x52, 93))
    S.append(lane("p7b_42", "Up", 0x42, 112))
    S += block("l7_drain", "warp_L7", drop=("l7_1a_st", "l7_candle"))
    # ---- the Magical Sword on the way to Level 6 -------------------------------------------------------------
    S += take("w8_52", "l7_62", "l7_61", "woods_0", "woods_1", "woods_2", "woods_3",
              "l7w20_50", "l7w21_40", "l7w22_41", "l7w23_31", "ms_21", "ms_sword")
    S.append(lane("ms_b31", "Down", 0x31, 208))
    S += take("l7w24_32", "l6_22")
    S += block("enter_L6", "warp_L6")
    # ---- Level 9 ---------------------------------------------------------------------------------------------
    S += block("dm9_w0b", "g9_credits")
    seen = set()
    for s in S:
        assert s[0] not in seen, f"segment name used twice: {s[0]}"
        seen.add(s[0])
    return S
