"""Film the tenth-kill bomb drop found in run 6 (L4 room 12, frame 45234): every frame from 600 frames before to 200
after, with the streak counter ($50), the forced-drop value ($51), bombs and the kill counter logged per frame."""
import json, pathlib, shutil, sys
sys.path.insert(0, ".")
from zelda import replay
from zelda.emulator import BizHawk
F = int(sys.argv[1]) if len(sys.argv) > 1 else 45234
ARCH = pathlib.Path("logs/archive/sixth_run_20260922")
inp = replay.load_inputs(ARCH / "fullgame.inputs.txt")
ck = sorted(((json.load(open(f))["frames"], json.load(open(f))["state"]) for f in (ARCH / "checkpoints").glob("fullgame_*.json")))
fr0, st = max(c for c in ck if c[0] <= F - 600)
out = pathlib.Path("youtube/capture/tenth"); out.mkdir(parents=True, exist_ok=True)
emu = BizHawk(log_name="capture_tenth.log", clean_sram=False)
emu.load(f"run6/{st}")
meta = []
for k in range(fr0, F + 200):
    s = emu.step(inp[k], 1)
    if k >= F - 600:
        r = emu.ram(0x50, 2)
        j = k - (F - 600)
        shutil.copyfile(emu.screenshot("_tenth_tmp"), out / f"{j:04d}.png")
        meta.append({"frame": k, "streak": r[0], "value": r[1], "bombs": s.bombs, "kills": s.kills, "hearts": s.hearts, "x": s.x, "y": s.y, "buttons": list(inp[k])})
json.dump(meta, open(out / "meta.json", "w"))
print("filmed", len(meta), "frames from", F - 600)
emu.close()
