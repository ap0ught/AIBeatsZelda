"""Survey the Patra in Level 9 room 0x61 before writing any strategy for it (the standing rule).

First read the live object table to learn which object ids the Patra actually uses - its core and
orbiting eyes may sit outside the 0x30-0x4F range tactics.survey assumed, and a survey that cannot
see its target reports "no damage" for every weapon. Then survey counting exactly those ids. Every
trial runs from an in-memory snapshot, so no rupee, arrow or bomb is really spent."""
from zelda.emulator import BizHawk
from zelda.lookahead import UNKILLABLE
from zelda import tactics

emu = BizHawk(log_name="probe_patra.log", clean_sram=False)
s = emu.load("ckpt_fullgame_s9_61"); s = emu.wait(30)
print("start:", s, "| bombs", s.bombs, "rupees", s.rupees, flush=True)
print("shot:", emu.screenshot("patra_61_start"), flush=True)
ts = emu.ram(0x34F, 12); hp = emu.ram(0x485, 12); xs = emu.ram(0x70, 12); ys = emu.ram(0x84, 12)
for i in range(12):
    if ts[i]:
        print(f"  slot {i:2d}: type {ts[i]:02X} hp {hp[i] >> 4:2d} at ({xs[i]},{ys[i]})", flush=True)
types = {t for t in ts if t and t < 0x50 and t not in UNKILLABLE}
print("counting types:", sorted(f"{t:02X}" for t in types), "| total health", tactics.boss_health(emu, types), flush=True)
results = tactics.survey(emu, log=lambda m: print(m, flush=True), types=types)
print("TOP:", results[:6], flush=True)
emu.close()
