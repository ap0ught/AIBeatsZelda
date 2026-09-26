"""Add a policy for money caves that open with a BOMB.

burn_cave_policy already handles the candle kind, and hc_cave_policy handles heart containers, but
neither fits the one cave that matters for pacing: 0x67, "IT'S A SECRET TO EVERYBODY", opened with a
bomb from (112,93) facing Up, paying 30 rupees. It sits on the Level 3 -> Level 1 walk the route
already makes, which is early enough to help pay for Gohma's arrows - the candle does not exist until
Level 7, so no burn cave can.

Measured behaviour this policy has to cope with (four probes' worth):
  * Link enters a cave at the BOTTOM of the room and the money sits in the middle;
  * `read_room_item` returns None for an old man's gift, so "is there an item?" is the wrong
    question - walk north up the middle and watch $066D instead;
  * the room takes a couple of hundred frames to finish loading before any of that is true.
"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import ast
import pathlib

PATH = "fullgame.py"
raw = pathlib.Path(PATH).read_bytes()
CRLF = b"\r\n" in raw
text = raw.decode("utf-8").replace("\r\n", "\n")

ANCHOR = "def cross(d, room, tries=30):"
assert text.count(ANCHOR) == 1, "cross() anchor"

POLICY = '''def bomb_cave_policy(nav, stand, face, want=30, budget=2500):
    """Bomb open a money cave, walk in, take what the old man leaves, and come back out.

    Written from four probes on screen 0x67. The cave pays 30 rupees; farming the same money cost
    about 620 frames per rupee, this costs about 37. Two things had to be measured rather than
    assumed: `read_room_item` is None for an old man's gift (so the money is found by walking north
    up the middle and watching the rupee counter, not by looking at the item slot), and the cave
    needs a couple of hundred frames to finish loading before any of that works."""
    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        emu.step = rec.step
        try:
            rec.step((), rng.randint(0, 8))
            before = emu.byte(0x66D)
            if emu.state().bombs < 1:
                return "no bombs to open it with"
            nav.go(lambda x, y: (x, y) == stand, "the rock", optimistic=True, max_replans=40)
            rec.step(face, 2)
            if not bot.select_b_item(emu, rec.step, bot.B_BOMBS):
                return "could not select bombs"
            rec.step("B", 2)
            for _ in range(90):
                rec.step((), 1)
            st = emu.state()
            for _ in range(240):                      # walk into the hole the bomb made
                if st.mode in (0x0B, 0x10):
                    break
                st = rec.step("Up", 1)
            if emu.state().mode not in (0x0B, 0x10):
                return "the bomb opened nothing"
            for _ in range(400):                      # let the cave load
                st = emu.state()
                if st.mode == 0x0B and st.y > 150:
                    break
                rec.step((), 2)
            for _ in range(400):                      # north up the middle, onto the money
                st = emu.state()
                if emu.byte(0x66D) >= before + want:
                    break
                if st.x < 116:
                    rec.step("Right", 1)
                elif st.x > 124:
                    rec.step("Left", 1)
                elif st.y > 140:
                    rec.step("Up", 1)
                else:
                    rec.step((), 1)
            got = emu.byte(0x66D) - before
            for _ in range(200):                      # back out the way we came in
                st = emu.state()
                if st.mode == 5:
                    break
                rec.step("Down", 1)
            return f"took {got}" if got else "the cave paid nothing"
        except (NavError, LinkDied, bot.BotError) as e:
            return "fail: " + str(e)[:40]
        finally:
            emu.step = orig
    return policy


'''

text = text.replace(ANCHOR, POLICY + ANCHOR)
ast.parse(text)
pathlib.Path(PATH).write_bytes((text.replace("\n", "\r\n") if CRLF else text).encode("utf-8"))
print("added bomb_cave_policy to fullgame.py")

import fullgame  # noqa: E402
print("segments still:", len(fullgame.segments()))
print("policy:", fullgame.bomb_cave_policy)
