import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import ast, pathlib
p = pathlib.Path("fullgame.py"); raw = p.read_bytes(); crlf = b"\r\n" in raw
t = raw.decode("utf-8").replace("\r\n", "\n")
old = '''                landed = False
                for f in range(900):
                    q = rec.step((), 1)
                    if q.room != room0'''
new = '''                landed = False
                stuck, lastx = 0, -1
                for f in range(900):
                    # walk to meet the wind along its row: a moving Link is a harder target for whatever is
                    # shooting at him, and it costs nothing (the ride is just as long wherever it starts)
                    meet = emu.byte(0x522) == 0 and stuck < 6 and emu.state().x > 56
                    q = rec.step("Left" if meet else (), 1)
                    stuck = stuck + 1 if (meet and q.x == lastx) else 0 if meet else stuck
                    lastx = q.x
                    if q.room != room0'''
assert t.count(old) == 1
t = t.replace(old, new)
ast.parse(t)
p.write_bytes((t.replace("\n", "\r\n") if crlf else t).encode("utf-8"))
print("whirl: walk to meet the wind")
