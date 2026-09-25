"""Level 5 -> the shops by whirlwind: two notes to Level 4's island, the raft back to the mainland, four screens.
probe_shop_whirl.py: ~1,900 frames from Level 5's door to the arrows shop's screen, against seventeen screens on
foot (~5,900 frames in the second run)."""
import ast, pathlib
p = pathlib.Path("fullgame.py"); raw = p.read_bytes(); crlf = b"\r\n" in raw
t = raw.decode("utf-8").replace("\r\n", "\n")
old = '''    S.append(("l7_1b",  lambda nav: make_cross_policy(nav, "Down"), ok(0x1B), 40))
    for i, (d, room) in enumerate(zip(L5_TO_L7_DIRS, L5_TO_L7_ROOMS)):
        S.append((f"l7w{i:02d}_{room:02x}",) + cross(d, room, 40))
        if room == 0x64:
            break
'''
new = '''    # THE WHIRLWIND TO THE SHOPS. Link owns the recorder now, and the wind stops at every finished dungeon.
    # Level 4's island door (0x45) is the raft ride and four screens from the arrows shop; Level 5's door
    # is seventeen screens from it on foot. The counter ($523) sits on Level 1: two notes facing Left move it
    # to Level 5 and then Level 4, one ride. Probe: ~1,900 frames door to shop screen, against ~5,900.
    S.append(("sw_w45", lambda nav: whirl_to_policy(nav, 0x45),
              lambda emu, s: s.room == 0x45 and s.level == 0 and s.mode == 5 and s.hearts > 0, 30))
    S.append(("sw_sail", dock_policy, lambda emu, s: s.room == 0x55 and s.mode == 5 and s.hearts > 0, 20))
    S.append(("sw_land", lambda nav: settle_policy(nav, lambda q: q.y >= 125 and q.mode == 5),
              lambda emu, s: s.room == 0x55 and s.mode == 5 and s.y >= 125 and s.hearts > 0, 10))
    S.append(("sw_shore", lambda nav: make_lareach_policy(nav, Goal(160, 173, 8)),
              lambda emu, s: s.room == 0x55 and s.mode == 5 and s.y >= 157 and s.hearts > 0, 40))
    S.append(("sw_65",) + cross("Down", 0x65, 40))
    S.append(("sw_64",) + cross("Left", 0x64, 40))
'''
assert t.count(old) == 1
t = t.replace(old, new)
ast.parse(t)
p.write_bytes((t.replace("\n", "\r\n") if crlf else t).encode("utf-8"))

from zelda.captions import CAPTIONS
import pprint
CAPTIONS.update({
    "sw_w45": ("TWO NOTES TO LEVEL 4'S ISLAND",
               "The shops are 17 screens away on foot. The wind stops at every finished dungeon, and Level 4's island is four from them."),
    "sw_sail": ("THE RAFT BACK TO THE MAINLAND", "The island's dock: the raft sails itself down to the lake shore."),
    "sw_land": ("THE RAFT BACK TO THE MAINLAND", "Wait for the raft to land."),
    "sw_shore": ("OFF THE DOCK", "An Octorok patrols under the pier: dash onto land clear of its column."),
    "sw_65": ("TO THE ARROWS SHOP", "South, west, then north twice: the shop cave is four screens from the dock."),
    "sw_64": ("TO THE ARROWS SHOP", "West one screen; the shop is two screens north of here."),
})
for n, (h, w) in CAPTIONS.items():
    assert len(h) <= 80 and len(w) <= 162, n
q = pathlib.Path("zelda/captions.py")
head = q.read_text(encoding="utf-8").split("CAPTIONS: dict[str, tuple[str, str]] = ", 1)[0]
q.write_text(head + "CAPTIONS: dict[str, tuple[str, str]] = " + pprint.pformat(CAPTIONS, width=118, sort_dicts=False) + "\n", encoding="utf-8")
import importlib, fullgame
names = [s[0] for s in fullgame.segments()]
assert len(names) == len(set(names))
i = names.index("L5_done")
print(len(names), "segments:", names[i:i + 14])
