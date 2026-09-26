"""Ride the whirlwind to Level 2's door for Level 8, starting from wherever the live run already is on the row-6
walk. usage: python patch_whirl_l8.py <last committed w8 room, hex, e.g. 66>

Restores fullgame.py / intent.py from logs/archive/*_before_whirl_l8.py first, then keeps the w8 crossings up
to and including that room (their checkpoints are the resume prefix) and replaces the rest of the walk (the
remaining w8 rooms and the whole n8 loop with cave_6b) by: wind to 0x3C, 4C, 4D, 5D, 6D east half, burn in.
probe_single_entries.py chain A: 4,525 frames from the pond into Level 8, against ~8,200 walking."""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import ast
import pathlib
import shutil
import sys

last = int(sys.argv[1], 16)
shutil.copy2("logs/archive/fullgame_before_whirl_l8.py", "fullgame.py")
shutil.copy2("logs/archive/intent_before_whirl_l8.py", "zelda/intent.py")


def load(p):
    raw = pathlib.Path(p).read_bytes()
    return raw.decode("utf-8").replace("\r\n", "\n"), b"\r\n" in raw


def save(p, t, crlf):
    ast.parse(t)
    pathlib.Path(p).write_bytes((t.replace("\n", "\r\n") if crlf else t).encode("utf-8"))


t, crlf = load("fullgame.py")
loop = '''    for room in (0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69, 0x6A, 0x6B, 0x6C):
        S.append((f"w8_{room:02x}",) + cross("Right", room, 40))
'''
assert t.count(loop) == 1
rooms = [r for r in (0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69, 0x6A, 0x6B, 0x6C) if r <= last]
keep = ("    for room in (" + ", ".join(f"0x{r:02X}" for r in rooms) + ("," if len(rooms) == 1 else "") + "):\n"
        '        S.append((f"w8_{room:02x}",) + cross("Right", room, 40))\n') if rooms else ""
a = t.index(loop)
b = t.index('    S.append(("enter_L8", lambda nav: burn_entry_policy(nav, (192, 109), "Left", 8),')
cut = t[a:b]
assert 'f"n8_{room:02x}"' in cut and '"cave_6b"' in cut
t = t[:a] + keep + f'''    # --- THE WHIRLWIND, NOT THE WALK (switched mid-run at 0x{last:02X}). Level 8's door (0x6D) is the rest of
    # row 6 plus a loop along the bottom row away on foot. The recorder's wind stops at every finished
    # dungeon, and Level 2's door (0x3C) is four screens from Level 8's: down to 4C, right to 4D, down to
    # 5D, and down into 6D's EAST half at x=192, the half with the burnable bush. probe_single_entries.py
    # chain A: 4,525 frames from the pond into Level 8, against ~8,200 walking. It also skips the
    # 100-rupee tree on 0x6B, which the purse no longer needs (only arrows are left to pay for).
    S.append(("wl8_3c", lambda nav: whirl_to_policy(nav, 0x3C),
              lambda emu, s: s.room == 0x3C and s.level == 0 and s.mode == 5 and s.hearts > 0, 30))
    for d, room in zip(["Down", "Right", "Down"], [0x4C, 0x4D, 0x5D]):
        S.append((f"wl8_{{room:02x}}",) + cross(d, room, 40))
    S.append(("wl8_6d", lambda nav: make_cross_at_policy(nav, "Down", at=192),
              lambda emu, s: s.hearts > 0 and s.mode == 5 and s.room == 0x6D and s.x >= 176, 40))
''' + t[b:]
old = '''    S.append(("hc_w37", lambda nav: whirl_to_policy(nav, 0x37),'''
assert t.count(old) == 1
# after the ride above the wind's counter sits on Level 2; Level 1's door is one note away
t = t.replace(old, '''    S.append(("hc_w37", lambda nav: whirl_to_policy(nav, 0x37, counter=0x3C),''')
save("fullgame.py", t, crlf)

t, crlf = load("zelda/intent.py")
old = '''    ("n9", "TOWARD DEATH MOUNTAIN",'''
assert t.count(old) == 1
t = t.replace(old, '''    ("wl8", "TOWARD LEVEL 8", "Four screens from Level 2's door to the lion's. Walking there along the "
                              "bottom of the map is far longer."),
    ("n9", "TOWARD DEATH MOUNTAIN",''')
old = '''    "n9_6c": ('''
assert t.count(old) == 1
t = t.replace(old, '''    "wl8_3c": ("RIDING THE WHIRLWIND TO LEVEL 2", "Level 8's door is a long walk along the bottom of the "
                                              "map, and four screens from Level 2's door. The wind is faster."),
    "n9_6c": (''')
save("zelda/intent.py", t, crlf)

import fullgame  # noqa: E402
from zelda import intent  # noqa: E402
names = [s[0] for s in fullgame.segments()]
assert len(names) == len(set(names))
i = names.index("w8_52")
print(len(names), "segments:", names[i:i + len(rooms) + 8])
for n in names[i:i + len(rooms) + 8]:
    print(f"   {n:9s} {intent.for_segment(n)[0]}")
