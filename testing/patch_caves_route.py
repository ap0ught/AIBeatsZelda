"""Re-route the money: caves instead of farms, one shopping trip instead of two.

The owner, after watching the bot farm again: "i dont understand why you are farming again. this is not
needed. you ignore rupees on the ground all the time, and then waste time farming." Both halves were
true. The bot was blind to monster drops until 2026-09-16, and 550 rupees sit in 14 secret caves.

What this does (all measured on the route before being written):
  * 0x3D - touch the Armos (push from (144,109) facing Down): +30, on the route already.
  * 0x2D - bomb the top rocks (from (112,77) facing Left): +30, on the route already.
  * delete farm68/farm80, the top-ups that paid for the arrows.
  * buy the monster bait on the SAME trip as the arrows - the grave shop on 0x34 is one screen north
    of the arrows shop on 0x44 - instead of a second expedition from Level 7's door.
  * delete the Level 6 farm leg (w7_52, whirl_l6, l6_farm_in, l6_farm20..61, l6_farm_out) and the
    second expedition (m7_* walk, fairy heal, second buy_food, b7_* walk, l7_drain2), and enter Level 7
    once, straight after the first pond drain.

Money check: Link reaches 0x3D with ~51 rupees; +30 +30 = 111, and a whole dungeon (Level 5) of drops
he can now see comes before the shop. Arrows (80) + bait (60) = 140.

usage: python patch_caves_route.py            (writes fullgame.py, re-stamps checkpoints, rolls back)
"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import ast
import hashlib
import json
import pathlib
import shutil
import time

PATH = pathlib.Path("fullgame.py")
raw = PATH.read_bytes()
CRLF = b"\r\n" in raw
t = raw.decode("utf-8").replace("\r\n", "\n")


def sub(old, new, what):
    global t
    n = t.count(old)
    assert n == 1, f"{what}: {n} matches"
    t = t.replace(old, new)
    print(f"  applied: {what}")


# ---- 1. caves on the Level 2 -> Level 5 walk
sub('''    for i, (d, room) in enumerate(zip(L2_TO_HILLS_DIRS, L2_TO_HILLS_ROOMS)):
        S.append((f"l5w{i:02d}_{room:02x}",) + cross(d, room, 40))''',
    '''    for i, (d, room) in enumerate(zip(L2_TO_HILLS_DIRS, L2_TO_HILLS_ROOMS)):
        S.append((f"l5w{i:02d}_{room:02x}",) + cross(d, room, 40))
        # Secret rupee caves the route walks straight through (Zelda Dungeon wiki list, each one
        # probed before it went in). The owner's rule: never farm - the caves hold 550 rupees.
        if room == 0x3D:
            S.append(("cave_3d", lambda nav: secret_cave_policy(nav, (144, 109), "Down", "push", want=30),
                      lambda emu, s: (s.hearts > 0 and s.room == 0x3D and s.level == 0 and s.mode == 5
                                      and emu.byte(0x66D) >= 75), 30))
        if room == 0x2D:
            # THE 100-RUPEE CAVE on 0x0F - no item needed, and none of the way there is visible to
            # the navigator (six probes to find it):
            #   leave 0x2D upward at column 120 (the default column lands in a dead-end pocket on
            #   0x1D), go right twice to 0x1F, then HOLD UP at x=128 through rock the tile map calls
            #   solid; the staircase is already drawn at (128,125). Then all the way back to 0x2D,
            #   where the route carries on west. The gift counts up one rupee at a time.
            S.append(("c0f_1d", lambda nav: make_cross_at_policy(nav, "Up", at=120), ok(0x1D), 30))
            S.append(("c0f_1e",) + cross("Right", 0x1E, 30))
            S.append(("c0f_1f",) + cross("Right", 0x1F, 30))
            S.append(("c0f_0f", lambda nav: hold_through_policy(nav, 128, "Up", 0x0F), ok(0x0F), 30))
            S.append(("cave_0f", lambda nav: secret_cave_policy(nav, None, "Up", "walk", want=100),
                      lambda emu, s: (s.hearts > 0 and s.room == 0x0F and s.level == 0 and s.mode == 5
                                      and emu.byte(0x66D) >= 150), 30))
            S.append(("c0f_b1f", lambda nav: hold_through_policy(nav, 128, "Down", 0x1F), ok(0x1F), 30))
            S.append(("c0f_b1e",) + cross("Left", 0x1E, 30))
            S.append(("c0f_b1d",) + cross("Left", 0x1D, 30))
            S.append(("c0f_b2d", lambda nav: make_cross_at_policy(nav, "Down", at=120), ok(0x2D), 30))''',
    "insert the 0x3D cave and the 0x0F hundred-rupee detour")

# ---- 2. no top-up farm before the arrows
sub('''    for target in (68, 80):
        S.append((f"farm{target}", lambda nav, tg=target: farm_dungeon_policy(nav, tg),
                  (lambda tg: lambda emu, s: s.hearts > 0 and emu.byte(0x66D) >= tg)(target), 40))''',
    '''    # (The farm68/farm80 top-ups that used to sit here are gone: the caves on 0x3D and 0x2D pay for
    # the arrows, and Link now picks up the rupees his fights drop.)''',
    "delete the arrow-money farm")

# ---- 3. buy the bait on the arrows trip
sub('''    S.append(("shop_leave", lambda nav: cave_exit_policy(nav),
              lambda emu, s: s.mode == 5 and s.level == 0 and s.hearts > 0, 20))''',
    '''    S.append(("shop_leave", lambda nav: cave_exit_policy(nav),
              lambda emu, s: s.mode == 5 and s.level == 0 and s.hearts > 0, 20))
    # Buy the MONSTER BAIT now, one screen north, instead of walking back from Level 7's door later.
    # Level 7's hungry Goriya only moves for it, and the candle that opens the rich caves is behind
    # him - the old route paid for that circle with a whirlwind back to Level 6, a farm, a walk across
    # the map and a second pond drain. E-4 (0x34) is a graveyard; the shop is under a gravestone.
    S.append(("bait_34",) + cross("Up", 0x34, 40))
    S.append(("buy_food", lambda nav: grave_shop_policy(nav, ram.BAIT),
              lambda emu, s: s.hearts > 0 and emu.byte(ram.BAIT) > 0, 25))
    S.append(("food_leave", lambda nav: cave_exit_policy(nav),
              lambda emu, s: s.mode == 5 and s.level == 0 and s.hearts > 0, 20))
    S.append(("bait_44",) + cross("Down", 0x44, 40))''',
    "buy the bait on the arrows trip")

# ---- 4. the Level 7 approach: enter once, no farm leg, no second expedition
a = t.index('    S.append(("w7_52",) + cross("Down", 0x52, 40))')
b = t.index('    S.append(("enter_L7b", lambda nav: stairs_entry_policy(nav, 7),')
c = t.index("\n", t.index("25))", b)) + 1
# also drop the long MONEY comment block that explained the farm leg
m = t.rfind("    # MONEY, and why it cannot be skipped.", 0, a)
start = m if m != -1 else a
t = t[:start] + '''    # Level 7 is entered ONCE. The bait was bought on the arrows trip, so there is no whirlwind back
    # to Level 6, no farm, no walk across the map for food and no second pond drain.
    S.append(("enter_L7", lambda nav: stairs_entry_policy(nav, 7),
              lambda emu, s: s.level == 7 and s.mode == 5 and s.hearts > 0, 25))
''' + t[c:]
print("  applied: single Level 7 entry; farm leg and second expedition removed")

ast.parse(t)
PATH.write_bytes((t.replace("\n", "\r\n") if CRLF else t).encode("utf-8"))

import fullgame  # noqa: E402
names = [s[0] for s in fullgame.segments()]
assert len(names) == len(set(names)), "duplicate names"
gone = [n for n in names if n.startswith(("l6_farm", "m7_", "b7_", "heal")) or n in
        ("farm68", "farm80", "w7_52", "whirl_l6", "l7_drain2", "enter_L7b")]
assert not gone, f"leftovers: {gone}"
for key in ("cave_3d", "cave_2d", "bait_34", "buy_food", "enter_L7"):
    assert key in names, key
print(f"\n{len(names)} segments")
i = names.index("l7_drain")
print("  after the pond:", names[i:i + 4])
j = names.index("buy_arrows")
print("  the shop trip:", names[j:j + 7])

h = hashlib.sha1("|".join(names).encode()).hexdigest()[:12]
ck = pathlib.Path("logs/checkpoints")
resume_at = "l5w02_3d"
doomed = [ck / f"fullgame_{n}.json" for n in names[names.index(resume_at) + 1:] if (ck / f"fullgame_{n}.json").exists()]
old_names = [p.stem.replace("fullgame_", "") for p in ck.glob("fullgame_*.json")]
stale = [ck / f"fullgame_{n}.json" for n in old_names if n not in names]
bak = pathlib.Path("logs/archive/partial_" + time.strftime("%Y%m%d_%H%M%S"))
bak.mkdir(parents=True, exist_ok=True)
for p in set(doomed + stale):
    if p.exists():
        shutil.copy2(p, bak / p.name)
        p.unlink()
for p in ck.glob("fullgame_*.json"):
    d = json.loads(p.read_text())
    if d.get("list_hash") != h:
        d["list_hash"] = h
        p.write_text(json.dumps(d))
have = [n for n in names if (ck / f"fullgame_{n}.json").exists()]
d = json.loads((ck / f"fullgame_{have[-1]}.json").read_text())
print(f"\nrolled back to '{have[-1]}': {d['frames']} frames | {d['summary'][40:95]}")
assert have[-1] == resume_at, have[-1]
