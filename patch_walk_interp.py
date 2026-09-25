"""Lattice.walk measured distance as 8*steps(nearest lattice point) PLUS the offset to that point. Between two
lattice points that over-counts by up to 8 px, and because snapping rounds half up it does so for LEFTWARD and
UPWARD progress only: a 12 px hold to the left was credited 4 px, the same hold to the right 12. Take the best
of the surrounding lattice points instead (exact in open floor). Behind a flag until the A/B says it helps."""
import pathlib

p = pathlib.Path("zelda/lookahead.py")
t = p.read_text(encoding="utf-8")
old = '''    def walk(self, field: dict, x: int, y: int, fallback: float) -> float:
        """Walking distance in pixels from (x, y) according to `field`, or `fallback` if off the lattice."""
        q = self.snap(x, y)
'''
new = '''    def walk(self, field: dict, x: int, y: int, fallback: float) -> float:
        """Walking distance in pixels from (x, y) according to `field`, or `fallback` if off the lattice."""
        if WALK_INTERP[0]:
            x0, y0 = x // 8 * 8, (y - 5) // 8 * 8 + 5
            best = None
            for qx in (x0, x0 + 8):
                for qy in (y0, y0 + 8):
                    f = field.get((qx, qy))
                    if f is not None:
                        d = 8.0 * f + abs(qx - x) + abs(qy - y)
                        if best is None or d < best:
                            best = d
            if best is not None:
                return best
        q = self.snap(x, y)
'''
assert t.count(old) == 1
t = t.replace(old, new)
old2 = "OLD_PLANNER = [False]"
assert t.count(old2) == 1
t = t.replace(old2, "WALK_INTERP = [False]         # True: interpolate walking distance between lattice points (see Lattice.walk)\n" + old2, 1)
p.write_text(t, encoding="utf-8")
print("patched")
