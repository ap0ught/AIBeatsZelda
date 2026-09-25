"""What do the secret caves actually pay?

The community map says 0x62 holds 100 rupees; sweeping all 92 reachable spots there found nothing at
all, which is the fourth time that map has been wrong. So trust nothing: open each cave the sweep
DID find, walk in, and read the rupee counter before and after.

The route needs roughly 240 rupees (arrows 80, monster bait 60, bomb capacity upgrade 100) and
farming them cost ~59,000 frames last time. This decides whether caves can replace that.

usage: python probe_cave_pay.py
"""
from zelda.emulator import BizHawk
from zelda.overworld import Navigator, NavError, LinkDied
from zelda import secrets
import fullgame

# (checkpoint, screen, how the sweep opened it, where to stand, which way to face)
CAVES = [
    ("ckpt_fullgame_w8_67", 0x67, "bomb", (112, 93), "Up"),
    ("ckpt_fullgame_h9_28", 0x28, "burn", (208, 141), "Down"),
]

emu = BizHawk(log_name="probe_cave_pay.log", clean_sram=False)
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
    before = emu.byte(0x66D)
    print(f"\n== SCREEN {screen:02X}: {method} from {stand} facing {face}; rupees before = {before}", flush=True)
    snap = emu.msave()
    try:
        pol = fullgame.burn_cave_policy(nav, stand, face, want_rupees=True)
        from zelda.search import Recorder
        import random
        rec = Recorder(emu)
        out = pol(emu, rec, random.Random(1), 4000)
        s2 = emu.state()
        after = emu.byte(0x66D)
        print(f"   policy said: {out}", flush=True)
        print(f"   rupees {before} -> {after}  (+{after - before}) in {len(rec.inputs)} frames; {s2}", flush=True)
        print("   shot:", emu.screenshot(f"cave_pay_{screen:02x}"), flush=True)
    except (NavError, LinkDied, Exception) as e:
        print(f"   FAILED: {type(e).__name__}: {str(e)[:110]}", flush=True)
    finally:
        emu.mload(snap)
        emu.mfree(snap)
emu.close()
