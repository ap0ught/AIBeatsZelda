"""Film every frame of an input list from a run-6 bookmark: python youtube/film_inputs.py <state> <json with 'inputs'> <outdir>"""
import json, pathlib, shutil, sys
sys.path.insert(0, ".")
from zelda.emulator import BizHawk
state, src, outdir = sys.argv[1], sys.argv[2], pathlib.Path(sys.argv[3])
outdir.mkdir(parents=True, exist_ok=True)
inputs = json.load(open(src))["inputs"]
emu = BizHawk(log_name="film_inputs.log", clean_sram=False)
emu.load(state)
for k, b in enumerate(inputs):
    emu.step(tuple(x for x in b.split(",") if x), 1)
    shutil.copyfile(emu.screenshot("_film_tmp"), outdir / f"{k:04d}.png")
emu.close()
print("filmed", len(inputs), "frames")
