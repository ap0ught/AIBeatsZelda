"""ROUTE 4 - the errand order the route planner found (knowledge/route4_plan.md, journal 41), glitchless.

    L3 -> heart rock 0x2C -> +100 at 0x0F -> BLUE CANDLE 0x0C -> WHITE SWORD (five hearts, before Level 1) -> L1 ->
    heart tree 0x47 -> L4 (outer-ring bomb shortcut) -> +100 at 0x6B -> L8 -> L2 -> L5 -> wind, arrows, bait -> L7
    (no candle cellar) -> MAGICAL SWORD (twelve hearts) -> L6 -> wind -> L9.

Built from route 3's own segment tuples wherever the third run already walked that screen or room - the policies
and success tests are the tested ones - plus a dozen new connectors (pinned to the router's lanes) and the new
errands. Dungeon blocks are reused whole; Level 4 swaps rooms 10-00-01-02 for 21-11 (two bombs) and Level 7 drops
its candle cellar."""
from __future__ import annotations

from zelda import ram
from zelda.lookahead import Goal
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
    # ---- Level 1 with the White Sword ----------------------------------------------------------------------
    S += take("l4w00_1a")
    S.append(lane("ws_19", "Left", 0x19, 149))            # straight west: the third run doubled back through 1B
    S += take("l4w04_18", "l4w05_17", "l4w06_27", "l4w07_28", "l4w08_38", "ow1_37")
    S += block("enter_L1", "warp_L1")
    # ---- heart tree, Level 4 -------------------------------------------------------------------------------
    S += take("ws_38", "l4w09_48", "l4w10_47")
    S.append(("h47_heart", lambda nav: fg.hc_cave_policy(nav, (176, 157), "Down", "burn"),
              lambda emu, s: (s.containers >= started().containers + 1 and s.level == 0 and s.mode == 5
                              and s.hearts > 0), 40))
    S += take("l4w11_46", "l4w12_56", "l4w13_55", "l4_sail")
    S += block("enter_L4", "l4_20")
    # THE OUTER RING. 20's east door is open; 21 is a moat with an island, and the ring outside the moat runs round
    # to the north wall, which is bombable, as is 11's east wall. Two bombs for three rooms, a fight, an old man's
    # speech and the ladder room (probe l4_ring: 395 + 590-830 frames).
    # It takes TWO bombs, and bombs are whatever the drops gave. So both roads are in the list and each segment
    # only acts when Link is standing where it starts: with two bombs in room 20 the ring, otherwise the third
    # run's road round the top (10, 00, 01, 02). A segment that does not apply passes in two frames.
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
    # ---- the second hundred, Level 8, Level 2 --------------------------------------------------------------
    S += take("l2_sail", "l2w00_56", "l2w01_57", "l2w02_58")
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
