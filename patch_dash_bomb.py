"""dash_bomb_policy: open a bombable wall in a room that is too dangerous to stand about in."""
import ast, pathlib
p = pathlib.Path("fullgame.py"); raw = p.read_bytes(); crlf = b"\r\n" in raw
t = raw.decode("utf-8").replace("\r\n", "\n")
anchor = "def gleeok_policy(nav, budget=6000):"
assert t.count(anchor) == 1
new = '''def dash_bomb_policy(nav, direction, then_room=None):
    """Bomb a wall in a room full of things that must not be fought: dash to the spot with the damage-aware
    planner, drop the bomb, keep dodging near it while the fuse burns, and leave through the hole.

    Level 8's Pols Voice room (4C) is the case: its north wall opens straight into the boss room, so the eight
    Pols Voices never have to die - but bomb_policy walks there with the plain navigator and then stands still
    for the fuse, and they hit for two hearts each."""
    from zelda.lookahead import plan_reach

    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        emu.step = rec.step
        try:
            rec.step((), rng.randint(0, 6))
            nudge_into_room(emu, rec.step)
            if not bot.select_b_item(emu, rec.step, bot.B_BOMBS):
                return "could not select bombs"
            tx, ty = bot.BOMB_SPOTS[direction]
            doors0 = emu.byte(0xEE)
            for _ in range(3):
                if emu.state().bombs < 1:
                    return "no bombs"
                emu.step = orig
                res = plan_reach(emu, rec, Goal(tx, ty, 3), max_frames=900, rng=rng)
                emu.step = rec.step
                if res != "arrived":
                    return res
                st = emu.state()
                for _ in range(24):
                    if (st.x, st.y) == (tx, ty):
                        break
                    st = rec.step(("Right" if st.x < tx else "Left") if st.x != tx else
                                  ("Down" if st.y < ty else "Up"), 1)
                rec.step(direction, 1)
                rec.step("B", 2)
                emu.step = orig
                plan_reach(emu, rec, Goal(tx, ty, -1), max_frames=72, rng=rng)     # dodge while it burns
                emu.step = rec.step
                for _ in range(30):
                    if emu.byte(0xEE) != doors0:
                        break
                    rec.step((), 1)
                if emu.byte(0xEE) != doors0:
                    break
            else:
                return "the wall never opened"
            s = nav.exit_screen(direction)
            return "through" if (then_room is None or s.room == then_room) else "odd"
        except (NavError, bot.BotError, LinkDied) as e:
            return "nav: " + str(e)[:40]
        finally:
            emu.step = orig
    return policy


'''
t = t.replace(anchor, new + anchor)
ast.parse(t)
p.write_bytes((t.replace("\n", "\r\n") if crlf else t).encode("utf-8"))
q = pathlib.Path("probe_chain.py"); s = q.read_text(encoding="utf-8")
s = s.replace('''    ("grab 4C floor key", lambda nav: make_grab_policy(nav, None), lambda s: s.room == 0x4C),
    ("bomb N 4C->3C", lambda nav: fg.bomb_policy(nav, "Up", 0x3C), lambda s: s.room == 0x3C)]),''',
 '''    ("dash-bomb N 4C->3C", lambda nav: fg.dash_bomb_policy(nav, "Up", 0x3C), lambda s: s.room == 0x3C)]),''')
q.write_text(s, encoding="utf-8")
print("dash_bomb_policy added")
