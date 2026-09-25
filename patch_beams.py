"""Sword beams. At full hearts every swing throws the sword across the room for the sword's full damage - the
reason human runners guard their health. plan_fight could not see it: a swing's rollout is 14 frames and the beam
needs up to 60 to cross the room, so a beam kill at range scored as "a swing that hit nothing" (-400) and the
planner walked up to everything instead.

With BEAMS on and Link at full health: swings are rolled out long enough for the beam to land (48 frames), they
are offered even when the nearest target is far (the "just walk closer" mode), and a lost half heart is priced
at full rate rather than the healthy discount - because the first hit also takes the beam away."""
import pathlib

p = pathlib.Path("zelda/lookahead.py")
t = p.read_text(encoding="utf-8")

old = "OLD_PLANNER = [False]"
new = "BEAMS = [True]                # full hearts: roll swings out far enough to see the sword beam land\n" + old
assert t.count(old) == 1
t = t.replace(old, new, 1)

old = """        if far:
            macros = [("hold", d, 8) for d in DIRS4]
            this_rollout = 8
"""
new = """        beam = BEAMS[0] and not OLD_PLANNER[0] and s0.hearts >= s0.containers and s0.sword >= 1
        if far:
            macros = [("hold", d, 8) for d in DIRS4]
            this_rollout = 8
            if beam and tlist:
                # a target in line, however far: the beam reaches it
                for t_ in tlist:
                    dx, dy = t_[2] - s0.x, t_[3] - s0.y
                    if abs(dy) <= 10 and abs(dx) > 16:
                        macros.append(("swing", "Right" if dx > 0 else "Left", 0))
                    if abs(dx) <= 10 and abs(dy) > 16:
                        macros.append(("swing", "Down" if dy > 0 else "Up", 0))
                macros = list(dict.fromkeys(macros))
"""
assert t.count(old) == 1
t = t.replace(old, new)

old = """            s2 = emu.step((), FUSE if m[0] == "bomb" else ARROW if (m[0] == "shoot" and lattice is not None)
                          else this_rollout)
"""
new = """            s2 = emu.step((), FUSE if m[0] == "bomb" else ARROW if (m[0] == "shoot" and lattice is not None)
                          else BEAM_ROLL if (m[0] == "swing" and beam) else this_rollout)
"""
assert t.count(old) == 1
t = t.replace(old, new)

old = """    FUSE = 86            # a bomb's blast lands well after a normal rollout, so give it its own
"""
new = """    FUSE = 86            # a bomb's blast lands well after a normal rollout, so give it its own
    BEAM_ROLL = 48       # ...and the sword beam crosses the room at ~3 px a frame
"""
assert t.count(old) == 1
t = t.replace(old, new)

old = """        dmg_w = damage_weight * caution(s0)
        if want_bombs and 5 <= help_n < 10:
"""
new = """        dmg_w = damage_weight * caution(s0)
        if beam:
            dmg_w = max(dmg_w, damage_weight)     # the first hit costs the beam as well as the half heart
        if want_bombs and 5 <= help_n < 10:
"""
assert t.count(old) == 1
t = t.replace(old, new)
p.write_text(t, encoding="utf-8")
print("patched plan_fight: sword beams")
