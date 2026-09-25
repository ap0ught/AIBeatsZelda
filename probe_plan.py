import sys
from zelda.emulator import BizHawk
from zelda.overworld import (Navigator, read_cells, plan, DOOR_GOALS, EDGE_GOALS, water_bridges, WATER_IDS,
                             OW_WATER_IDS, DIRS, legal, box_cells)
emu = BizHawk(log_name="probe_plan.log", clean_sram=False); nav = Navigator(emu)
s = emu.load(sys.argv[1]); d = sys.argv[2]
s = emu.step("Right", 16) if s.x <= 16 else s
nav.kb.use(s.level, s.mode)
cells = read_cells(emu)
ok = water_bridges(cells, WATER_IDS if s.level else OW_WATER_IDS) if emu.byte(0x663) else None
print("ladder", emu.byte(0x663), "start", (s.x, s.y), "horz cells row10:", sorted(c for c in (ok[1] if ok else []) if c[0] == 10))
goal = (DOOR_GOALS if s.level else EDGE_GOALS)[d]
for label, en in (("no enemies", ()), ("threats", nav.threats())):
    path = plan(cells, nav.kb, (s.x, s.y), goal, True, None, en, None, cells_ok=ok)
    pos = (s.x // 8 * 8, s.y); pts = [pos]
    for st in path or []:
        pos = (pos[0] + DIRS[st][0], pos[1] + DIRS[st][1]); pts.append(pos)
    print(label, len(path or []), "steps:", " ".join(f"{x},{y}" for x, y in pts[::2]))
x, y = 56, 141
for nx in (64, 72, 80):
    print("legal", (nx, y), legal(cells, nav.kb, nx, y, True, None, ok[1] if ok else None), [f"{cells[cy][cx]:02X}" for cy, cx in box_cells(nx, y)])
for pt in ((88,109),(96,109),(104,109),(112,109),(128,109),(152,109),(160,109)):
    print("legal", pt, legal(cells, nav.kb, pt[0], pt[1], True, None, ok[1]), [f"{cells[cy][cx]:02X}" for cy, cx in box_cells(*pt)], [(cy,cx) in ok[1] for cy,cx in box_cells(*pt)])
print("row 6 tiles:", " ".join(f"{cells[6][c]:02X}" for c in range(32)))
print("row 7 tiles:", " ".join(f"{cells[7][c]:02X}" for c in range(32)))
emu.close()
