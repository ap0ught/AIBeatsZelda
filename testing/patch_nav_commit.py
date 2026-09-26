"""Stop the navigator flip-flopping: a Zol hovering by the far side of a ladder crossing made the route 'through it'
and the route 'all the way round' swap places every two steps, and Link paced 64->80->64 for 60 re-plans (Level 5
room 57, 60 attempts out of 60). Weak killable enemies now cost about what cutting them down costs, and turning
straight back on the last step costs extra."""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import ast, pathlib
p = pathlib.Path("zelda/overworld.py"); raw = p.read_bytes(); crlf = b"\r\n" in raw
t = raw.decode("utf-8").replace("\r\n", "\n")
def sub(old, new, what):
    global t
    assert t.count(old) == 1, (what, t.count(old)); t = t.replace(old, new); print("  applied:", what)
sub('''            elif d < 16:
                pen += 5 * hh
            elif d < 28:
                pen += 1.5 * hh''', '''            elif t < 0x40 and t not in _NO_CUT:
                # weak and killable: walking through its patch should cost about what cutting it down does
                # (two swings, ~5 steps in all), not a detour round the room
                if d < 16:
                    pen += 2.5
                elif d < 28:
                    pen += 0.8
            elif d < 16:
                pen += 5 * hh
            elif d < 28:
                pen += 1.5 * hh''', "weak killable enemies cost a swing, not a detour")
sub('''AVOID = [1.0]''', '''AVOID = [1.0]
_NO_CUT = {0x49, 0x2B, 0x2C, 0x2D, 0x40, 0x11, 0x1A, 0x01, 0x02, 0x0B, 0x0C}   # traps, Bubbles, Zora, Peahat, Lynel, Darknut''', "_NO_CUT")
sub('''def plan(cells, kb: TileKB, start: tuple[int, int], goal, optimistic: bool = False,
         blocked: set | None = None, enemies=(), extra: set | None = None, forbid=None,
         cells_ok: set | None = None, pen_scale: float = 1.0) -> list[str] | None:''',
    '''def plan(cells, kb: TileKB, start: tuple[int, int], goal, optimistic: bool = False,
         blocked: set | None = None, enemies=(), extra: set | None = None, forbid=None,
         cells_ok: set | None = None, pen_scale: float = 1.0, reluctant: str | None = None) -> list[str] | None:''', "plan(): reluctant first step")
sub('''            nc = cost + 1 + (enemy_penalty(enemies, nxt[0], nxt[1], pen_scale) if enemies else 0)''',
    '''            nc = cost + 1 + (enemy_penalty(enemies, nxt[0], nxt[1], pen_scale) if enemies else 0)
            if reluctant is not None and cur == start and d == reluctant:
                nc += 12                     # turning straight back is only right when it clearly pays''', "reversal cost")
sub('''            path = plan(cells, self.kb, (s.x, s.y), goal, optimistic, self.blocked.get(key), enemies, extra,
                        cells_ok=cells_ok, forbid=ent_forbid, pen_scale=pen_scale)''',
    '''            path = plan(cells, self.kb, (s.x, s.y), goal, optimistic, self.blocked.get(key), enemies, extra,
                        cells_ok=cells_ok, forbid=ent_forbid, pen_scale=pen_scale,
                        reluctant=None if OLD_AVOIDANCE[0] else _OPP.get(last_dir))''', "go(): pass the last direction")
sub('''        swung: dict = {}
        while attempt < max_replans and s.frame - f_start < frames_budget:''', '''        swung: dict = {}
        last_dir = None
        while attempt < max_replans and s.frame - f_start < frames_budget:''', "go(): last_dir init")
sub('''                s = r
                if (s.x, s.y) == target:''', '''                s = r
                last_dir = d
                if (s.x, s.y) == target:''', "go(): track last_dir")
sub('''class NavError(RuntimeError):''', '''_OPP = {"Up": "Down", "Down": "Up", "Left": "Right", "Right": "Left"}


class NavError(RuntimeError):''', "_OPP")
ast.parse(t)
p.write_bytes((t.replace("\n", "\r\n") if crlf else t).encode("utf-8"))
print("navigator commits to a direction")
