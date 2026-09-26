"""Why can't Link walk down off the pier on lake screen 0x55? Dump the cells around him and the tile
KB's verdict on each id, try the Down plan with pieces removed, then try the detour the run has used
before: east to 0x56, back in from the east edge, then down."""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
from zelda.emulator import BizHawk
from zelda.overworld import Navigator, read_cells, plan, EDGE_GOALS, read_enemies, entrance_spots

emu = BizHawk(log_name="probe_pier.log", clean_sram=False)
nav = Navigator(emu)
s = emu.load("ckpt_fullgame_rb_land"); s = emu.wait(4)
print("start:", s, flush=True)
print("shot:", emu.screenshot("pier_55_start"), flush=True)
cells = read_cells(emu)
kb = nav.kb
kb.use(0, 5)
walk = kb.walkable() if callable(kb.walkable) else kb.walkable
solid = kb.solid() if callable(kb.solid) else kb.solid
print(f"cells rows 4..21, cols 8..27 (Link x={s.x} y={s.y}; his box is cols {s.x//8}..{(s.x+15)//8}, "
      f"rows {(s.y+3-64)//8}..{(s.y+18-64)//8}):", flush=True)
print("      " + " ".join(f"{c:2d}" for c in range(8, 28)), flush=True)
for r in range(4, 22):
    print(f"  {r:2d}  " + " ".join(f"{cells[r][c]:02X}" for c in range(8, 28)), flush=True)
ids = sorted({cells[r][c] for r in range(4, 22) for c in range(8, 28)})
print("KB verdicts:", {f"{i:02X}": ("walk" if i in walk else "SOLID" if i in solid else "unknown") for i in ids}, flush=True)
enemies = read_enemies(emu)
print("enemies:", [(hex(e[1]), e[2], e[3]) for e in enemies], flush=True)
print("entrance spots (the planner forbids squares near these):", entrance_spots(cells), flush=True)
for label, kw in (("optimistic, no enemies", dict(optimistic=True)),
                  ("optimistic, with enemies", dict(optimistic=True, enemies=enemies)),
                  ("strict", dict(optimistic=False))):
    p = plan(cells, kb, (s.x, s.y), EDGE_GOALS["Down"], **kw)
    print(f"plan Down [{label}]:", None if p is None else f"{len(p)} steps, first {p[:6]}", flush=True)
for d in ("Right", "Left", "Up"):
    p = plan(cells, kb, (s.x, s.y), EDGE_GOALS[d], optimistic=True)
    print(f"plan {d}:", None if p is None else f"{len(p)} steps, first {p[:6]}", flush=True)
root = emu.msave()
for route in (["Down"], ["Right", "Left", "Down"]):
    emu.mload(root); emu.wait(2)
    trail = []
    try:
        for d in route:
            q = nav.exit_screen(d)
            trail.append(f"{d}->{q.room:02X}@({q.x},{q.y})")
    except Exception as e:
        trail.append(f"FAILED {type(e).__name__}: {str(e)[:80]}")
    print("route", route, ":", " | ".join(trail), "| end", emu.state(), flush=True)
    if emu.state().room == 0x65:
        print("  shot:", emu.screenshot("pier_route_ok"), flush=True)
emu.mfree(root)
emu.close()
