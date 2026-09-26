"""plan(): once Link is standing on the stepladder he can only keep going along it. The planner let him
turn sideways on a bridged water tile; the game does not, so rooms like Level 4's dark Keese room (two
one-tile water gaps on the way to the east door) burned their attempts on BLOCKED moves."""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import ast, pathlib
p = pathlib.Path("zelda/overworld.py"); raw = p.read_bytes(); crlf = b"\r\n" in raw
t = raw.decode("utf-8").replace("\r\n", "\n")
old = '''        for d, (dx, dy) in DIRS.items():
            nxt = (cur[0] + dx, cur[1] + dy)
            ok_cells = None
            if cells_ok:
                ok_cells = cells_ok[0] if d in ("Up", "Down") else cells_ok[1]
            if (cur, d) in blocked:
                continue
'''
new = '''        # Standing on the stepladder (his box overlaps bridged water), Link can only carry on along
        # the axis he stepped onto it by - the game will not let him turn off its side.
        on_ladder_axis = None
        if cells_ok and prev[cur] is not None:
            if any(c in cells_ok[0] or c in cells_ok[1] for c in box_cells(*cur)):
                on_ladder_axis = prev[cur][1] in ("Up", "Down")
        for d, (dx, dy) in DIRS.items():
            nxt = (cur[0] + dx, cur[1] + dy)
            ok_cells = None
            if cells_ok:
                ok_cells = cells_ok[0] if d in ("Up", "Down") else cells_ok[1]
            if (cur, d) in blocked:
                continue
            if on_ladder_axis is not None and (d in ("Up", "Down")) != on_ladder_axis:
                continue
'''
assert t.count(old) == 1
t = t.replace(old, new)
ast.parse(t)
p.write_bytes((t.replace("\n", "\r\n") if crlf else t).encode("utf-8"))
print("ladder axis rule added")
