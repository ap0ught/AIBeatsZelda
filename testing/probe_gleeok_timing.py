"""When did the Gleeok fight actually end, and when did the policy stop?
The end-state probe showed $034D=0x66 and gleeok_dead()=True, so the death predicate DOES latch -
the audit's stuck-predicate theory is wrong. So replay the segment's own recorded inputs and watch
for the frame the room clears, the frame the last input is pressed, and what the fight did after."""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import json, pathlib
from zelda.emulator import BizHawk, LOGS_DIR
from zelda.overworld import read_enemies
from zelda import boss

def inputs_of(name):
    d = json.loads((LOGS_DIR / "checkpoints" / f"fullgame_{name}.json").read_text())
    return [tuple(b for b in l.split(",") if b) for l in d["inputs"]], d["frames"]

pre, pre_n = inputs_of("l4_13")
post, post_n = inputs_of("gleeok")
seg = post[pre_n:]
print(f"gleeok segment = {len(seg)} recorded frames (log said 6020)", flush=True)
last_input = max((i for i, b in enumerate(seg) if b), default=-1)
print(f"last frame with any button held: {last_input} ({len(seg)-1-last_input} idle frames after it)", flush=True)

emu = BizHawk(log_name="probe_gleeok_timing.log", clean_sram=False)
# Load the state the segment itself started from, and DO NOT settle first. The previous attempt at
# this probe called emu.wait(2) before replaying, which advanced two frames with no buttons held and
# desynced every input after it - Link died in the replay and the measurement was worthless.
emu.load("fullgame_gleeok_start")
cleared_at = dead_at = empty_at = None
for i, b in enumerate(seg):
    emu.step(b, 1)
    if cleared_at is None and emu.byte(0x34D):
        cleared_at = i
    if dead_at is None and boss.gleeok_dead(emu):
        dead_at = i
    if empty_at is None and not read_enemies(emu):
        empty_at = i
    if i % 1000 == 0:
        print(f"   f+{i:5d} $034D={emu.byte(0x34D):02X} enemies={len(read_enemies(emu))} "
              f"dead={boss.gleeok_dead(emu)} hearts={emu.state().hearts}", flush=True)
print(f"\nroom-cleared flag set at frame {cleared_at}", flush=True)
print(f"gleeok_dead() first True at frame {dead_at}", flush=True)
print(f"read_enemies() first empty at frame {empty_at}", flush=True)
print(f"segment ran to {len(seg)} -> wasted {len(seg) - (dead_at or 0)} frames after the boss died", flush=True)
print("final:", emu.state(), flush=True)
emu.close()
