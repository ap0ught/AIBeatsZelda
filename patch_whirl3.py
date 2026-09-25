import ast, pathlib
p = pathlib.Path("fullgame.py"); raw = p.read_bytes(); crlf = b"\r\n" in raw
t = raw.decode("utf-8").replace("\r\n", "\n")
old = '''                for _ in range(900):                         # the ride
                    q = rec.step((), 1)
                    if q.room != room0 and q.mode == 5 and emu.byte(0x522) == 0 and not (emu.byte(0xAC) & 0x40):
                        break
                else:
                    return "the wind never came"'''
new = '''                # The ride. The wind can MISS: while Link is flashing from a hit the game skips his
                # collisions, the wind's included (a Zora's fireball did exactly this on 0x47). If it sweeps
                # past, the counter has still moved - re-plan from RAM rather than wait for nothing.
                landed = False
                for f in range(900):
                    q = rec.step((), 1)
                    if q.room != room0 and q.mode == 5 and emu.byte(0x522) == 0 and not (emu.byte(0xAC) & 0x40):
                        landed = True
                        break
                    if (f > 8 and f % 4 == 0 and q.room == room0 and emu.byte(0x522) == 0
                            and 0x2E not in emu.ram(0x34F, 12)):
                        break
                if not landed:
                    continue'''
assert t.count(old) == 1
t = t.replace(old, new)
ast.parse(t)
p.write_bytes((t.replace("\n", "\r\n") if crlf else t).encode("utf-8"))
print("whirl: re-plan when the wind misses")
