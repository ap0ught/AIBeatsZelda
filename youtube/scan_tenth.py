"""Find the tenth-kill bomb drops in run 6: replay the whole input log reading the kill-streak counter ($50), the
forced-drop value ($51) and Link's bombs every frame. Prints every streak that reached ten and what dropped."""
import json, pathlib, sys
sys.path.insert(0, ".")
from zelda import replay
from zelda.emulator import BizHawk
inp = replay.load_inputs("logs/archive/sixth_run_20260922/fullgame.inputs.txt")
emu = BizHawk(log_name="scan_tenth.log")          # clean battery save, like the recorder: the replay must start from real power-on
prev = None; events = []
for k, b in enumerate(inp):
    emu.step(b, 1)
    if k % 2:
        continue
    r = emu.ram(0x50, 2); c50, c51 = r[0], r[1]
    if prev is not None and prev[0] >= 8 and c50 < prev[0]:      # the streak ended (a hit or the tenth kill)
        s = emu.state()
        events.append({"frame": k, "streak_before": prev[0], "value": c51, "bombs": s.bombs, "level": s.level, "room": s.room})
        print(f"frame {k:6d} L{s.level} room {s.room:02X}: streak {prev[0]} -> {c50}, drop value {c51}, bombs {s.bombs}", flush=True)
    prev = (c50, c51)
json.dump(events, open("youtube/capture/tenth_kill_events.json", "w"), indent=1)
emu.close()
