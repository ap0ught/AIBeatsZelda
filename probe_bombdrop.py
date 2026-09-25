"""Validate bomb_drop_policy exactly as the run would use it: random_search from the checkpoint where
the passage from 0x30 surfaces in Level 9's room 0x04, Link with no bombs."""
import fullgame
from zelda.emulator import BizHawk
from zelda.overworld import Navigator
from zelda.search import random_search

emu = BizHawk(log_name="probe_bombdrop.log", clean_sram=False)
nav = Navigator(emu)
best = random_search(emu, "ckpt_fullgame_g9_pass_30", fullgame.bomb_drop_policy(nav),
                     lambda e, s: s.hearts > 0 and s.room == 0x04 and s.bombs >= 1,
                     tries=16, max_frames=4000, label="probe bomb drop", log=print, prefer_hearts=True, patience=4)
print("BEST:", None if best is None else (best.frames, best.hearts), flush=True)
emu.close()
