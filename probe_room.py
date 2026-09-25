"""Print a room as the navigator sees it, from a saved state.

usage: python probe_room.py <state name> [wait frames]
Legend: '.' walkable, '#' solid, '~' water, 'B' block, 'D' locked door, 'S' shutter, '?' unknown tile,
        'L' Link, digits = enemy slots. One character per 8x8 cell (32 x 22)."""
import sys

from zelda.emulator import BizHawk
from zelda.overworld import (Navigator, read_cells, read_enemies, enemy_name, WATER_IDS, OW_WATER_IDS,
                             BLOCK_IDS, LOCKED_DOOR_IDS, SHUTTER_CLOSED_IDS, harm_halfhearts)

emu = BizHawk(log_name="probe_room.log", clean_sram=False)
nav = Navigator(emu)
s = emu.load(sys.argv[1])
if len(sys.argv) > 2:
    s = emu.step((), int(sys.argv[2]))
nav.kb.use(s.level, s.mode)
cells = read_cells(emu)
water = WATER_IDS if s.level else OW_WATER_IDS
grid = []
for r in range(22):
    row = []
    for c in range(32):
        t = cells[r][c]
        ch = ("~" if t in water else "B" if t in BLOCK_IDS else "D" if t in LOCKED_DOOR_IDS else
              "S" if t in SHUTTER_CLOSED_IDS else "." if t in nav.kb.walkable else
              "#" if t in nav.kb.solid else "?")
        row.append(ch)
    grid.append(row)
ens = read_enemies(emu)
st = emu.ram(0xAC, 12)
for e in ens:
    r, c = (e[3] - 61) // 8, e[2] // 8
    if 0 <= r < 22 and 0 <= c < 32:
        grid[r][c] = str(e[0] % 10)
r, c = (s.y - 61) // 8, s.x // 8
if 0 <= r < 22 and 0 <= c < 32:
    grid[r][c] = "L"
print(f"{sys.argv[1]}: level {s.level} room {s.room:02X} Link ({s.x},{s.y}) hearts {s.hearts} keys {s.keys} bombs {s.bombs} "
      f"ladder {emu.byte(0x663)}")
print("    " + "".join(f"{c % 10}" for c in range(32)))
for r in range(22):
    print(f"{61 + r * 8:3d} " + "".join(grid[r]))
for e in ens:
    print(f"  slot {e[0]}: type {e[1]:02X} {enemy_name(e[1])} at ({e[2]},{e[3]}) hp {e[4]:02X} state {st[e[0]]:02X} harm {harm_halfhearts(e[1])}")
unknown = sorted({cells[r][c] for r in range(22) for c in range(32)
                  if cells[r][c] not in nav.kb.walkable and cells[r][c] not in nav.kb.solid})
print("  unknown tile ids:", [f"{t:02X}" for t in unknown])
emu.close()
