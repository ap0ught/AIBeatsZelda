"""After a route edit that only changes segments AHEAD of the run: re-stamp every checkpoint with the new
segment-list fingerprint, back up and remove any checkpoint whose name left the route, and confirm the
resume point is still the newest checkpoint on the new list."""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import hashlib
import json
import pathlib
import shutil
import time

import fullgame

names = [s[0] for s in fullgame.segments()]
assert len(names) == len(set(names)), "duplicate names"
h = hashlib.sha1("|".join(names).encode()).hexdigest()[:12]
ck = pathlib.Path("logs/checkpoints")
newest = max(ck.glob("fullgame_*.json"), key=lambda p: json.loads(p.read_text())["frames"])
bak = pathlib.Path("logs/archive/partial_" + time.strftime("%Y%m%d_%H%M%S"))
removed = 0
for p in ck.glob("fullgame_*.json"):
    n = p.stem.replace("fullgame_", "")
    if n not in names:
        bak.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, bak / p.name)
        p.unlink()
        removed += 1
        continue
    d = json.loads(p.read_text())
    if d.get("list_hash") != h:
        d["list_hash"] = h
        p.write_text(json.dumps(d))
have = [n for n in names if (ck / f"fullgame_{n}.json").exists()]
d = json.loads((ck / f"fullgame_{have[-1]}.json").read_text())
print(f"{len(names)} segments, fingerprint {h}; removed {removed} off-route checkpoints")
print(f"resume point: {have[-1]} at {d['frames']} frames (newest before: {newest.stem})")
assert "fullgame_" + have[-1] == newest.stem, "the newest checkpoint is not the resume point"
gaps = [n for n in names[:names.index(have[-1])] if n not in have]
assert not gaps, f"checkpoints missing before the resume point: {gaps[:5]}"
