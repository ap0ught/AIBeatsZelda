"""Level 8's eight Pols Voices (room 0x4C, exit west to 0x4B). The route fights them with arrows because a
note says they ignore the sword; the disassembly says the sword works on them too (mask $FE). Measure the
sword fighter against the bow fighter from the first run's own state."""
import random

import fullgame as fg
from zelda.emulator import BizHawk
from zelda.overworld import Navigator, read_enemies
from zelda.search import Recorder
from zelda.segments import make_lafight_policy

emu = BizHawk(log_name="probe_l8_pols.log", clean_sram=False)
nav = Navigator(emu)
emu.load("ckpt_fullgame_r8_pass")
emu.step((), 30)
print("enemies:", sorted({f"{e[1]:02X} hp{e[4]:02X}" for e in read_enemies(emu)}), flush=True)
VARIANTS = {"sword": lambda: make_lafight_policy(nav, "Left"), "bow": lambda: fg.bow_fight_policy(nav, "Left")}
for name, make in VARIANTS.items():
    for seed in range(3):
        emu.load("ckpt_fullgame_r8_pass")
        s0 = emu.state()
        rec = Recorder(emu)
        try:
            out = make()(emu, rec, random.Random(seed), 4000)
        except Exception as e:
            out = f"{type(e).__name__}: {str(e)[:40]}"
        s = emu.state()
        ok = s.room == 0x4B and s.mode == 5 and s.hearts > 0
        print(f"{name:5s} seed {seed}: {str(out)[:30]:32s} -> {s.room:02X} {len(rec.inputs):5d} fr  hearts {s0.hearts}->{s.hearts} "
              f"rupees {s0.rupees}->{s.rupees} {'OK' if ok else 'WRONG'}", flush=True)
emu.close()
