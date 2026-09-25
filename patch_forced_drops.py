"""Bombs on demand. The cartridge counts kills in a row without Link being hit (HelpDropCount, $50); the TENTH
is a guaranteed drop - five rupees, or BOMBS if that kill's damage was a bomb's (HelpDropValue, $51). A hit
resets the count (Z_01 Link_BeHarmed). Human runners count kills for exactly this; the fourth run died at a wall
with no bombs because the bot treated drops as weather.

plan_fight now reads the count once per decision. With the ninth kill banked, bombs wanted (fewer in hand than
BOMB_TARGET) and one to spare, it offers bomb macros whatever the usual thrift says, pays well for the blast that
makes the tenth kill, and frowns on wasting the tenth on a sword swing. While a streak is building it prices
damage higher, because a hit throws the streak away."""
import pathlib

p = pathlib.Path("zelda/lookahead.py")
t = p.read_text(encoding="utf-8")

old = "OLD_PLANNER = [False]"
new = ("BOMB_TARGET = [6]             # plan_fight works the ten-kill forced drop for bombs while Link holds fewer than this\n"
       + old)
assert t.count(old) == 1
t = t.replace(old, new, 1)

old = """            offer_bombs = s0.bombs > (0 if use_bombs == "free" else 2) and near_target and s0.level != 9 and (
                use_bombs == "free" or (use_bombs == "sparing" and cluster >= 3))
"""
new = """            offer_bombs = s0.bombs > (0 if use_bombs == "free" else 2) and near_target and s0.level != 9 and (
                use_bombs == "free" or (use_bombs == "sparing" and cluster >= 3))
            if streak_bomb and near_target:
                offer_bombs = True               # the tenth kill, made with a bomb, pays four bombs back
"""
assert t.count(old) == 1
t = t.replace(old, new)

old = """        urgency = 1.0 + URGENCY * (frames / max_frames)
        dmg_w = damage_weight * caution(s0)
"""
new = """        urgency = 1.0 + URGENCY * (frames / max_frames)
        dmg_w = damage_weight * caution(s0)
        if want_bombs and 5 <= help_n < 10:
            dmg_w *= 1.5                          # a hit resets the streak
"""
assert t.count(old) == 1
t = t.replace(old, new)

old = """        tlist = targets(emu) if targets is not None else [
            e for e in read_enemies(emu) if killable(e) and e[0] not in ignore]
        near_target = any(max(abs(t[2] - s0.x), abs(t[3] - s0.y)) <= 48 for t in tlist)
"""
new = """        tlist = targets(emu) if targets is not None else [
            e for e in read_enemies(emu) if killable(e) and e[0] not in ignore]
        near_target = any(max(abs(t[2] - s0.x), abs(t[3] - s0.y)) <= 48 for t in tlist)
        help_n = emu.byte(0x50)                   # kills in a row since Link was last hit
        want_bombs = (not OLD_PLANNER[0]) and 1 <= s0.bombs < BOMB_TARGET[0] and use_bombs != "never"
        streak_bomb = want_bombs and help_n == 9
"""
assert t.count(old) == 1
t = t.replace(old, new)

old = """            # spending a bomb has to pay for itself: the score already gives 150 a kill, so this
            # is worth it for three at once or for something the sword cannot hurt, not otherwise
            if m[0] == "bomb" and use_bombs != "free":
                sc -= 320
"""
new = """            # spending a bomb has to pay for itself: the score already gives 150 a kill, so this
            # is worth it for three at once or for something the sword cannot hurt, not otherwise
            if m[0] == "bomb" and use_bombs != "free":
                sc -= 320
            if streak_bomb and n1 < n0:
                if m[0] == "bomb" and emu.byte(0x51):
                    sc += 1200                    # the tenth kill was the bomb's: four bombs are on the floor
                elif m[0] != "bomb":
                    sc -= 500                     # the tenth kill wasted on five rupees
"""
assert t.count(old) == 1
t = t.replace(old, new)
p.write_text(t, encoding="utf-8")

k = pathlib.Path("knowledge/wr_route_comparison.md")
kt = k.read_text(encoding="utf-8")
kt = kt.replace("  A hit on Link resets $50 (Z_04 ~6049), so a streak is worth protecting when bombs or rupees are short.",
                "  A hit on Link resets $50, $51 AND $627 (Z_01 Link_BeHarmed - the whirlwind's 'harm' too), so a streak is\n"
                "  worth protecting when bombs or rupees are short. Dodongo's death SETS $50=$51=10: the next kill after\n"
                "  Level 2's boss drops bombs for certain.")
k.write_text(kt, encoding="utf-8")
print("patched plan_fight: forced bomb drops")
