"""The guide's second 100-rupee tree: 0x62, "third tree from the top". The first sweep of 0x62 burned only
the eastern lane (the one the Level 8 walk uses) and found nothing, so drop into the WESTERN pocket from
0x52 at x=80 - one screen south of Level 7's pond, where the Triforce warp lands - and sweep that half."""
import random

from zelda.emulator import BizHawk
from zelda.overworld import Navigator
from zelda.search import Recorder
from zelda.segments import make_cross_at_policy
from zelda import secrets

emu = BizHawk(log_name="probe_cave_62.log", clean_sram=False)
nav = Navigator(emu)
emu.load("ckpt_fullgame_w8_52")
s = emu.state()
print(f"start {s.room:02X} ({s.x},{s.y}) rupees {s.rupees} bitem {s.bitem}", flush=True)
rec = Recorder(emu)
out = make_cross_at_policy(nav, "Down", at=80)(emu, rec, random.Random(3), 3000)
s = emu.state()
print(f"cross: {out} -> {s.room:02X} ({s.x},{s.y}) {len(rec.inputs)} fr", flush=True)
print("shot:", emu.screenshot("cave62_west_pocket"), flush=True)
emu.save("probe_62_west")
res = secrets.sweep(emu, nav, methods=("burn",))
s = emu.state()
print("sweep:", res, f"-> {s.room:02X} ({s.x},{s.y}) rupees {s.rupees}", flush=True)
print("shot:", emu.screenshot("cave62_after_sweep"), flush=True)
emu.close()
