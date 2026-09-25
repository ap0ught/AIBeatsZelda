import ast, pathlib
p = pathlib.Path("zelda/lookahead.py"); raw = p.read_bytes(); crlf = b"\r\n" in raw
t = raw.decode("utf-8").replace("\r\n", "\n")
def sub(old, new, what):
    global t
    assert t.count(old) == 1, (what, t.count(old)); t = t.replace(old, new); print("  applied:", what)
sub('''            # spending a bomb has to pay for itself: the score already gives 150 a kill, so this''',
    '''            # A key spent on a door nobody asked for is a locked door later with no key: Level 4's Vire room
            # has a locked north door the route never uses, Link brushed it mid-fight, and three rooms on the
            # run stopped dead at the door the key was for.
            if s2.keys < s0.keys:
                sc -= 6000
            # spending a bomb has to pay for itself: the score already gives 150 a kill, so this''', "plan_fight: never spend a key")
sub('''                    sc = -800 * dmg_scale * (s0.hearts - s2.hearts) * 2''',
    '''                    sc = -800 * dmg_scale * (s0.hearts - s2.hearts) * 2
                    if s2.keys < s0.keys:
                        sc -= 6000              # a dash never unlocks a door on the way''', "plan_reach: never spend a key")
ast.parse(t)
p.write_bytes((t.replace("\n", "\r\n") if crlf else t).encode("utf-8"))
