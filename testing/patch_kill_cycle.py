"""Steer the ordinary bomb drops. The drop table's column is the kill cycle ($52A), advanced just before the
drop is chosen; only "row 2" monsters have bombs in their row, at columns 1, 6 and 8. So when bombs are wanted and
the cycle stands at 0, 5 or 7, the NEXT kill should be a row-2 monster if one is in the room (41 % of those drop
bombs). A nudge in plan_fight's scoring, nothing more: the search's bomb-aware ranking keeps the attempts where
it paid."""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import pathlib

p = pathlib.Path("zelda/lookahead.py")
t = p.read_text(encoding="utf-8")

old = "BOMB_TARGET = [6]"
new = ("ROW2 = {0x09, 0x0A, 0x03, 0x01, 0x12, 0x06, 0x0B, 0x24, 0x30}   # the only monsters with bombs in their drop row\n"
       + old)
assert t.count(old) == 1
t = t.replace(old, new, 1)

old = """        streak_bomb = want_bombs and help_n == 9 and streak_patience > 0
"""
new = """        streak_bomb = want_bombs and help_n == 9 and streak_patience > 0
        row2_next = (want_bombs and emu.byte(0x52A) in (0, 5, 7) and any(t_[1] in ROW2 for t_ in tlist)
                     and not all(t_[1] in ROW2 for t_ in tlist))
"""
assert t.count(old) == 1
t = t.replace(old, new)

old = """            if streak_bomb and n1 < n0:
"""
new = """            if row2_next and n1 < n0:
                alive = {e[0] for e in ens}
                dead = [t_ for t_ in tlist if t_[0] not in alive]
                if dead:
                    sc += 120 if any(t_[1] in ROW2 for t_ in dead) else -80
            if streak_bomb and n1 < n0:
"""
assert t.count(old) == 1
t = t.replace(old, new)
p.write_text(t, encoding="utf-8")
print("patched plan_fight: kill-cycle nudge for bomb drops")
