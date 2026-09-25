"""How long is a monster untouchable after a sword hit? Replays run 4's own six-Darknut fight and prints the
invincibility timers ($4F0+slot) around every hit."""
import json, pathlib, sys
from zelda import replay
from zelda.emulator import BizHawk
ARCH = pathlib.Path("logs/archive/fourth_run_20260919")
INPUTS = replay.load_inputs(ARCH / "fullgame.inputs.txt")
seg, prev = sys.argv[1], sys.argv[2]
a = json.load(open(ARCH / f"checkpoints/fullgame_{prev}.json"))["frames"]
b = json.load(open(ARCH / f"checkpoints/fullgame_{seg}.json"))["frames"]
emu = BizHawk(log_name="probe_iframes.log", clean_sram=False)
emu.load(f"run4/ckpt_fullgame_{prev}")
last_hp = None
hits = []
timers = []
for k in range(a, b):
    emu.step(INPUTS[k], 1)
    hp = [v >> 4 for v in emu.ram(0x485, 12)]
    inv = list(emu.ram(0x4F0, 12))
    if last_hp is not None:
        for i in range(12):
            if hp[i] < last_hp[i]:
                hits.append((k - a, i, last_hp[i], hp[i], inv[i]))
    timers.append(inv)
    last_hp = hp
print("hits:", len(hits))
for f, i, h0, h1, t in hits[:30]:
    run = [timers[j][i] for j in range(f, min(f + 40, len(timers)))]
    n = next((j for j, v in enumerate(run) if v == 0), None)
    print(f"  frame {f:4d} slot {i} hp {h0}->{h1} timer at hit {t}; zero again after {n} frames: {run[:24]}")
gaps = [hits[j + 1][0] - hits[j][0] for j in range(len(hits) - 1)]
print("frames between consecutive hits:", gaps, "mean", sum(gaps) / max(1, len(gaps)))
emu.close()
