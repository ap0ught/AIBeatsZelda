"""walk_out_policy (Ganon's room -> Zelda): try the straight walk FIRST.

The planner's holds are 8 frames = 12 px, and from x=112 that cycles 124 -> 128 -> 116 -> 112: never the door's
column (120). It reached the wall under the door in 96 frames and then dithered there until its 900-frame budget
ran out; the last-resort "line up on the door and push" then walked out. 1,087 frames for a 100-frame walk in an
empty room. Now the straight line-up is tried on a scratch copy of the state; if it arrives unhurt it is played
for real, and the planner is only for a room where something is in the way."""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import pathlib

p = pathlib.Path("fullgame.py")
t = p.read_text(encoding="utf-8")
old = """            tx, ty = spot or SPOTS[direction]
            room0 = emu.state().room
            res = plan_reach(emu, rec, Goal(tx, ty, 6), max_frames=budget, rng=rng)
            emu.step = rec.step
"""
new = """            tx, ty = spot or SPOTS[direction]
            room0 = emu.state().room

            def line_up(step):
                st = emu.state()
                stall, last = 0, None
                for _ in range(240):
                    if abs(st.x - tx) <= 2 and abs(st.y - ty) <= 2:
                        return True
                    st = step(("Right" if st.x < tx else "Left") if abs(st.x - tx) > 2
                              else ("Down" if st.y < ty else "Up"), 1)
                    stall = stall + 1 if (st.x, st.y) == last else 0
                    last = (st.x, st.y)
                    if stall >= 8 or st.room != room0 or st.mode != 5:
                        return False
                return False

            h0 = emu.state().hearts
            root = emu.msave()
            straight = line_up(emu.step) and emu.state().hearts >= h0          # scratch copy: not recorded
            emu.mload(root)
            emu.mfree(root)
            if straight:
                line_up(rec.step)
                res = "arrived"
            else:
                res = plan_reach(emu, rec, Goal(tx, ty, 6), max_frames=budget, rng=rng)
            emu.step = rec.step
"""
assert t.count(old) == 1
p.write_text(t.replace(old, new), encoding="utf-8")
print("patched walk_out_policy")
