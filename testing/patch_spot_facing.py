"""plan_fight's walking-distance field pulled Link toward ALL FOUR sides of every target - including a Darknut's
FRONT, where the shield eats every swing. The old Manhattan shaping left the front spot out (that is what the
per-branch `spots` list does), and the A/B from run 2's states shows it: Darknut rooms are 8-26% slower with the
lattice (l5_rec_st 1,523 -> 1,925). Build the field's sources with the same facing rule. Behind SPOT_FACING
until the A/B agrees."""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import pathlib

p = pathlib.Path("zelda/lookahead.py")
t = p.read_text(encoding="utf-8")
old = """        if lattice is not None and tlist:
            srcs = []
            for e in tlist:
                srcs += [(e[2] - 24, e[3]), (e[2] + 24, e[3]), (e[2], e[3] - 24), (e[2], e[3] + 24)]
            spot_field = lattice.field(srcs)
"""
new = """        if lattice is not None and tlist:
            srcs = []
            for e in tlist:
                f = emu.byte(0x98 + e[0]) if (SPOT_FACING[0] and e[1] in (0x0B, 0x0C)) else 0
                fx, fy = {1: (1, 0), 2: (-1, 0), 4: (0, 1), 8: (0, -1)}.get(f, (0, 0))
                if fx:                        # a Darknut: its sides and its back, never its shield
                    srcs += [(e[2] - fx * 24, e[3]), (e[2], e[3] - 24), (e[2], e[3] + 24)]
                elif fy:
                    srcs += [(e[2], e[3] - fy * 24), (e[2] - 24, e[3]), (e[2] + 24, e[3])]
                else:
                    srcs += [(e[2] - 24, e[3]), (e[2] + 24, e[3]), (e[2], e[3] - 24), (e[2], e[3] + 24)]
            spot_field = lattice.field(srcs)
"""
assert t.count(old) == 1
t = t.replace(old, new)
old2 = "OLD_PLANNER = [False]"
assert t.count(old2) == 1
t = t.replace(old2, "SPOT_FACING = [False]         # True: the strike-spot field leaves out a Darknut's shield side\n" + old2, 1)
p.write_text(t, encoding="utf-8")
print("patched (flag off by default)")
