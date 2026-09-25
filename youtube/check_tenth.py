"""For every streak-of-ten ending found by scan_tenth.py: did bombs go up right after (a bomb-made tenth kill)?
Replays from the nearest run-6 checkpoint. Prints the bomb count 1 frame before and 180 frames after each event."""
import json, pathlib, sys
sys.path.insert(0, ".")
from zelda import replay
from zelda.emulator import BizHawk
ARCH = pathlib.Path("logs/archive/sixth_run_20260922")
inp = replay.load_inputs(ARCH / "fullgame.inputs.txt")
ck = sorted(((json.load(open(f))["frames"], json.load(open(f))["state"]) for f in (ARCH / "checkpoints").glob("fullgame_*.json")))
ev = json.load(open("youtube/capture/tenth_kill_events.json"))
emu = BizHawk(log_name="check_tenth.log", clean_sram=False)
out = []
for e in ev:
    f = e["frame"]
    if f < 100:
        continue
    fr0, st = max((c for c in ck if c[0] <= f - 60), default=(None, None))
    if st is None:
        continue
    emu.load(f"run6/{st}")
    bombs_before = bombs_after = None; val = 0
    for k in range(fr0, min(len(inp), f + 180)):
        s = emu.step(inp[k], 1)
        if k == f - 1:
            bombs_before = s.bombs
        if f - 4 <= k <= f + 4:
            val = max(val, emu.ram(0x51, 1)[0])
        bombs_after = s.bombs
    tag = "BOMB DROP" if bombs_after > (bombs_before or 0) else ""
    print(f"frame {f:6d} L{e['level']} room {e['room']:02X}: bombs {bombs_before} -> {bombs_after}  $51 max {val}  {tag}", flush=True)
    out.append({**e, "bombs_before": bombs_before, "bombs_after": bombs_after, "drop_value": val})
json.dump(out, open("youtube/capture/tenth_kill_checked.json", "w"), indent=1)
emu.close()
