"""Cut the grinding out of the route, and pay for the rest from caves.

Measured on the finished run: the two rupee farms and the trips that exist only to reach them cost
roughly 97,000 frames - 27 minutes of a 103-minute run - to earn about 140 rupees, at ~620 frames
per rupee. A secret cave pays 30 rupees in about 1,100 frames: 37 frames per rupee.

What the probes established (knowledge/rupee_caves.md), because the community map was wrong five
times over:
  * 0x0F - the audit's 100-rupee hope - CANNOT BE REACHED; the approach is walled mountain.
  * 0x62's 100 rupees DO NOT EXIST; 92 reachable spots bombed, pushed and burned, nothing.
  * 0x1A is "PAY ME AND I'LL TALK" - it TAKES 5/10/20. The route must not walk into it.
  * 0x67 is "IT'S A SECRET TO EVERYBODY": +30 rupees for one bomb, and Link has SIX bombs when the
    route already walks across that screen on the way to Level 1. This is the only money that
    arrives before Gohma's arrows must be bought - the candle, and every burn cave with it, is two
    dungeons away.
  * 0x28 (burn, +30 measured) and 0x6B (burn, +100, already in the route) arrive after Level 7 and
    pay for the monster bait and the bomb capacity upgrade.

So: the second farm goes entirely, the first shrinks from nine targets to two small top-ups, and the
cave goes in where Link already stands.
"""
import ast
import pathlib

PATH = "fullgame.py"
raw = pathlib.Path(PATH).read_bytes()
CRLF = b"\r\n" in raw
text = raw.decode("utf-8").replace("\r\n", "\n")

