"""Replace secret_cave_policy with a version that can also WALK into an already-drawn cave, and add
hold_through_policy for gaps the navigator believes are solid rock. Written as a file because the
same patch inline in a shell heredoc died on quoting."""
import ast
import pathlib

p = pathlib.Path("fullgame.py")
raw = p.read_bytes()
crlf = b"\r\n" in raw
t = raw.decode("utf-8").replace("\r\n", "\n")
a = t.index("def secret_cave_policy(")
b = t.index("def cross(d, room, tries=30):")

NEW = '''def secret_cave_policy(nav, stand, face, method, want=30, budget=900):
    """Open a secret rupee cave (or walk into one already drawn), take the money, walk back out.

    method: "push" leans on the Armos from `stand`; "bomb" blows the rock in front of `stand`;
    "walk" is for a staircase already drawn on the screen (stand may be None).

    All of it was learned by probing. The navigator stands on the exact tile (the planner alone reached
    0x3D's spot one time in three) with the planner as fallback. A bombed doorway only shows up as tiles
    that CHANGED, so the screen is photographed first. Link enters a cave at the bottom, the gift sits in
    the middle and the room-item slot reads empty for it, so the money is found by walking north watching
    $066D - and a 100-rupee gift is counted up one rupee at a time, so wait for the WHOLE amount (a probe
    that stopped early read +46 on 0x0F's hundred). Owner's rule: never farm; the caves hold 550 rupees."""
    from zelda.lookahead import plan_reach
    from zelda.overworld import read_cells
    from zelda import secrets

    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        try:
            rec.step((), rng.randint(0, 8))
            before = emu.byte(0x66D)
            if method == "bomb" and emu.state().bombs < 1:
                return "no bombs to open it with"
            emu.step = rec.step
            base = None
            if method != "walk":
                try:
                    nav.go(lambda x, y: (x, y) == stand, "the cave spot", optimistic=True, max_replans=60)
                except NavError:
                    emu.step = orig
                    plan_reach(emu, rec, Goal(stand[0], stand[1], 3), max_frames=budget, rng=rng)
                    emu.step = rec.step
                st = emu.state()
                for _ in range(60):
                    if (st.x, st.y) == stand:
                        break
                    st = rec.step(("Right" if st.x < stand[0] else "Left") if st.x != stand[0]
                                  else ("Down" if st.y < stand[1] else "Up"), 1)
                if (st.x, st.y) != stand:
                    return f"could not stand at {stand}"
                base = read_cells(emu)
                if method == "push":
                    for _ in range(140):
                        if emu.state().mode in (0x0B, 0x10) or secrets.opening(emu, base):
                            break
                        rec.step(face, 1)
                else:
                    if not bot.select_b_item(emu, rec.step, bot.B_BOMBS):
                        return "could not select bombs"
                    rec.step(face, 1)
                    rec.step("B", 2)
                    for _ in range(150):
                        rec.step((), 1)
            st = emu.state()
            for _ in range(400):                               # onto the staircase
                if st.mode in (0x0B, 0x10):
                    break
                op = secrets.opening(emu, base) if base is not None else secrets.opening(emu)
                if op is None:
                    st = rec.step(face, 1)
                    continue
                dx, dy = op[0] - st.x, op[1] - st.y
                st = rec.step(("Right" if dx > 0 else "Left") if abs(dx) > 2 else ("Down" if dy > 0 else "Up"), 1)
            if emu.state().mode not in (0x0B, 0x10):
                return "never got into the cave"
            for _ in range(400):                               # let the cave finish loading
                st = emu.state()
                if st.mode == 0x0B and st.y > 150:
                    break
                rec.step((), 2)
            target = min(255, before + want)
            for _ in range(700):                               # onto the money, and let it count up
                st = emu.state()
                if emu.byte(0x66D) >= target:
                    break
                rec.step("Right" if st.x < 116 else "Left" if st.x > 124 else ("Up" if st.y > 140 else ()), 1)
            got = emu.byte(0x66D) - before
            for _ in range(260):                               # back out
                if emu.state().mode == 5:
                    break
                rec.step("Down", 1)
            for _ in range(200):
                st = emu.state()
                if st.mode == 5 and st.level == 0:
                    break
                rec.step((), 2)
            return f"took {got}" if got > 0 else "the cave paid nothing"
        except (NavError, LinkDied, bot.BotError) as e:
            return "fail: " + str(e)[:40]
        finally:
            emu.step = orig
    return policy


def hold_through_policy(nav, x, direction, to_room, budget=400):
    """Walk through a gap the navigator believes is solid rock.

    0x1F's top edge reads as unbroken rock in the tile map and nav.exit_screen refuses it at every
    column, yet holding Up at x=128 walks straight into 0x0F - the screen with the guide's 100-rupee
    cave. Get to that column near the edge with the navigator, square up, and hold the direction."""
    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        emu.step = rec.step
        try:
            rec.step((), rng.randint(0, 8))
            if direction == "Up":
                near = lambda px, py: px == x and py <= 93
            else:
                near = lambda px, py: px == x and py >= 189
            try:
                nav.go(near, f"the gap at x={x}", optimistic=True, max_replans=60)
            except (NavError, LinkDied):
                pass
            st = emu.state()
            for _ in range(60):
                if st.x == x:
                    break
                st = rec.step("Right" if st.x < x else "Left", 1)
            start = st.room
            for _ in range(budget):
                if st.room != start:
                    break
                st = rec.step(direction, 1)
            for _ in range(200):
                if emu.state().mode == 5:
                    break
                rec.step((), 2)
            r = emu.state().room
            return "through" if r == to_room else f"ended on {r:02X}"
        except (NavError, LinkDied) as e:
            return "fail: " + str(e)[:40]
        finally:
            emu.step = orig
    return policy


'''

t = t[:a] + NEW + t[b:]
ast.parse(t)
p.write_bytes((t.replace("\n", "\r\n") if crlf else t).encode("utf-8"))
print("patched: secret_cave_policy (with walk mode) and hold_through_policy")
