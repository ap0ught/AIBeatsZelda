"""Screen 0x67's secret is opened with a BOMB, not the candle - the first payout probe tried to burn
it and reported "nothing burned". Open it properly and see what the old man pays.

Also re-checks 0x28 (already confirmed: +30 rupees in 1,150 frames) as a control, so a zero here
means the cave is poor rather than the probe being wrong.
"""
import random

import fullgame
from zelda.emulator import BizHawk
from zelda.overworld import Navigator, NavError, LinkDied
from zelda.search import Recorder

# (checkpoint, screen, method, stand, face)
CAVES = [
    ("ckpt_fullgame_w8_67", 0x67, "bomb", (112, 93), "Up"),
    ("ckpt_fullgame_h9_28", 0x28, "burn", (208, 141), "Down"),
]

emu = BizHawk(log_name="probe_cave_pay2.log", clean_sram=False)
nav = Navigator(emu)
for ckpt, screen, method, stand, face in CAVES:
    try:
        s = emu.load(ckpt); s = emu.wait(4)
    except Exception as e:
        print(f"== {screen:02X}: cannot load {ckpt}: {str(e)[:70]}", flush=True)
        continue
    if s.room != screen or s.level:
        print(f"== {screen:02X}: {ckpt} stands on {s.room:02X} L{s.level}; skipping", flush=True)
        continue
    before, bombs = emu.byte(0x66D), s.bombs
    print(f"\n== SCREEN {screen:02X}: {method} from {stand} facing {face}; "
          f"rupees {before}, bombs {bombs}", flush=True)
    snap = emu.msave()
    try:
        # hc_cave_policy knows both methods: walk to the spot, bomb or burn it, find the opening,
        # walk in and take what is inside. Its own success test counts heart containers; here we
        # just read the rupee counter afterwards.
        pol = fullgame.hc_cave_policy(nav, stand, face, method)
        rec = Recorder(emu)
        out = pol(emu, rec, random.Random(3), 4000)
        after = emu.byte(0x66D)
        print(f"   policy said: {out}", flush=True)
        print(f"   rupees {before} -> {after} (+{after - before}) in {len(rec.inputs)} frames", flush=True)
        print(f"   state: {emu.state()}", flush=True)
        print("   shot:", emu.screenshot(f"cave_pay2_{screen:02x}"), flush=True)
    except (NavError, LinkDied) as e:
        print(f"   FAILED: {type(e).__name__}: {str(e)[:110]}", flush=True)
    except Exception as e:
        print(f"   ERROR: {type(e).__name__}: {str(e)[:110]}", flush=True)
    finally:
        emu.mload(snap)
        emu.mfree(snap)
emu.close()
