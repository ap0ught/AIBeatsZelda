"""Route 3: cut what the door tables and the probes say the run never needed (2026-09-18).

Found by reading the cartridge's door tables against the finished run and probing each change from that run's
own states (probe_chain.py, probe_cross_audit.py):
  L1  bomb 53's north wall (280 frames, 3/3) instead of the three-room keys-only loop; that frees a key, so the
      74 detour goes; the boomerang (never used) is no longer fought for.
  L4  the dark room's key is a FLOOR key: grab it (606) instead of clearing five Zols in the dark (1,579).
  L5  the 77 key detour, the 56/57 excursion (exploration residue) and clearing 65 all go; 66's floor key is
      grabbed; both bombed walls are dashed (damage-aware) rather than walked.
  L6  the 7A key detour goes; 28's east wall is bombed straight into 29 (whose key is on the floor), which skips
      the Gleeok mini-boss, a locked door, and the whole 1A/1B/0B excursion to an old man's dead end (~7,000).
  L7  the 3A key detour goes (and with it the Digdogger that re-entering 39 used to spawn); rooms whose exit is
      open or locked are crossed, not cleared (l7_19: 2,653 -> ~450).
  L8  5E's north shutter leads straight to 4E: the 5D/5C/4D loop goes except for 5D's floor key; from the
      passage, 4C's north wall is dash-bombed straight into the Gleeok's room - the eight Pols Voices, 4B and 3B
      never happen (4,121 -> ~810, no damage in 4/4 probes).
  L9  15 -> 16 is an open door: crossed, not cleared.
Keys (needs 3+2+3+1+3 from Level 5 on) are covered by: L4's 02 floor key, L5 66/47/27/26, L6 58/29/2D,
L8 7F/5E/5D, L9 56 - every pickup has a success test that insists on the key.
"""
import ast
import pathlib

PATH = pathlib.Path("fullgame.py")
raw = PATH.read_bytes()
CRLF = b"\r\n" in raw
t = raw.decode("utf-8").replace("\r\n", "\n")


def sub(old, new, what):
    global t
    n = t.count(old)
    assert n == 1, f"{what}: {n} matches"
    t = t.replace(old, new)
    print("  applied:", what)


def cut(start, end, new, what):
    """Replace from the line starting with `start` up to (not including) the line starting with `end`."""
    global t
    a = t.index(start)
    b = t.index(end, a)
    t = t[:a] + new + t[b:]
    print("  applied:", what)


# ---------------------------------------------------------------- Level 1
sub('''    S.append(("l1_74",      lambda nav: make_cross_policy(nav, "Right"),  ok(0x74), 30))
    S.append(("l1_74_key",  lambda nav: make_clear_grab_policy(nav, "Left"),  ok(0x73, keys=2), 60))
''', '''    # (The detour east for 74's key is gone: bombing 53's north wall below saves the locked door that key
    # was for. Keys: 72, 53, 33, 23, 45 for the five locks 63, 23, 22, 44, 35.)
''', "L1: drop the 74 key detour")
sub('''    S.append(("l1_52",      lambda nav: make_cross_policy(nav, "Left"),   ok(0x52), 40))
    S.append(("l1_42",      lambda nav: make_cross_policy(nav, "Up"),     ok(0x42), 40))
    S.append(("l1_43",      lambda nav: make_cross_policy(nav, "Right"),  ok(0x43), 40))
''', '''    # Link HAS bombs now (Level 3 came first), so blast 53's north wall - 280 frames in the probe, 3 of 3 -
    # instead of the three-room loop through a locked door that the bombless route needed.
    S.append(("l1_43",      lambda nav: bomb_policy(nav, "Up", 0x43),     ok(0x43), 40))
''', "L1: bomb 53 -> 43")
sub('''    S.append(("l1_44_boom", lambda nav: make_clear_grab_policy(nav, "Right"), ok(0x45), 60))
''', '''    # The boomerang in here was fought for and never thrown once in the whole run. Walk on through.
    S.append(("l1_45",      lambda nav: make_cross_policy(nav, "Right"),  ok(0x45), 40))
''', "L1: skip the boomerang")

# ---------------------------------------------------------------- Level 4
sub('''    S.append(("l4_40_key",  lambda nav: make_clear_grab_policy(nav, "Up"),     ok(0x30, keys=3), 60))''',
    '''    # 40's key lies on the floor (ROM: not an after-clear item). Grab it and go - clearing five Zols in the
    # dark first cost 1,579 frames and was the owner's "stuck in the dark room for nearly 30 seconds".
    S.append(("l4_40_key",  lambda nav: make_grab_policy(nav, "Up"),           ok_gain(0x30, keys=1), 60))''',
    "L4: grab 40's floor key")
sub('''    S.append(("l4_02",      lambda nav: make_cross_policy(nav, "Right"),       ok(0x02), 50))''',
    '''    # 01's floor key is the one Level 5 starts on, so take it on purpose rather than by luck.
    S.append(("l4_02",      lambda nav: make_grab_policy(nav, "Right"),        ok_gain(0x02, keys=1), 50))''',
    "L4: take 01's floor key deliberately")

