"""What does 0x1F look like, and where is the way up to 0x0F (or the hidden stairway itself)?
Reached the way that works: leave 0x2D upward at column 120, then right twice."""
from zelda.emulator import BizHawk
from zelda.overworld import Navigator, NavError, LinkDied, read_cells
from zelda import secrets

emu = BizHawk(log_name="probe_1f.log", clean_sram=False)
nav = Navigator(emu)
emu.load("ckpt_fullgame_l5w03_2d"); emu.wait(4)
s = nav.exit_screen("Up", at=120); s = nav.exit_screen("Right"); s = nav.exit_screen("Right")
print(f"on {s.room:02X} at ({s.x},{s.y}) hearts {s.hearts}", flush=True)
print("opening detector on 0x1F:", secrets.opening(emu), flush=True)
cells = read_cells(emu)
print("tile map (16 wide x 11 tall, top-left cell of each tile):", flush=True)
for r in range(11):
    print(f"  {r:2d} " + " ".join(f"{cells[r*2][c*2]:02X}" for c in range(16)), flush=True)
print("shot:", emu.screenshot("probe_1f_screen"), flush=True)
snap = emu.msave()
for col in (136, 152, 168, 184, 200, 216, 232):
    emu.mload(snap)
    try:
        s = nav.exit_screen("Up", at=col)
        print(f"  Up at x={col}: reached {s.room:02X} at ({s.x},{s.y})", flush=True)
        print("  opening on arrival:", secrets.opening(emu), flush=True)
        print("  shot:", emu.screenshot(f"probe_0f_from_{col}"), flush=True)
        break
    except (NavError, LinkDied) as e:
        print(f"  Up at x={col}: {str(e)[:70]}", flush=True)
emu.mfree(snap)
emu.close()
