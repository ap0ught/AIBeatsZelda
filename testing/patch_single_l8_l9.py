"""Level 8 climbed once, Level 9 entered once, and success tests that count from the segment's own start.

LEVEL 8. The first run climbed to 0x3E, bombed on up to 0x2E and 0x1E for nothing (a Gohma room it then
walked back out of), came all the way out of the dungeon, walked a loop to the 100-rupee tree on 0x6B,
walked back, and climbed the same rooms again: ~13,000 frames. The tree is on the walk IN (segment n8_6b),
and probe_single_entries.py chain B took its hundred from that side first time (1,019 frames, then down
to 0x7B in 260). So: take the money on the way in, and from 0x3E go straight on east to 0x3F.

LEVEL 9. The first run went in, came out for heart container #12 and the Magical Sword, went back in,
came out AGAIN to sail across the lake and buy bombs, and went back in a third time: ~38,000 frames of
the video. Everything Level 9 needs is fetched first now - heart #12 (0x47, burn), the Magical Sword
(0x21), then Death Mountain by the road the second entry used (no fairy detour, no 16/15 dead end) -
and the dungeon is played once. No bombs are bought anywhere: Link picks up drops now, and 0x16's pile
tops him up inside. Chain C (whirlwind 6C -> Level 1's door -> 38 -> 48) and chain D (0x16 north to
0x06, the join between the first entry's rooms and the Silver Arrow route) were probed.

RELATIVE TESTS. Every "keys >= N" was a count copied from the first run. The single Level 6 climb already
leaves Link one key richer than that run, which turns "keys >= 4" at 0x2D true BEFORE the key is taken.
Each of those segments gained exactly one key in the first run, so the test is now "one more key than
the segment started with" (zelda.runner.SEG_START). Same for the 100-rupee cave and the bomb piles.

usage: python patch_single_l8_l9.py      (edits fullgame.py, zelda/runner.py, zelda/intent.py)
"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import ast
import pathlib


def load(path):
    raw = pathlib.Path(path).read_bytes()
    return raw.decode("utf-8").replace("\r\n", "\n"), b"\r\n" in raw


def save(path, text, crlf):
    ast.parse(text)
    pathlib.Path(path).write_bytes((text.replace("\n", "\r\n") if crlf else text).encode("utf-8"))


def sub(text, old, new, what, count=1):
    n = text.count(old)
    assert n == count, f"{what}: {n} matches"
    print(f"  applied: {what}")
    return text.replace(old, new)


# ------------------------------------------------------------------ runner: remember the segment start
t, crlf = load("zelda/runner.py")
t = sub(t, "\nclass Run", '''
# The state MAIN was in when the current segment began. Success tests that must count from the start of
# their own segment ("one more key than Link came in with") read it; runner.segment sets it before the
# search and it stays put while the winner is played into MAIN and trimmed.
SEG_START: State | None = None


class Run''', "SEG_START module global")
t = sub(t, '''        s0 = main.state()
        main.note(f"SEGMENT {name}: room''', '''        s0 = main.state()
        global SEG_START
        SEG_START = s0
        main.note(f"SEGMENT {name}: room''', "set SEG_START in segment()")
save("zelda/runner.py", t, crlf)

# ------------------------------------------------------------------ fullgame
t, crlf = load("fullgame.py")
t = sub(t, '''    def ok(room, **need):
        return lambda emu, s: (s.room == room and s.mode == 5 and s.hearts > 0
                               and all(getattr(s, k) >= v for k, v in need.items()))
''', '''    def ok(room, **need):
        return lambda emu, s: (s.room == room and s.mode == 5 and s.hearts > 0
                               and all(getattr(s, k) >= v for k, v in need.items()))

    def started():
        from zelda import runner as zrunner
        return zrunner.SEG_START

    def ok_gain(room, **gain):
        """ok(), counted from the state the segment STARTED in - "one more key than Link walked in with".
        The absolute counts copied from the first run go true too early (or never) as soon as the route
        before them changes what Link carries, and the single Level 6 climb already does."""
        return lambda emu, s: (s.room == room and s.mode == 5 and s.hearts > 0
                               and all(getattr(s, k) >= getattr(started(), k) + v for k, v in gain.items()))
''', "ok_gain helper")

for old, new, what in [
    ('ok(0x2C, keys=4), 60))', 'ok_gain(0x2C, keys=1), 60))', "l6_2d key test relative"),
    ('ok(0x39, keys=4), 60))', 'ok_gain(0x39, keys=1), 60))', "l7_3a_key key test relative"),
    ('ok(0x7E, keys=2), 50))', 'ok_gain(0x7E, keys=1), 50))', "l8_7f_key key test relative"),
    ('ok(0x5D, keys=3), 50))', 'ok_gain(0x5D, keys=1), 50))', "l8_5e_key key test relative"),
    ('ok(0x5C, keys=4), 50))', 'ok_gain(0x5C, keys=1), 50))', "l8_5d_key key test relative"),
    ('ok(0x5D, keys=5), 50))', 'ok_gain(0x5D, keys=1), 50))', "l8_5c_key key test relative"),
    ('lambda emu, s: s.hearts > 0 and s.room == 0x3F and s.bombs >= 4, 50))',
     'lambda emu, s: (s.hearts > 0 and s.room == 0x3F\n'
     '                             and s.bombs >= min(emu.byte(0x67C), started().bombs + 4)), 50))',
     "r8_3f_bombs test relative"),
]:
    t = sub(t, old, new, what)

# ---- Level 8: the 100-rupee tree on the walk in
t = sub(t, '''    for d, room in zip(["Left", "Down", "Right", "Right", "Right", "Right", "Up", "Left", "Left"],
                       [0x6B, 0x7B, 0x7C, 0x7D, 0x7E, 0x7F, 0x6F, 0x6E, 0x6D]):
        S.append((f"n8_{room:02x}",) + cross(d, room, 40))
''', '''    for d, room in zip(["Left", "Down", "Right", "Right", "Right", "Right", "Up", "Left", "Left"],
                       [0x6B, 0x7B, 0x7C, 0x7D, 0x7E, 0x7F, 0x6F, 0x6E, 0x6D]):
        S.append((f"n8_{room:02x}",) + cross(d, room, 40))
        if room == 0x6B:
            # The 100-rupee tree ("third from the left, bottom row of the central trees") is on this
            # screen - the first run walked straight past it, then came back out of Level 8 for it.
            # Level 8's Pols Voices and Level 9's Like Likes are arrow fights, a rupee a shot.
            S.append(("cave_6b", lambda nav: burn_cave_policy(nav, (128, 141), "Down"),
                      lambda emu, s: (s.hearts > 0 and s.level == 0 and s.mode == 5 and s.room == 0x6B
                                      and emu.byte(0x66D) >= min(255, started().rupees + 90)), 25))
''', "cave_6b on the walk in")

a = t.index('    S.append(("l8_2e",  lambda nav: bomb_policy(nav, "Up", 0x2E),')
b = t.index('    S.append(("r8_3f",  lambda nav: make_lafight_policy(nav, "Right"), ok(0x3F), 50))')
cut = t[a:b]
for must in ('"l8_1e"', '"o8_out"', '"m8_6c"', '"cave_6b"', '"s8_', '"r8_in"', '"r8_3e"'):
    assert must in cut, must
t = t[:a] + '''    # Straight on east into 3F. 3F has a staircase standing in the open - the join to the wing with the
    # Gleeok and the eighth Triforce - so the rooms above 3E (a bombed wall and a Gohma room with
    # shutters) are never needed. The first run went up there, came back down, walked out of the
    # dungeon for money and climbed all of this again; the money is taken on the walk in now.
''' + t[b:]
print("  applied: Level 8 climbed once (l8_2e ... r8_3e removed)")

# ---- Level 9: fetch everything first, enter once
a = t.index('    S.append(("n9_6c",) + cross("Left", 0x6C, 40))')
b = t.index('    S.append(("s9_06",) + cross("Up", 0x06, 40))')
cut = t[a:b]
for must in ('"whirl_l5"', '"h9_heal"', '"x9_out"', '"hc_47_heart"', '"ms_sword"', '"r9_enter"', '"rb_buy1"',
             '"rb_16b"', '"m9_16_bombs"', '"l9_56_key"'):
    assert must in cut, must
t = t[:a] + '''    S.append(("n9_6c",) + cross("Left", 0x6C, 40))
    # --- EVERYTHING LEVEL 9 NEEDS, FETCHED BEFORE GOING IN. The first run entered Level 9 three times:
    # out again for a heart container and the Magical Sword, back in, out AGAIN to sail across the lake
    # and buy bombs, back in - about 38,000 frames. Now: heart container #12, the Magical Sword (its old
    # man wants twelve), then up Death Mountain once, and the dungeon is played straight through. Bombs
    # are never bought - drops are picked up now, and room 0x16's pile tops Link up inside.
    # Heart container #12: the whirlwind to Level 1's door, three screens to 0x47, burn the tree.
    # (The wind's counter is not known after Level 8, so the first ride learns it; the old man in the
    # cave offers a potion on the left and the container on the right.)
    S.append(("hc_w37", lambda nav: whirl_to_policy(nav, 0x37),
              lambda emu, s: s.room == 0x37 and s.level == 0 and s.mode == 5 and s.hearts > 0, 30))
    for d, room in zip(["Right", "Down", "Left"], [0x38, 0x48, 0x47]):
        S.append((f"hc_{room:02x}",) + cross(d, room, 40))
    S.append(("hc_47_heart", lambda nav: hc_cave_policy(nav, (176, 157), "Down", "burn"),
              lambda emu, s: s.containers >= 12 and s.level == 0 and s.mode == 5 and s.hearts > 0, 40))
    # The Magical Sword: the whirlwind to Level 6's door, three screens to the graveyard's corner.
    S.append(("ms_w22", lambda nav: whirl_to_policy(nav, 0x22, counter=0x37),
              lambda emu, s: s.room == 0x22 and s.level == 0 and s.mode == 5 and s.hearts > 0, 30))
    for d, room in zip(["Down", "Left", "Up"], [0x32, 0x31, 0x21]):
        S.append((f"ms_{room:02x}",) + cross(d, room, 40))
    S.append(("ms_sword", grave_sword_policy,
              lambda emu, s: s.sword >= 3 and s.level == 0 and s.mode == 5 and s.hearts > 0, 40))
    # Death Mountain from Level 5's door: west along row 1 to 0x17, up, and west twice to Spectacle
    # Rock - the road the first run's second entry walked (no fairy-pond detour, no 16/15 dead end).
    S.append(("d9_w0b", lambda nav: whirl_to_policy(nav, 0x0B, counter=0x22),
              lambda emu, s: s.room == 0x0B and s.level == 0 and s.mode == 5 and s.hearts > 0, 30))
    for d, room in zip(["Down", "Left", "Left", "Left", "Left", "Up", "Left", "Left"],
                       [0x1B, 0x1A, 0x19, 0x18, 0x17, 0x07, 0x06, 0x05]):
        S.append((f"d9_{room:02x}",) + cross(d, room, 40))
    S.append(("enter_L9", lambda nav: bomb_entry_policy(nav, (80, 173), "Up", (80, 157), 9),
              lambda emu, s: s.level == 9 and s.mode == 5 and s.hearts > 0, 40))
    # --- Level 9, once. Room 66 is the old man who lets all-eight-Triforce holders pass - his two flames
    # sit in the object table looking exactly like enemies. North to 56 (a key on the floor), bomb its
    # west wall into 55, the four-bombable-wall hub; the staircase under one of its blocks is the only
    # way into the body of the dungeon.
    S.append(("l9_66",) + cross("Up", 0x66, 40))
    S.append(("l9_56",  lambda nav: make_lafight_policy(nav, "Up"),  ok(0x56), 50))
    S.append(("l9_56_key", lambda nav: make_clear_grab_policy(nav, None),
              lambda emu, s: s.hearts > 0 and s.room == 0x56 and s.keys >= started().keys + 1, 50))
    S.append(("l9_55",  lambda nav: bomb_policy(nav, "Left", 0x55),
              lambda emu, s: s.hearts > 0 and s.room == 0x55 and s.level == 9, 40))
    S.append(("l9_55_st", clear_push_stairs_policy,
              lambda emu, s: s.hearts > 0 and s.mode == 9, 40))
    S.append(("l9_pass", passage_policy,
              lambda emu, s: s.hearts > 0 and s.level == 9 and s.mode == 5 and s.room != 0x55, 30))
    # Surfaced in 14: five LIKE LIKES, nine hit points each - forty-two seconds of sword per attempt and
    # it never finishes. An arrow does ten.
    S.append(("m9_15",  lambda nav: bow_fight_policy(nav, "Right"), ok(0x15), 50))
    S.append(("m9_16",  lambda nav: make_lafight_policy(nav, "Right"), ok(0x16), 50))
    # 0x16's floor item is a pile of four bombs - the only reachable pile before the Silver Arrow walls.
    S.append(("m9_16_bombs", lambda nav: make_clear_grab_policy(nav, None),
              lambda emu, s: (s.hearts > 0 and s.room == 0x16
                              and s.bombs >= min(emu.byte(0x67C), started().bombs + 4)), 50))
    # North through the locked door to the old man ("go to the next room"), bomb his west wall.
''' + t[b:]
print("  applied: Level 9 entered once (x9_*, r9_*, rb_*, h9_*, n9 road removed; d9 road added)")
save("fullgame.py", t, crlf)

# ------------------------------------------------------------------ captions
t, crlf = load("zelda/intent.py")
t = sub(t, '''    ("n9", "TOWARD DEATH MOUNTAIN",''', '''    ("d9", "UP DEATH MOUNTAIN", "Magical Sword, twelve hearts, arrows and bombs: Level 9 gets entered "
                                "once, with everything it needs."),
    ("n9", "TOWARD DEATH MOUNTAIN",''', "caption family d9")
t = sub(t, '''    "r6_18": (''', '''    "n9_6c": ("OFF THE STAIRCASE", "The whirlwind will not pick Link up while he stands on a dungeon's "
                                   "stairs."),
    "hc_w37": ("RIDING THE WHIRLWIND TO LEVEL 1", "Three screens from a tree that hides a heart "
                                                  "container. The Magical Sword's old man wants twelve; "
                                                  "Link has eleven."),
    "hc_47_heart": ("HEART CONTAINER NUMBER TWELVE", "Burn the tree. Inside: a potion on the left, a "
                                                     "container on the right. Take the container."),
    "ms_w22": ("RIDING TO LEVEL 6'S DOOR", "The Magical Sword is under a gravestone three screens away."),
    "d9_w0b": ("RIDING TO THE FOOT OF DEATH MOUNTAIN", "Level 5's door. Level 9 is a bombable rock at the "
                                                       "top of the mountain."),
    "enter_L9": ("LEVEL 9 - DEATH MOUNTAIN", "Entered once. The first run went in three times: for a "
                                             "sword, for bombs, and for real."),
    "m9_16_bombs": ("A PILE OF BOMBS", "Level 9 is bombable walls from here to Ganon. Take the pile "
                                       "instead of buying them."),
    "r6_18": (''', "captions for the new Level 9 errand")
save("zelda/intent.py", t, crlf)

import fullgame  # noqa: E402
from zelda import intent  # noqa: E402
names = [s[0] for s in fullgame.segments()]
assert len(names) == len(set(names)), "duplicate names"
for gone in ("l8_2e", "l8_1e", "o8_out", "m8_6c", "s8_7b", "r8_in", "r8_3e", "whirl_l5", "h9_heal", "x9_out",
             "r9_enter", "rb_buy1", "rb_16b", "n9_b05", "n9_1b"):
    assert gone not in names, gone
print(f"\n{len(names)} segments")
i = names.index("n8_6b")
print("  L8 walk in:", names[i:i + 4])
j = names.index("l8_3e")
print("  L8 climb:  ", names[j - 1:j + 4])
k = names.index("warp_L8")
print("  L9 errand: ", names[k:k + 36])
for n in names[k:k + 36]:
    print(f"     {n:12s} {intent.for_segment(n)[0]}")
