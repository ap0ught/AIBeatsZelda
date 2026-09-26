import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import ast, pathlib
p = pathlib.Path("zelda/overworld.py"); raw = p.read_bytes(); crlf = b"\r\n" in raw
t = raw.decode("utf-8").replace("\r\n", "\n")
old = '''            stuck[pos] = not any(ok(pos[0], pos[1], d) for d in ("Up", "Down"))                and not legal(cells, kb, pos[0], pos[1], optimistic, extra)'''
assert t.count(old) == 1, t.count(old)
new = '''            # Standing on the stepladder is NOT being stuck. This only checked the vertical bridge
            # set, so a position on a HORIZONTAL ladder crossing counted as "stuck in scenery" and
            # was allowed to move anywhere at all - straight up a river, for instance.
            stuck[pos] = not any(ok(pos[0], pos[1], d) for d in ("Up", "Down", "Left", "Right")) \
                and not legal(cells, kb, pos[0], pos[1], optimistic, extra)'''
t = t.replace(old, new)
ast.parse(t)
p.write_bytes((t.replace("\n", "\r\n") if crlf else t).encode("utf-8"))
print("escaping() fixed")