# ---------------------------------------------------------------- Level 5
cut('    S.append(("l5_77",      lambda nav: make_cross_policy(nav, "Right"),   ok(0x77), 40))',
    '    # That staircase is a PASSAGE, not an item room',
    '''    S.append(("l5_66",      lambda nav: make_cross_policy(nav, "Up"),      ok(0x66), 50))
    # 66's key is a FLOOR key: take it (the first locked door is on the far side of the passage). The old
    # route also went east for 77's key (1,720 frames), up to 56 and 57 and back (exploration residue) and
    # cleared 65 on principle - none of it needed. Both walls are dashed with the damage-aware planner:
    # Gibdos and Blue Darknuts hit for two hearts and bomb_policy stands still for the fuse.
    S.append(("l5_66_key",  lambda nav: make_grab_policy(nav, None),
              lambda emu, s: s.hearts > 0 and s.room == 0x66 and s.mode == 5 and s.keys >= started().keys + 1, 60))
    S.append(("l5_65",      lambda nav: dash_bomb_policy(nav, "Left", 0x65),   ok(0x65), 50))
    S.append(("l5_64",      lambda nav: dash_bomb_policy(nav, "Left", 0x64),   ok(0x64), 50))
    S.append(("l5_rec_st",  clear_push_stairs_policy,
              lambda emu, s: s.hearts > 0 and s.mode == 9, 40))
''', "L5: no 77 detour, no 56/57 excursion, no 65 clear")

# ---------------------------------------------------------------- Level 6
cut('    S.append(("l6_7a",      lambda nav: make_cross_policy(nav, "Right"),   ok(0x7A), 40))',
    '    S.append(("l6_78",      lambda nav: make_cross_policy(nav, "Left"),    ok(0x78), 50))',
    '''    # (No detour east for 7A's key: Link arrives with two from Level 5.)
''', "L6: drop the 7A key detour")
sub('''    S.append(("l6_48",      lambda nav: make_lafight_policy(nav, "Up"),    ok(0x48), 60))''',
    '''    S.append(("l6_48",      lambda nav: make_clear_grab_policy(nav, "Up"), ok_gain(0x48, keys=1), 60))''',
    "L6: 58's key is required now")
cut('    # Straight on into 18.',
    '    # 3A is the end of the line on this side of the map',
    '''    # FROM 28, BOMB EAST INTO 29. The door table shows 28's east wall and 29's west wall are one bombable
    # wall. The old route went north into a Gleeok mini-boss instead, east through 19, 1A and 1B to an old
    # man's dead end at 0B, all the way back, and south through a locked door - about 7,000 frames - to
    # reach this same room. 28 is a chequerboard of blocks (the standard bombing spot is a block) full of
    # Wizzrobes, so the wall is dashed: probe 3/3 at ~750 frames. 29's key is on the floor.
    S.append(("l6_29",      lambda nav: dash_bomb_policy(nav, "Right", 0x29), ok(0x29), 60))
    S.append(("l6_39",      lambda nav: make_grab_policy(nav, "Down"),     ok_gain(0x39, keys=1), 60))
''', "L6: bomb 28 -> 29, skip the mini-boss and the 1A/1B/0B excursion")
sub('''    S.append(("l6_1d",      lambda nav: make_lafight_policy(nav, "Down"),  ok(0x2D), 60))''',
    '''    # 1D's south door is open: cross it (265 frames against 1,166 clearing it first).
    S.append(("l6_1d",      lambda nav: make_cross_policy(nav, "Down"),    ok(0x2D), 60))''', "L6: cross 1D")
sub('''    S.append(("l6_2d",      lambda nav: make_clear_grab_policy(nav, "Left"), ok(0x2C, keys=4), 60))''',
    '''    S.append(("l6_2d",      lambda nav: make_clear_grab_policy(nav, "Left"), ok_gain(0x2C, keys=1), 60))''',
    "L6: 2D key relative") if 'ok(0x2C, keys=4)' in t else print("  (l6_2d already relative)")
sub('''    S.append(("l6_2c",      lambda nav: make_lafight_policy(nav, "Up"),    ok(0x1C), 60))''',
    '''    # 2C's north door is LOCKED, not a shutter: nothing in here has to die. Dash to it (damage-aware -
    # the plain crossing took five hearts from the blade traps and Wizzrobes; Gohma is next door).
    S.append(("l6_2c",      lambda nav: make_lareach_policy(nav, Goal(120, 93, 10), then_exit="Up"), ok(0x1C), 60))''',
    "L6: dash 2C")

# ---------------------------------------------------------------- Level 7
sub('''    S.append(("l7_49",  lambda nav: make_lafight_policy(nav, "Up"),   ok(0x49), 60))''',
    '''    S.append(("l7_49",  lambda nav: make_cross_policy(nav, "Up"),     ok(0x49), 60))''', "L7: cross 59")
