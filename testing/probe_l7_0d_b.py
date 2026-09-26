"""Level 7 room 0D: what is left standing after the fight, and what does the game's cleared flag say?"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import random
from zelda.emulator import BizHawk
from zelda.overworld import Navigator, read_enemies
from zelda.lookahead import plan_fight, killable
from zelda.search import Recorder

emu = BizHawk(log_name="probe_l7_0d.log", clean_sram=False)
nav = Navigator(emu)
emu.load("ckpt_fullgame_l7_0d")
rec = Recorder(emu)
rec.step((), 2)
print("at start:", [(e[0], hex(e[1]), e[2], e[3], hex(e[4])) for e in read_enemies(emu)], "cleared", emu.byte(0x34D))
for chunk in range(6):
    res = plan_fight(emu, rec, max_frames=400, rng=random.Random(1))
    es = read_enemies(emu)
    st = emu.ram(0xAC, 12)
    print(chunk, res, "frames", len(rec.inputs), "cleared flag", emu.byte(0x34D),
          [(e[0], hex(e[1]), e[2], e[3], hex(e[4]), "K" if killable(e) else "-", st[e[0]]) for e in es])
    if res == "clear":
        break
emu.close()
