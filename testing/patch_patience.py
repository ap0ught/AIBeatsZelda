import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import ast, pathlib
p = pathlib.Path("zelda/search.py"); raw = p.read_bytes(); crlf = b"\r\n" in raw
t = raw.decode("utf-8").replace("\r\n", "\n")
old = '''                if best is None:
                    limit = patience * 2
                elif HEARTS_FREE[0] or best.hearts >= min(c, st["h0"]):
                    limit = max(4, patience - 2)     # unhurt (or hearts are free): little left to find'''
new = '''                if best is None:
                    limit = patience * 2
                elif HEARTS_FREE[0]:
                    # a boss: attempts differ by a factor of two or more (Gleeok: 964 one run, 2,346 the next
                    # after stopping at six), and with four scouts the extra attempts are cheap
                    limit = patience * 3
                elif best.hearts >= min(c, st["h0"]):
                    limit = max(4, patience - 2)     # unhurt: little left to find'''
assert t.count(old) == 1
t = t.replace(old, new)
ast.parse(t)
p.write_bytes((t.replace("\n", "\r\n") if crlf else t).encode("utf-8"))
print("boss patience x3")
