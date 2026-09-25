import ast, pathlib
p = pathlib.Path("fullgame.py"); raw = p.read_bytes(); crlf = b"\r\n" in raw
t = raw.decode("utf-8").replace("\r\n", "\n")
old = '''                if st.x < 40:
                    rec.step("Right", 40 - st.x)             # room for the notes before the wind arrives
                    if face == "Left":
                        face = "Down"
                room0 = emu.state().room'''
new = '''                # Items cannot be used inside the screen's border strip (a note played at x=240, just off
                # the edge Link walked in by, simply does not sound), and the wind arrives from the left,
                # so keep clear of that side too while there are notes left to play.
                if st.x > 208:
                    rec.step("Left", st.x - 208)
                elif st.x < 48:
                    rec.step("Right", 48 - st.x)
                if st.y > 189:
                    rec.step("Up", st.y - 189)
                elif st.y < 85:
                    rec.step("Down", 85 - st.y)
                st = emu.state()
                if idx == goal:
                    faces = ["Right", "Left"]                # away one level and straight back
                else:
                    faces = [face] * notes
                room0 = st.room
                played = 0
                for face in faces:
                    rec.step(face, 1)
                    rec.step("B", 2)
                    if emu.byte(0x3C) == 0:
                        rec.step((), 2)
                    if emu.byte(0x3C) == 0:
                        break                                # the note did not sound: re-plan from RAM
                    played += 1
                    for _ in range(200):                     # the tune: the whole game is frozen
                        if emu.byte(0x3C) == 0:
                            break
                        rec.step((), 1)
                if not played:
                    rec.step("Right" if st.x < 120 else "Left", 16)
                    continue
                if 0x2E not in emu.ram(0x34F, 12) and emu.byte(0x522) == 0:
                    # no free object slot for the wind (the counter still moved): thin the screen out
                    from zelda.lookahead import plan_fight
                    emu.step = orig
                    plan_fight(emu, rec, max_frames=500, rng=rng)
                    emu.step = rec.step
                    continue
                notes = 0'''
assert t.count(old) == 1
t = t.replace(old, new)
old2 = '''                for n in range(notes):
                    rec.step(face, 1)
                    rec.step("B", 2)
                    for _ in range(200):                     # the tune: the whole game is frozen
                        if emu.byte(0x3C) == 0:
                            break
                        rec.step((), 1)
                for _ in range(900):                         # the ride'''
new2 = '''                for _ in range(900):                         # the ride'''
assert t.count(old2) == 1
t = t.replace(old2, new2)
ast.parse(t)
p.write_bytes((t.replace("\n", "\r\n") if crlf else t).encode("utf-8"))
print("whirl policy: border strip, idx==goal, no free slot")
