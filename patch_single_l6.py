"""Climb Level 6 ONCE.

The owner, watching the first finished run: "you also go in and out of level 6 a lot for some reason."
The reason was money. Link reached Level 6 broke, climbed to 0x28 (one door from the Gleeok), walked out,
rode the whirlwind east, walked to the arrows shop on 0x44, rode back to Level 3, walked the Lost Woods
again and climbed the same eight rooms a second time - about 25,000 frames, seven minutes of video.

The caves pay for the arrows before Level 5 now (Link has 193 rupees there), and the walk from Level 5
already passes 0x64, two screens south of the shop. So: at 0x64 go up to the arrows (0x44) and the bait
(0x34, one more screen), come back down 0x54 and west along 0x53 and 0x52 to 0x62, and carry on into the
Lost Woods exactly as before. Every crossing in that detour was already made by an earlier run
(64->54->44 on the old shop walk; 44->34 and 34->44->54->53->52 on the old bait expedition), and the one
new join, 52->62 arriving from the east, went 6/6 in probe_52_south.py.

It also drops the pointless 62 -> 52 -> 42 -> 52 -> 62 loop the old walk made on the way to the woods.

usage: python patch_single_l6.py      (edits fullgame.py + zelda/intent.py; does NOT touch checkpoints)
"""
import ast
import pathlib


def load(path):
    raw = pathlib.Path(path).read_bytes()
    return raw.decode("utf-8").replace("\r\n", "\n"), b"\r\n" in raw


def save(path, t, crlf):
    ast.parse(t)
    pathlib.Path(path).write_bytes((t.replace("\n", "\r\n") if crlf else t).encode("utf-8"))


t, crlf = load("fullgame.py")


def sub(old, new, what):
    global t
    n = t.count(old)
    assert n == 1, f"{what}: {n} matches"
    t = t.replace(old, new)
    print(f"  applied: {what}")


# ---- 1. stop the Level 5 walk at 0x64 and shop from there
sub('''    for i, (d, room) in enumerate(zip(L5_TO_L7_DIRS, L5_TO_L7_ROOMS)):
        S.append((f"l7w{i:02d}_{room:02x}",) + cross(d, room, 40))
''', '''    for i, (d, room) in enumerate(zip(L5_TO_L7_DIRS, L5_TO_L7_ROOMS)):
        S.append((f"l7w{i:02d}_{room:02x}",) + cross(d, room, 40))
        if room == 0x64:
            break
    # --- SHOPPING ON THE WAY WEST. The arrows shop (0x44) is two screens north of this one and the
    # graveyard that sells monster bait (0x34) is one more. Gohma in Level 6 needs the arrows and the
    # Goriya in Level 7 needs the bait, and the caves already paid for both (140 rupees). The old route
    # shopped from INSIDE Level 6 instead - out, across the map, back, and the same eight rooms climbed
    # twice - which is what the owner saw in the video as going "in and out of level 6 a lot".
    S.append(("sh7_54",) + cross("Up", 0x54, 40))
    S.append(("sh7_44",) + cross("Up", 0x44, 40))
    S.append(("buy_arrows", lambda nav: shop_policy(nav, ram.ARROWS),
              lambda emu, s: s.hearts > 0 and emu.byte(ram.ARROWS) > 0, 25))
    S.append(("shop_leave", lambda nav: cave_exit_policy(nav),
              lambda emu, s: s.mode == 5 and s.level == 0 and s.hearts > 0, 20))
    S.append(("bait_34",) + cross("Up", 0x34, 40))
    S.append(("buy_food", lambda nav: grave_shop_policy(nav, ram.BAIT),
              lambda emu, s: s.hearts > 0 and emu.byte(ram.BAIT) > 0, 25))
    S.append(("food_leave", lambda nav: cave_exit_policy(nav),
              lambda emu, s: s.mode == 5 and s.level == 0 and s.hearts > 0, 20))
    S.append(("bait_44",) + cross("Down", 0x44, 40))
    # and back to the road west: 54, then along 53 and 52 (the old bait expedition's way back) to 62.
    S.append(("fw7_54",) + cross("Down", 0x54, 40))
    S.append(("fw7_53",) + cross("Left", 0x53, 40))
    S.append(("fw7_52",) + cross("Left", 0x52, 40))
''', "shop at 0x44 and 0x34 on the walk west")

# ---- 2. the old walk went on 63 -> 62 -> 52 -> 42 and then straight back down 52 to 62
sub('''    S.append(("l7_52",   lambda nav: make_cross_policy(nav, "Down"),  ok(0x52), 40))
''', '', "drop the 42 -> 52 backtrack")

# ---- 3. Level 6 climbed once: cut from the walk-out at 0x28 to the end of the second climb
a = t.index("    # NOT into 18 yet.")
b = t.index('    S.append(("r6_18",')
cut = t[a:b]
for must in ('"l6_out"', '"whirl_east"', '"whirl_l3"', '"l6_return"', '"r6_28"', '"buy_arrows"', '"bait_44"'):
    assert must in cut, must
t = t[:a] + '''    # Straight on into 18. Link used to turn round here - one door from the Gleeok - walk out, go
    # shopping for the arrows across the map and climb these same eight rooms a second time: 25,000
    # frames. The arrows and the bait are bought on the walk west now, so Level 6 is climbed once.
''' + t[b:]
print("  applied: Level 6 climbed once (l6_out ... r6_28 removed)")
save("fullgame.py", t, crlf)

# ---- captions for the new names
t, crlf = load("zelda/intent.py")
sub('''    ("m7", "CROSSING TO THE SHOPS",''', '''    ("sh7", "UP TO THE ARROWS SHOP", "It is two screens off the road west. Buying here, on the way, is "
                                     "what lets Level 6 be climbed once instead of twice."),
    ("bait_", "THE GRAVEYARD SHOP", "Monster bait is sold under a gravestone, one screen north of the "
                                    "arrows."),
    ("fw7", "BACK ON THE ROAD WEST", "Arrows and bait bought. Next: the Lost Woods, and Level 6 behind "
                                     "them."),
    ("m7", "CROSSING TO THE SHOPS",''', "caption families sh7 / bait_ / fw7")
sub('''    "buy_arrows": ("BUYING ARROWS", "Gohma takes arrows and nothing else. They are sold, not found."),''',
    '''    "buy_arrows": ("BUYING ARROWS", "Gohma takes arrows and nothing else. They are sold, not found - "
                                    "and the secret caves already paid for them."),
    "r6_18": ("INTO THE GLEEOK'S ROOM", "The shutters close behind Link, so the search sends him in with "
                                        "as many hearts as it can find."),''', "caption r6_18")
save("zelda/intent.py", t, crlf)

import importlib  # noqa: E402
import fullgame  # noqa: E402
from zelda import intent  # noqa: E402
importlib.reload(fullgame)
names = [s[0] for s in fullgame.segments()]
assert len(names) == len(set(names)), "duplicate names"
for gone in ("l6_out", "l6_back", "shop_out", "whirl_east", "whirl_l3", "l6_return", "r6_7a", "r6_28",
             "l7w14_63", "l7w17_42", "l7_52", "shop14_54", "bwoods_0"):
    assert gone not in names, gone
i = names.index("l7w13_64")
print(f"\n{len(names)} segments")
print("  walk west:", names[i:i + 18])
j = names.index("l6_28")
print("  Level 6:  ", names[j - 2:j + 4])
for n in names[i:i + 18] + ["r6_18"]:
    print(f"     {n:12s} {intent.for_segment(n)[0]}")
