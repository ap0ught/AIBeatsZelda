"""Fixed waits: the whirlwind (one ride, several notes, the counter read from RAM), the subscreen (polled),
block pushes (polled).

WHIRLWIND, from the disassembly (Z_07 WieldFlute, Z_01 SummonWhirlwind/UpdateWhirlwind):
  * the destination counter is RAM $523 (TeleportingLevelIndex & 7 -> Level 1..8). Every recorder use on the
    overworld moves it one OWNED level forward (Link facing Right/Up) or back (Left/Down) - whether or not a
    whirlwind is already on screen - and the destination is read when the wind PICKS LINK UP.
  * the whole game freezes for the $98-frame tune, the wind included; a press during the freeze is ignored.
  So: read the counter, play as many notes as the target is steps away, each the moment the last tune ends,
  and take ONE ride. The old policy pressed again 141 frames after a note - inside the freeze - so its extra
  notes were lost, every ride moved one level (Level 1 -> Level 6 was three rides, 2,082 frames), and with the
  counter unknown it spent a whole ride finding out where it was. It also stood 50-140 frames after landing.
"""
import ast
import pathlib


def load(path):
    raw = pathlib.Path(path).read_bytes()
    return raw.decode("utf-8").replace("\r\n", "\n"), b"\r\n" in raw


def save(path, t, crlf):
    ast.parse(t)
    pathlib.Path(path).write_bytes((t.replace("\n", "\r\n") if crlf else t).encode("utf-8"))


# ------------------------------------------------------------------ whirlwind
t, crlf = load("fullgame.py")
a = t.index("def whirl_to_policy(nav, target, counter=None):")
b = t.index("def shop_policy(nav, want_addr, xs=(152, 120, 72)):")
NEW = '''def whirl_to_policy(nav, target, counter=None):
    """Ride the recorder's whirlwind to a finished dungeon's door: one ride, as many notes as it takes.

    From the disassembly (Z_07 WieldFlute, Z_01 SummonWhirlwind / UpdateWhirlwind):
      * the destination counter is RAM $523 (TeleportingLevelIndex; & 7 -> Levels 1..8). Every recorder use
        on the overworld moves it one OWNED level forward (Link facing Right or Up) or back (Left or Down),
        even with a whirlwind already on screen, and the destination is read when the wind picks Link up.
      * the game freezes for the $98-frame tune - the wind too - and a press during the freeze is ignored.
    So read the counter, play one note per step the moment the previous tune ends, and take ONE ride.
    `counter` is ignored now (kept for the call sites): the RAM byte is the truth.
    0x42 is Level 7's pond, where the recorder drains the water instead; step off it first."""
    POND = 0x42

    def owned_steps(idx, goal, step, tri):
        n, i = 0, idx
        while n < 9:
            i = (i + step) % 8
            if tri & (1 << i):
                n += 1
                if i == goal:
                    return n
        return 99

    def policy(emu, rec, rng, max_frames):
        orig = emu.step
        emu.step = rec.step
        try:
            rec.step((), rng.randint(0, 6))
            goal = LEVEL_DOORS.index(target)
            for ride in range(4):
                st = emu.state()
                if st.room == target and st.mode == 5 and not st.level:
                    return "arrived"
                if st.level:
                    bot.hold_until(emu, "Down", lambda q: q.level == 0 and q.mode == 5, 600)
                    continue
                if st.room == POND:
                    nav.exit_screen("Down")
                    continue
                if not bot.select_b_item(emu, rec.step, bot.B_RECORDER):
                    return "could not select the recorder"
                st = emu.state()
                tri = emu.byte(0x671)
                idx = emu.byte(0x523) & 7
                up, down = owned_steps(idx, goal, 1, tri), owned_steps(idx, goal, -1, tri)
                if min(up, down) >= 99:
                    return "that level's Triforce is not owned"
                notes = min(up, down)
                # the facing picks the direction; never face off the edge of the screen
                if up <= down:
                    face = "Up" if st.x >= 224 else "Right"
                else:
                    face = "Down" if st.x <= 16 else "Left"
                if st.x < 40:
                    rec.step("Right", 40 - st.x)             # room for the notes before the wind arrives
                    if face == "Left":
                        face = "Down"
                room0 = emu.state().room
                for n in range(notes):
                    rec.step(face, 1)
                    rec.step("B", 2)
                    for _ in range(200):                     # the tune: the whole game is frozen
                        if emu.byte(0x3C) == 0:
                            break
                        rec.step((), 1)
                for _ in range(900):                         # the ride
                    q = rec.step((), 1)
                    if q.room != room0 and q.mode == 5 and emu.byte(0x522) == 0 and not (emu.byte(0xAC) & 0x40):
                        break
                else:
                    return "the wind never came"
            st = emu.state()
            return "arrived" if (st.room == target and not st.level) else f"stopped at {st.room:02X}"
        except (NavError, LinkDied, bot.BotError) as e:
            return "fail: " + str(e)[:40]
        finally:
            emu.step = orig
    return policy


'''
t = t[:a] + NEW + t[b:]
save("fullgame.py", t, crlf)
print("  applied: whirl_to_policy rewritten")

# ------------------------------------------------------------------ subscreen polling
t, crlf = load("zelda/bot.py")
old = '''    step("Start", 2); step((), 60)
    for _ in range(16):
        if b_item(emu) == want:
            break
        step("Right", 2); step((), 10)
    step("Start", 2); step((), 60)
    ok = b_item(emu) == want'''
new = '''    # Measured (probe_menu.py): the subscreen takes 62 frames to scroll in (MenuState $E1 counts 2..6, then 7
    # = ready), the cursor moves on every fresh press, and it takes 58 frames to scroll out. Poll instead of
    # waiting a flat 60 + 12 per move + 60.
    step("Start", 1)
    for _ in range(90):
        if emu.byte(0xE1) == 7:
            break
        step((), 1)
    for _ in range(12):
        if b_item(emu) == want:
            break
        step("Right", 1); step((), 1)
    step("Start", 1)
    for _ in range(90):
        if emu.byte(0xE1) == 0:
            break
        step((), 1)
    ok = b_item(emu) == want'''
assert t.count(old) == 1
t = t.replace(old, new)
save("zelda/bot.py", t, crlf)
print("  applied: select_b_item polls the menu state")

# ------------------------------------------------------------------ block pushes polled
t, crlf = load("zelda/overworld.py")
old = '''                for _ in range(90):
                    emu.step(push, 1)
                now = read_cells(emu)
                if any(now[r][c] != before[r][c] for r in range(22) for c in range(32)):'''
new = '''                for i in range(90):
                    emu.step(push, 1)
                    # stop the moment the tile map changes instead of leaning on it for 90 frames
                    if i >= 12 and i % 3 == 0:
                        now = read_cells(emu)
                        if any(now[r][c] != before[r][c] for r in range(22) for c in range(32)):
                            break
                now = read_cells(emu)
                if any(now[r][c] != before[r][c] for r in range(22) for c in range(32)):'''
assert t.count(old) == 1
t = t.replace(old, new)
save("zelda/overworld.py", t, crlf)
print("  applied: push_any_block stops when the block moves")
