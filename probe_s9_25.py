"""Validate bow_clear_grab_policy on Level 9 room 0x25 exactly as the run will use it: random_search
from the s9_25 checkpoint; success = Link alive in 0x25 with the bomb pile taken (bombs >= 4).
The sword-only policy timed out on all fifty attempts here."""
import fullgame
from zelda.emulator import BizHawk
from zelda.overworld import Navigator
from zelda.search import random_search

emu = BizHawk(log_name="probe_s9_25.log", clean_sram=False)
nav = Navigator(emu)
best = random_search(emu, "ckpt_fullgame_s9_25", fullgame.bow_clear_grab_policy(nav),
                     lambda e, s: s.hearts > 0 and s.room == 0x25 and s.bombs >= 4,
                     tries=8, max_frames=3000, label="probe s9_25 bombs", log=print, prefer_hearts=True)
print("BEST:", None if best is None else (best.frames, best.hearts), flush=True)
emu.close()
