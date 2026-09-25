import ast, pathlib
def load(p):
    raw = pathlib.Path(p).read_bytes(); return raw.decode("utf-8").replace("\r\n", "\n"), b"\r\n" in raw
def save(p, t, crlf):
    ast.parse(t); pathlib.Path(p).write_bytes((t.replace("\n", "\r\n") if crlf else t).encode("utf-8"))
t, crlf = load("zelda/lookahead.py")
old = '''            offer_bombs = s0.bombs > 0 and near_target and s0.level != 9 and ('''
new = '''            # ...and never the last two: the route bombs walls (Level 1's 53, the 0x67 cave, Level 5's two)
            # and a fight that spends the bomb a wall needed stops the whole run at that wall.
            offer_bombs = s0.bombs > (0 if use_bombs == "free" else 2) and near_target and s0.level != 9 and ('''
assert t.count(old) == 1
t = t.replace(old, new)
save("zelda/lookahead.py", t, crlf)
t, crlf = load("fullgame.py")
old = '''          ("5b_bombs", lambda nav: make_clear_policy(nav, "Up"), 0x4B, 80, {"bombs": 1}),'''
new = '''          ("5b_bombs", lambda nav: make_lafight_policy(nav, "Up"), 0x4B, 80, {"bombs": 1}),'''
assert t.count(old) == 1
t = t.replace(old, new)
old = '''          ("4a_bombs", lambda nav: make_clear_policy(nav, "Left"), 0x49, 60, {}),'''
new = '''          ("4a_bombs", lambda nav: make_lafight_policy(nav, "Left"), 0x49, 60, {"bombs": 5}),'''
assert t.count(old) == 1
t = t.replace(old, new)
save("fullgame.py", t, crlf)
print("bomb reserve; L3 bomb rooms use the lookahead fighter")