cut('    S.append(("l7_3a",  lambda nav: bomb_policy(nav, "Right", 0x3A),',
    '    S.append(("l7_28",  lambda nav: make_lafight_policy(nav, "Up"),   ok(0x28), 60))',
    '''    # (No bombing east into 3A for its key: Link arrives with the three keys Level 7 needs, and coming back
    # from 3A is what made 39 repopulate with a Digdogger. West, straight on.)
    S.append(("l7_38",  lambda nav: make_cross_policy(nav, "Left"),   ok(0x38), 60))
''', "L7: drop the 3A key detour and its Digdogger")
sub('''    S.append(("l7_28",  lambda nav: make_lafight_policy(nav, "Up"),   ok(0x28), 60))''',
    '''    S.append(("l7_28",  lambda nav: make_cross_policy(nav, "Up"),     ok(0x28), 60))''', "L7: cross 38 (locked door)")
sub('''    S.append(("l7_19",  lambda nav: make_lafight_policy(nav, "Right"), ok(0x19), 60))''',
    '''    # 18's east door is LOCKED: it never needed the room cleared (2,653 frames; crossing it, ~450).
    S.append(("l7_19",  lambda nav: make_cross_policy(nav, "Right"),  ok(0x19), 60))''', "L7: cross 18 (locked door)")

# ---------------------------------------------------------------- Level 8
sub('''    S.append(("l8_7f_key", lambda nav: make_clear_grab_policy(nav, "Left"), ok_gain(0x7E, keys=1), 50))''',
    '''    # 7F's key lies on the floor: grab it (475 frames against 1,383 clearing the room first).
    S.append(("l8_7f_key", lambda nav: make_grab_policy(nav, "Left"), ok_gain(0x7E, keys=1), 50))''', "L8: grab 7F's floor key")
sub('''    S.append(("l8_6e",  lambda nav: make_lafight_policy(nav, "Up"),   ok(0x6E), 50))''',
    '''    S.append(("l8_6e",  lambda nav: make_cross_policy(nav, "Up"),     ok(0x6E), 50))''', "L8: cross the entrance")
cut('    S.append(("l8_5d_key", lambda nav: make_clear_grab_policy(nav, "Left"), ok_gain(0x5C, keys=1), 50))',
    '    S.append(("l8_3e",) + cross("Up", 0x3E, 50))',
    '''    # 5D's key is on the floor: step in, take it, step back (the third key Level 9 needs). Then NORTH out
    # of 5E: the door table shows 5E's north shutter opens onto 4E, so the old loop west through 5D, 5C and
    # 4D - three rooms and a locked door - was never needed.
    S.append(("l8_5d_key", lambda nav: make_grab_policy(nav, "Right"), ok_gain(0x5E, keys=1), 50))
    S.append(("l8_4e",  lambda nav: make_lafight_policy(nav, "Up"),   ok(0x4E), 50))
''', "L8: north out of 5E")
cut('    S.append(("l8_4b",  lambda nav: bow_fight_policy(nav, "Left"),  ok(0x4B), 50))',
    '    # A 40,000-frame budget means every FAILED attempt',
    '''    # The passage surfaces in 4C among eight Pols Voices - and 4C's NORTH wall is the Gleeok room's south
    # wall, bombable from either side (ROM). Dash to it with the damage-aware planner, bomb it, keep dodging
    # while the fuse burns: ~810 frames with no damage, 4 of 4 in the probe. The old route shot all eight,
    # crossed 4B and 3B and bombed in from the west: 4,121 frames.
    S.append(("l8_3c",  lambda nav: dash_bomb_policy(nav, "Up", 0x3C),
              lambda emu, s: s.hearts > 0 and s.room == 0x3C and s.level == 8, 50))
''', "L8: bomb north from 4C into the boss room")

# ---------------------------------------------------------------- Level 9
sub('''    S.append(("m9_16",  lambda nav: make_lafight_policy(nav, "Right"), ok(0x16), 50))''',
    '''    S.append(("m9_16",  lambda nav: make_cross_policy(nav, "Right"),  ok(0x16), 50))''', "L9: cross 15 (open door)")

ast.parse(t)
PATH.write_bytes((t.replace("\n", "\r\n") if CRLF else t).encode("utf-8"))

import fullgame  # noqa: E402
names = [s[0] for s in fullgame.segments()]
assert len(names) == len(set(names)), [n for n in names if names.count(n) > 1]
print(f"\n{len(names)} segments")
for lv, a, b in (("L1", "enter_L1", "L1_done"), ("L5", "enter_L5", "L5_done"), ("L6", "enter_L6", "L6_done"),
                 ("L7", "enter_L7", "L7_done"), ("L8", "enter_L8", "L8_done")):
    i, j = names.index(a), names.index(b)
    print(f"  {lv}: " + " ".join(names[i:j + 1]))
