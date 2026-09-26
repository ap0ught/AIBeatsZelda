"""Which RAM byte says Link has the Triforce of Power? Walk into it and diff the whole 2KB of RAM.
The probe that checked $0672 (Items+$1B, by the disassembly's own table) saw the item vanish with
that byte still 0, so measure instead of trusting the address."""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
from zelda.emulator import BizHawk
from zelda.overworld import read_room_item

emu = BizHawk(log_name="probe_takepower.log", clean_sram=False)
s = emu.load("ckpt_fullgame_g9_ganon"); s = emu.wait(2)
before = bytes(emu.ram(0x000, 0x800))
print("start:", s, "| item", read_room_item(emu), flush=True)
for _ in range(600):
    it = read_room_item(emu)
    if it is None:
        break
    _, ix, iy = it
    q = emu.state()
    dx, dy = ix - q.x, iy - q.y
    if abs(dx) <= 2 and abs(dy) <= 2:
        emu.step((), 1)
        continue
    emu.step(("Right" if dx > 0 else "Left") if abs(dx) >= abs(dy) else ("Down" if dy > 0 else "Up"), 1)
print("item gone at", emu.state(), flush=True)
emu.step((), 180)
after = bytes(emu.ram(0x000, 0x800))
diff = [(a, before[a], after[a]) for a in range(0x800) if before[a] != after[a]]
print(f"{len(diff)} bytes changed", flush=True)
print("  zero page:", " ".join(f"${a:02X} {b:02X}->{c:02X}" for a, b, c in diff if a < 0x100), flush=True)
print("  $400-$5FF:", " ".join(f"${a:03X} {b:02X}->{c:02X}" for a, b, c in diff if 0x400 <= a < 0x600), flush=True)
print("  $600-$6FF:", " ".join(f"${a:03X} {b:02X}->{c:02X}" for a, b, c in diff if 0x600 <= a < 0x700), flush=True)
print("  $700+:", " ".join(f"${a:03X} {b:02X}->{c:02X}" for a, b, c in diff if a >= 0x700), flush=True)
print("mode", f"{emu.byte(0x12):02X}", "| state:", emu.state(), flush=True)
print("shot:", emu.screenshot("takepower_after"), flush=True)
emu.close()
