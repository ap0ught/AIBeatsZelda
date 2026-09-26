"""plan_reach: a pixel-precise FINAL APPROACH.

The planner moves in 8-frame holds (12 px). Near a goal with a tolerance of a few pixels that can cycle for
ever without landing - Ganon's room (800 frames at the wall under the door), and the White Sword cave's mouth
(60 of 60 attempts timed out at 5,000 frames in the fourth run). When Link is within 28 px of the goal, try
single-frame steps toward it on a scratch copy of the state (x first, then y, then the other order); if one
arrives without taking damage, play it for real. Tried at most once every third decision."""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import pathlib

p = pathlib.Path("zelda/lookahead.py")
t = p.read_text(encoding="utf-8")
old = """        if goal(s0.x, s0.y):
            return "arrived"
        # a swing is only worth considering with something killable in reach; offered always, it is
"""
new = """        if goal(s0.x, s0.y):
            return "arrived"
        tgt = getattr(goal, "target", None)
        if tgt is not None and not OLD_PLANNER[0]:
            tries_fa += 1
            if abs(s0.x - tgt[0]) + abs(s0.y - tgt[1]) <= 28 and tries_fa % 3 == 1:
                done = False
                for x_first in (True, False):
                    seq = []
                    root = emu.msave()
                    st = s0
                    stall, last = 0, None
                    for _ in range(48):
                        if goal(st.x, st.y):
                            break
                        dx, dy = tgt[0] - st.x, tgt[1] - st.y
                        if x_first:
                            d = ("Right" if dx > 0 else "Left") if dx else ("Down" if dy > 0 else "Up")
                        else:
                            d = ("Down" if dy > 0 else "Up") if dy else ("Right" if dx > 0 else "Left")
                        st = emu.step(d, 1)
                        seq.append(d)
                        stall = stall + 1 if (st.x, st.y) == last else 0
                        last = (st.x, st.y)
                        if stall >= 6 or st.mode not in (5, 9) or st.room != room0:
                            break
                    ok = goal(st.x, st.y) and st.hearts >= s0.hearts and st.mode in (5, 9) and st.room == room0
                    emu.mload(root)
                    emu.mfree(root)
                    if ok:
                        for d in seq:
                            rec.step(d, 1)
                        done = True
                        break
                if done:
                    return "arrived"
        # a swing is only worth considering with something killable in reach; offered always, it is
"""
assert t.count(old) == 1
t = t.replace(old, new)
old2 = """    last_dir = None
    lattice = goal_field = None
    if not OLD_PLANNER[0] and getattr(goal, "target", None) is not None:"""
new2 = """    last_dir = None
    tries_fa = 0
    lattice = goal_field = None
    if not OLD_PLANNER[0] and getattr(goal, "target", None) is not None:"""
assert t.count(old2) == 1
t = t.replace(old2, new2)
p.write_text(t, encoding="utf-8")
print("patched plan_reach: final approach")
