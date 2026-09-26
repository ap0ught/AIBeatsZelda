"""Bold where it is cheap, careful where it is not. Going through everything put Link into Level 4 on ONE heart:
a Lynel on the White Sword trek hits for one or two hearts, not the half heart of an Octorok. Heavy hitters get
a wide berth again, avoidance grows as health falls, and each attempt draws its own caution so the search can
weigh a wider line against a faster one."""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import ast, pathlib
def load(p):
    raw = pathlib.Path(p).read_bytes(); return raw.decode("utf-8").replace("\r\n", "\n"), b"\r\n" in raw
def save(p, t, crlf):
    ast.parse(t); pathlib.Path(p).write_bytes((t.replace("\n", "\r\n") if crlf else t).encode("utf-8"))
def sub(t, old, new, what):
    assert t.count(old) == 1, (what, t.count(old)); print("  applied:", what); return t.replace(old, new)
t, crlf = load("zelda/overworld.py")
t = sub(t, '''            if d < 16:
                pen += 5 * hh
            elif d < 28:
                pen += 1.5 * hh
            elif d < 44 and hh >= 3:
                pen += 1.0 * hh''', '''            if hh >= 3:
                # one or two HEARTS a touch (Lynels, Blue Darknuts, Wizzrobes, Gibdos): these are not
                # the "basic mobs" worth walking through - keep a real distance
                if d < 24:
                    pen += 25 * hh
                elif d < 40:
                    pen += 5 * hh
                elif d < 56:
                    pen += 1.5 * hh
            elif d < 16:
                pen += 5 * hh
            elif d < 28:
                pen += 1.5 * hh''', "wide berth for heavy hitters")
t = sub(t, '''            pen_scale = 1.0 if OLD_AVOIDANCE[0] else (4.0 if s.hearts <= 2.0 else 2.0 if s.hearts <= 3.0 else 1.0)
''', '''            pen_scale = 1.0 if OLD_AVOIDANCE[0] else (
                (5.0 if s.hearts <= 2.0 else 2.5 if s.hearts <= 3.0 else 1.5 if s.hearts < 6.0 else 1.0)
                * getattr(self, "avoid_bias", 1.0))
''', "avoidance grows as health falls; per-attempt bias")
save("zelda/overworld.py", t, crlf)

t, crlf = load("zelda/search.py")
t = sub(t, '''        nav.jitter = (rng, rng.choice([0.05, 0.12, 0.25] if OLD_AVOIDANCE[0] else [0.0, 0.0, 0.04, 0.10, 0.18]))''',
        '''        nav.jitter = (rng, rng.choice([0.05, 0.12, 0.25] if OLD_AVOIDANCE[0] else [0.0, 0.0, 0.04, 0.10, 0.18]))
        nav.avoid_bias = rng.choice([1.0, 1.0, 1.0, 2.5, 6.0])      # some attempts bold, some careful''', "per-attempt caution in crossings")
t = sub(t, '''        finally:
            emu.step = orig_step
            nav.jitter = None
    return policy


def random_search(''', '''        finally:
            emu.step = orig_step
            nav.jitter = None
            nav.avoid_bias = 1.0
    return policy


def random_search(''', "reset bias") if '''        finally:
            emu.step = orig_step
            nav.jitter = None
    return policy


def random_search(''' in t else t
save("zelda/search.py", t, crlf)

t, crlf = load("zelda/lookahead.py")
t = sub(t, '''                    near = sum(max(0, 28 - max(abs(e[2] - s2.x), abs(e[3] - s2.y))) for e in ens)''',
        '''                    from .overworld import harm_halfhearts
                    near = sum(max(0, (28 if harm_halfhearts(e[1]) < 3 else 44) - max(abs(e[2] - s2.x), abs(e[3] - s2.y)))
                               * max(1.0, harm_halfhearts(e[1]) / 2.0) for e in ens)''', "plan_reach keeps further from heavy hitters")
save("zelda/lookahead.py", t, crlf)
print("careful where it matters")
