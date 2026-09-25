"""Two navigator fixes from the Magical Sword trip (overworld 0x32, the one-tile staircase with Lynels at its foot):

1. A step that fails because Link was HIT (knocked back) or because a monster is standing on the target is not
   a wall. The navigator recorded it as "this move is impossible", and on a one-tile staircase that removes the
   only path: 58 of 60 attempts ended "no path to the Left edge".
2. Lynels were excluded from "cut down what stands directly in the way" (they are in NEVER_CHASE - rightly, they
   are not worth hunting). In a corridor there is no way round one, and walking into it costs two hearts a touch:
   swing at it like anything else that blocks the lane."""
import pathlib

p = pathlib.Path("zelda/overworld.py")
t = p.read_text(encoding="utf-8")

old1 = """                r = self._unlock(d, pos, target, cells) if door else self._step_to(d, target)
                if r is None:
                    s = emu.state()
                    self._learn_block(cells, pos, d, target, key)
                    break
"""
new1 = """                r = self._unlock(d, pos, target, cells) if door else self._step_to(d, target)
                if r is None:
                    s = emu.state()
                    # knocked back by a hit, or a monster standing where the step ends: that is not scenery
                    crowd = any(max(abs(e[2] - target[0]), abs(e[3] - target[1])) < 20 for e in self.threats())
                    if s.hearts < hearts0 or crowd:
                        if s.hearts < hearts0:
                            emu.note(f"Knocked back going {d} at {pos} ({s.hearts} hearts left): not a wall, carrying on")
                            hearts0 = s.hearts
                        break
                    self._learn_block(cells, pos, d, target, key)
                    break
"""
assert t.count(old1) == 1
t = t.replace(old1, new1)

old2 = """            if t >= 0x40 or t in NEVER_CHASE or t in (0x0B, 0x0C):
                continue                      # bosses/flames, the unkillable, and Darknuts' shields
"""
new2 = """            if t >= 0x40 or (t in NEVER_CHASE and t not in (0x01, 0x02)) or t in (0x0B, 0x0C):
                continue                      # bosses/flames, the unkillable, and Darknuts' shields
                # (Lynels are never CHASED, but one standing in the lane is cut down like anything else)
"""
assert t.count(old2) == 1
t = t.replace(old2, new2)
p.write_text(t, encoding="utf-8")
print("patched navigator: knockback is not a wall; Lynels in the lane get the sword")
