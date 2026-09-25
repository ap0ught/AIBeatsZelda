import ast, pathlib
p = pathlib.Path("zelda/bot.py"); raw = p.read_bytes(); crlf = b"\r\n" in raw
t = raw.decode("utf-8").replace("\r\n", "\n")
old = '''    step("Start", 1)
    for _ in range(90):
        if emu.byte(0xE1) == 7:
            break
        step((), 1)
    for _ in range(12):'''
new = '''    step("Start", 1)
    # MenuState ($E1) counts up, sits on one value for the ~56-frame scroll, then steps once more when the
    # menu goes live (6 -> 7 in a dungeon, 7 -> 8 outside): wait for the step that ends the long plateau.
    last, run = emu.byte(0xE1), 0
    for _ in range(120):
        step((), 1)
        v = emu.byte(0xE1)
        if v != last:
            if run > 20:
                break
            last, run = v, 0
        else:
            run += 1
    for _ in range(12):'''
assert t.count(old) == 1
t = t.replace(old, new)
ast.parse(t)
p.write_bytes((t.replace("\n", "\r\n") if crlf else t).encode("utf-8"))
print("menu polling fixed")