CUTS: list[tuple[str, str, str]] = [
    ("take the 30-rupee cave on the way to Level 1",
     """    for d, room in zip(L3_TO_L1_DIRS, L3_TO_L1_ROOMS):
        S.append((f"ow1_{room:02x}",) + cross(d, room))
""",
     """    for d, room in zip(L3_TO_L1_DIRS, L3_TO_L1_ROOMS):
        S.append((f"ow1_{room:02x}",) + cross(d, room))
        if room == 0x67:
            # "IT'S A SECRET TO EVERYBODY" - 30 rupees under a rock Link is already walking past,
            # for one of the six bombs he is carrying. Measured: +30 in about 1,100 frames, against
            # ~620 frames per rupee for farming. This is the only cave whose money arrives before
            # the arrows have to be bought; every burn cave waits on a candle from Level 7.
            S.append(("cave_67", lambda nav: bomb_cave_policy(nav, (112, 93), "Up", want=30),
                      lambda emu, s: (s.hearts > 0 and s.level == 0 and s.mode == 5
                                      and s.room == 0x67 and emu.byte(0x66D) >= 25), 30))
"""),

    ("shrink the nine-target farm to two top-ups",
     """    for target in (33, 43, 53, 63, 68, 73, 78, 83, 85):
        S.append((f"farm{target}", lambda nav, tg=target: farm_dungeon_policy(nav, tg),
                  (lambda tg: lambda emu, s: s.hearts > 0 and emu.byte(0x66D) >= tg)(target), 40))
""",
     """    # This used to be nine targets and 37,421 frames - ten minutes of the video - because Link
    # arrived with nothing and the arrows cost 80. With the cave on 0x67 taken he arrives most of
    # the way there, so ask only for the gap, and in two steps: farm_dungeon_policy earns about ten
    # rupees an attempt, and a segment that asks for much more than that fails every try.
    for target in (68, 80):
        S.append((f"farm{target}", lambda nav, tg=target: farm_dungeon_policy(nav, tg),
                  (lambda tg: lambda emu, s: s.hearts > 0 and emu.byte(0x66D) >= tg)(target), 40))
"""),

    ("the second farm's travel",
     """    S.append(("l7_out", leave_dungeon_policy,
              lambda emu, s: s.level == 0 and s.mode == 5 and s.hearts > 0, 30))
    S.append(("w7_52",) + cross("Down", 0x52, 40))
    S.append(("whirl_l6", lambda nav: whirl_to_policy(nav, 0x22),
              lambda emu, s: s.mode == 5 and s.level == 0 and s.room == 0x22 and s.hearts > 0, 20))
    S.append(("l6_farm_in", lambda nav: enter_level_policy(nav, 6),
              lambda emu, s: s.level == 6 and s.mode == 5 and s.hearts > 0, 20))
""",
     """    # (Level 7 used to be abandoned here for a second trip back to Level 6 to farm - the going in
    # and out of Level 6 that showed up so plainly in the video. The monster bait and the bomb
    # capacity upgrade are paid for by the burn caves on 0x6B and 0x28 instead, and Level 7 is now
    # played straight through.)
"""),

    ("the second farm loop",
     """    for t in (40, 47, 54, 61):
        S.append((f"fd{t}", lambda nav, tg=t: farm_dungeon_policy(nav, tg, 6),
                  (lambda tg: lambda emu, s: s.hearts > 0 and emu.byte(0x66D) >= tg)(t), 10))
""", ""),

    ("leaving Level 6 after the second farm",
     """    S.append(("l6_farm_out", leave_dungeon_policy,
              lambda emu, s: s.level == 0 and s.mode == 5 and s.hearts > 0, 30))
""", ""),

    ("the walled-off bomb pile",
     """    S.append(("s9_26",) + cross("Down", 0x26, 40))
    S.append(("s9_25",) + cross("Left", 0x25, 40))
""",
     """    # (0x25's bomb pile sits in a middle lane sealed by two full columns of blocks that do not
    # move, so the run no longer walks to it. Bombs come from drops and the capacity upgrade.)
"""),

    ("the 0x43 dead end (approach)",
     """    S.append(("s9_53",) + cross("Up", 0x53, 40))
""",
     """    # (0x53 and the room above it were a wrong deduction: 0x43 is an old man's hint room, not the
    # Silver Arrow. Forty attempts and a bomb went into it. The route now goes west from 0x63, which
    # is also what frees the key that detour used to spend.)
"""),

    ("the 0x43 dead end (the room)",
     """    S.append(("s9_43", lambda nav: open_or_bomb_policy(nav, "Up", 0x43),
              lambda emu, s: s.hearts > 0 and s.room == 0x43 and s.level == 9, 40))
""", ""),

    ("the 0x43 dead end (old man's text)",
     """    S.append(("s9_43_text", lambda nav: settle_policy(nav, lambda q: False, max_wait=600),
              lambda emu, s: s.hearts > 0 and s.room == 0x43 and s.mode == 5, 10))
""", ""),

    ("the 0x43 dead end (walking back)",
     """    S.append(("s9_b53",) + cross("Down", 0x53, 40))
""", ""),

    ("the 0x43 dead end (fighting back out)",
     """    S.append(("s9_b63", lambda nav: bow_fight_policy(nav, "Down"), ok(0x63), 50))
""", ""),
]

for what, old, new in CUTS:
    n = text.count(old)
    assert n == 1, f"{what}: found {n} matches, expected 1"
    text = text.replace(old, new)
    print(f"applied: {what}")

ast.parse(text)
pathlib.Path(PATH).write_bytes((text.replace("\n", "\r\n") if CRLF else text).encode("utf-8"))
print("\nfullgame.py rewritten")

import fullgame  # noqa: E402
names = [s[0] for s in fullgame.segments()]
assert len(names) == len(set(names)), "duplicate segment names"
should_be_gone = [n for n in names if n.startswith("fd") or n in
                  ("l7_out", "w7_52", "whirl_l6", "l6_farm_in", "l6_farm_out", "s9_53", "s9_43",
                   "s9_43_text", "s9_b53", "s9_b63", "s9_26", "s9_25",
                   "farm33", "farm43", "farm53", "farm63", "farm73", "farm78", "farm83", "farm85")]
print(f"segments: {len(names)} (was 609)")
print("cave_67 present:", "cave_67" in names, "| farms now:", [n for n in names if n.startswith("farm")])
print("leftovers that should be gone:", should_be_gone)
