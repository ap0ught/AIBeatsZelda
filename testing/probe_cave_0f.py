"""B1: is there a walk-in cave on overworld screen 0x0F, and does it pay 100 rupees?
The whole sub-hour plan rests on this: it would replace ~59,000 frames of rupee farming.
The ROM's overworld secret table marks 0x0F as 0x03 - the same value as screens whose entrance is
already drawn - but knowledge/rooms.json has never seen that corner of the map, so walk it and look.
Route: from 0x1C (where the Level 2 -> hills chain lands) Up to 0x0C, then east 0x0D, 0x0E, 0x0F."""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
from zelda.emulator import BizHawk
from zelda.overworld import Navigator, NavError, LinkDied, read_cells
from zelda import secrets

emu = BizHawk(log_name="probe_cave0f.log", clean_sram=False)
nav = Navigator(emu)
s = emu.load("ckpt_fullgame_l5w05_1c"); s = emu.wait(4)
print("start:", s, "| rupees", emu.byte(0x66D), flush=True)
for d in ("Up", "Right", "Right", "Right"):
    try:
        s = nav.exit_screen(d)
        print(f"  {d:5s} -> screen {s.room:02X}  ({s.x},{s.y}) hearts {s.hearts}", flush=True)
    except (NavError, LinkDied) as e:
        print(f"  {d:5s} BLOCKED: {str(e)[:90]}", flush=True)
        break
print("final screen:", f"{s.room:02X}", flush=True)
spot = secrets.opening(emu)
print("opening detector says:", spot, flush=True)
cells = read_cells(emu)
for r16 in range(11):
    print("   " + " ".join(f"{cells[r16*2][c16*2]:02X}" for c16 in range(16)), flush=True)
print("shot:", emu.screenshot(f"cave0f_screen_{s.room:02x}"), flush=True)
emu.close()
