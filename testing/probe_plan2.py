import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
from zelda.emulator import BizHawk
from zelda.overworld import (Navigator, read_cells, plan, DOOR_GOALS, water_bridges, WATER_IDS, DIRS, legal, box_cells, LADDER_FLAG)
emu = BizHawk(log_name="probe_plan2.log", clean_sram=False); nav = Navigator(emu)
s = emu.load("ckpt_fullgame_l5_c57"); emu.step((), 2)
for d, n in (("Right", 24), ("Up", 22), ("Right", 22)):
    s = emu.step(d, n)
print("Link at", (s.x, s.y), "ladder flag", emu.byte(LADDER_FLAG))
nav.kb.use(s.level, s.mode)
cells = read_cells(emu)
ok = water_bridges(cells, WATER_IDS)
print("horz row6:", sorted(c for c in ok[1] if c[0] in (6, 7)))
print("vert row6:", sorted(c for c in ok[0] if c[0] in (6, 7)))
goal = DOOR_GOALS["Up"]
for label, en in (("no enemies", ()), ("threats", nav.threats())):
    for start in ((64, 109), (72, 109), (80, 109)):
        path = plan(cells, nav.kb, start, goal, True, None, en, None, cells_ok=ok)
        print(label, start, len(path or []), (path or [])[:12])
for x in (88, 96, 104, 112):
    print("legal", (x, 109), legal(cells, nav.kb, x, 109, True, None, ok[1]), [f"{cells[cy][cx]:02X}" for cy, cx in box_cells(x, 109)])
emu.close()
