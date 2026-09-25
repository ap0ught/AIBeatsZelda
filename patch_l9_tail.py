"""Two late-game fixes found in the finished third run.

1. plan_reach in a room the tile map cannot read (Ganon's: its floor is drawn in doorway tiles 0x24, which the
   walkability map does not count as floor). The lattice then covers only the door lane, Link's own square is
   not on it, and the mixed lattice/Manhattan shaping went nowhere: g9_32 burned its whole 900-frame budget
   before the last-resort "line up and push" walked out - 1,087 frames against 275 in the second run. If Link's
   start is not on the lattice, shape by straight-line distance as before.
2. Level 9's door: the new navigator reaches the bombing spot on Spectacle Rock in 270-311 frames, the
   damage-aware planner in 424-810 (probe_l9_door.py). Let the search try both: navigator on most attempts,
   planner on the rest and as the fallback."""
import pathlib

p = pathlib.Path("zelda/lookahead.py")
t = p.read_text(encoding="utf-8")
old = """    if not OLD_PLANNER[0] and getattr(goal, "target", None) is not None:
        lattice = Lattice(emu)
        goal_field = lattice.field([goal.target])
"""
new = """    if not OLD_PLANNER[0] and getattr(goal, "target", None) is not None:
        lattice = Lattice(emu)
        goal_field = lattice.field([goal.target])
        if lattice.walk(goal_field, s0.x, s0.y, None) is None:
            lattice = goal_field = None      # a room the tile map cannot read (Ganon's): straight-line shaping
"""
assert t.count(old) == 1
p.write_text(t.replace(old, new), encoding="utf-8")

p = pathlib.Path("fullgame.py")
t = p.read_text(encoding="utf-8")
old = """            from zelda.lookahead import plan_reach
            emu.step = orig
            res = plan_reach(emu, rec, Goal(tx, ty, 6), max_frames=4000, rng=rng)
            emu.step = rec.step
            if res != "arrived":
                return "could not reach the bombing spot: " + str(res)
            dx, dy = doorway
"""
new = """            from zelda.lookahead import plan_reach
            # ...that was the OLD navigator. The new one prices Lynels by what they do and cuts down what
            # stands in the lane, and it gets here in 270-311 frames against the planner's 424-810. The search
            # tries both and keeps whichever came out ahead.
            res = None
            if rng.random() < 0.65:
                try:
                    nav.go(lambda x, y: abs(x - tx) <= 6 and abs(y - ty) <= 6, "the bombing spot",
                           optimistic=True, max_replans=80)
                    res = "arrived"
                except NavError:
                    res = None
            if res is None:
                emu.step = orig
                res = plan_reach(emu, rec, Goal(tx, ty, 6), max_frames=4000, rng=rng)
                emu.step = rec.step
            if res != "arrived":
                return "could not reach the bombing spot: " + str(res)
            dx, dy = doorway
"""
assert t.count(old) == 1
p.write_text(t.replace(old, new), encoding="utf-8")
print("patched plan_reach fallback and the Level 9 door approach")
