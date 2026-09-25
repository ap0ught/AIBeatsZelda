import ast, pathlib
def load(p):
    raw = pathlib.Path(p).read_bytes(); return raw.decode("utf-8").replace("\r\n", "\n"), b"\r\n" in raw
def save(p, t, crlf):
    ast.parse(t); pathlib.Path(p).write_bytes((t.replace("\n", "\r\n") if crlf else t).encode("utf-8"))
t, crlf = load("fullgame.py")
old = '''            rec.step((), rng.randint(0, 90))
            return "dead" if Manhandla(nav, rng).fight(max_frames=2500) else "alive"
        except LinkDied:
            return "died"'''
new = '''            rec.step((), rng.randint(0, 30))
            rec.step("Right" if emu.state().x <= 32 else (), 16)      # out of the bombed doorway
            # The scripted bomber (zelda.boss.Manhandla) died 60 times out of 60 from the third run's state.
            # The lookahead fighter with bombs free to use killed it 8 of 8 in 190-260 frames: it SEES, in
            # its rollouts, where a blast catches the heads and where standing gets Link hit.
            from zelda.lookahead import plan_fight
            emu.step = orig
            res = plan_fight(emu, rec, max_frames=2500, rng=rng, use_bombs="free", log=True)
            return "dead" if res == "clear" else res
        except LinkDied:
            return "died"'''
assert t.count(old) == 1
t = t.replace(old, new)
save("fullgame.py", t, crlf)
t, crlf = load("zelda/lookahead.py")
old = '''    if CAUTION_OVERRIDE[0] is not None:
        return CAUTION_OVERRIDE[0]
    h, c = s.hearts, max(1, s.containers)'''
new = '''    h, c = s.hearts, max(1, s.containers)
    if CAUTION_OVERRIDE[0] is not None and h > 3.5:
        return CAUTION_OVERRIDE[0]           # a refill is coming - but only while there is health to spend'''
assert t.count(old) == 1
t = t.replace(old, new)
save("zelda/lookahead.py", t, crlf)
print("manhandla: lookahead with bombs; caution override only with health to spend")
