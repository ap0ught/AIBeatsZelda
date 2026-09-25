"""Roll the run back to a checkpoint: back up and remove every fullgame checkpoint JSON with more frames than
`name`'s. (The .State files stay; they are overwritten as the run passes them again.)
usage: python rollback_to.py <segment name>"""
import json
import pathlib
import shutil
import sys
import time

name = sys.argv[1]
ck = pathlib.Path("logs/checkpoints")
keep = json.loads((ck / f"fullgame_{name}.json").read_text())["frames"]
bak = pathlib.Path("logs/archive/partial_" + time.strftime("%Y%m%d_%H%M%S") + f"_after_{name}")
n = 0
for p in ck.glob("fullgame_*.json"):
    if json.loads(p.read_text())["frames"] > keep:
        bak.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, bak / p.name)
        p.unlink()
        n += 1
print(f"rolled back to {name} ({keep} frames); {n} later checkpoints moved to {bak}")
