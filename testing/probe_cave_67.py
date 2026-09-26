"""What does screen 0x67's cave pay?

The sweep opens it with a bomb from (112,93) facing Up. Two probes have now confirmed the cave is
real and enterable - Link walked in - but neither measured the money: the first tried to burn a
bomb secret, and the second used the heart-container policy, whose success test is "containers went
up", so it reported failure on a cave full of rupees.

So: bomb the wall, then hand over to burn_cave_policy, which skips its candle step when the entrance
is already open and just walks in, takes what is there, and leaves. Read $066D on the way out.
"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import random

import fullgame
from zelda.emulator import BizHawk
from zelda.overworld import Navigator, NavError, LinkDied
from zelda.search import Recorder
from zelda import bot, secrets

CKPT, SCREEN, STAND, FACE = "ckpt_fullgame_w8_67", 0x67, (112, 93), "Up"

emu = BizHawk(log_name="probe_cave67.log", clean_sram=False)
nav = Navigator(emu)
s = emu.load(CKPT); s = emu.wait(4)
print("start:", s, "| rupees", emu.byte(0x66D), "bombs", s.bombs, flush=True)
rec = Recorder(emu)
orig = emu.step
try:
    emu.step = rec.step
    nav.go(lambda x, y: (x, y) == STAND, "the bombing spot", max_replans=40)
    rec.step(FACE, 2)
    if not bot.select_b_item(emu, rec.step, bot.B_BOMBS):
        print("could not select bombs", flush=True)
    else:
        rec.step("B", 2)
        for _ in range(90):
            rec.step((), 1)
        spot = secrets.opening(emu)
        print("after the bomb, opening detector says:", spot, flush=True)
        emu.step = orig
        before = emu.byte(0x66D)
        out = fullgame.burn_cave_policy(nav, STAND, FACE, want_rupees=True)(emu, rec, random.Random(5), 4000)
        after = emu.byte(0x66D)
        print(f"policy said: {out}", flush=True)
        print(f"rupees {before} -> {after}  (+{after - before}) after {len(rec.inputs)} frames total", flush=True)
        print("state:", emu.state(), flush=True)
        print("shot:", emu.screenshot("cave67_paid"), flush=True)
except (NavError, LinkDied) as e:
    print(f"FAILED: {type(e).__name__}: {str(e)[:120]}", flush=True)
finally:
    emu.step = orig
emu.close()
