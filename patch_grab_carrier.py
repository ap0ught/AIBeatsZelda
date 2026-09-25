import ast, pathlib
p = pathlib.Path("zelda/segments.py"); raw = p.read_bytes(); crlf = b"\r\n" in raw
t = raw.decode("utf-8").replace("\r\n", "\n")
old = '''            Fighter(nav).grab_key_by_dodging()
            if read_room_item(emu) is not None:
                return "item not taken"'''
new = '''            Fighter(nav).grab_key_by_dodging()
            if read_room_item(emu) is not None:
                # Still there after standing on it: something is CARRYING it (a Stalfos holds a key in
                # Level 1 - the "item" moves about with it). Kill the carrier and take what it drops. The old
                # navigator got this by accident: it waited on the Stalfos in its way and then killed it.
                from .lookahead import plan_fight

                def carrier(e):
                    it = read_room_item(e)
                    if it is None:
                        return []
                    near = [q for q in read_enemies(e) if q[1] < 0x40 and max(abs(q[2] - it[1]), abs(q[3] - it[2])) <= 12]
                    return near[:1]
                if carrier(emu):
                    emu.step = orig
                    plan_fight(emu, rec, max_frames=1500, rng=rng, targets=carrier,
                               done=lambda e: not carrier(e), log=True)
                    emu.step = rec.step
                    for _ in range(10):
                        if read_room_item(emu) is not None:
                            break
                        rec.step((), 4)
                    Fighter(nav).grab_key_by_dodging()
            if read_room_item(emu) is not None:
                return "item not taken"'''
assert t.count(old) == 1
t = t.replace(old, new)
ast.parse(t)
p.write_bytes((t.replace("\n", "\r\n") if crlf else t).encode("utf-8"))
print("grab policy kills a carrier")
