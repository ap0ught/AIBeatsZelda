"""Finish what patch_caves_route.py started: its edits to fullgame.py landed, but its post-check still
expected the 0x2D cave that was deliberately dropped, so it stopped before rolling back. Verify the new
route, back up and remove checkpoints after the resume point, re-stamp the rest."""
import hashlib
import json
import pathlib
import shutil
import time

import fullgame

names = [s[0] for s in fullgame.segments()]
assert len(names) == len(set(names)), "duplicate names"
for key in ("cave_3d", "c0f_1d", "c0f_0f", "cave_0f", "c0f_b2d", "bait_34", "buy_food", "enter_L7"):
    assert key in names, f"missing {key}"
gone = [n for n in names if n.startswith(("l6_farm", "m7_", "b7_", "heal", "fd")) or n in
        ("farm68", "farm80", "w7_52", "whirl_l6", "l7_drain2", "enter_L7b", "cave_2d")]
assert not gone, f"leftovers: {gone}"
print(f"{len(names)} segments; new route verified")
i = names.index("l5w03_2d")
print("  the 0x0F detour:", names[i:i + 11])
j = names.index("buy_arrows")
print("  the shop trip:  ", names[j:j + 6])
k = names.index("l7_drain")
print("  Level 7:        ", names[k:k + 3])

h = hashlib.sha1("|".join(names).encode()).hexdigest()[:12]
ck = pathlib.Path("logs/checkpoints")
resume_at = "l5w02_3d"
keep = set(names[:names.index(resume_at) + 1])
bak = pathlib.Path("logs/archive/partial_" + time.strftime("%Y%m%d_%H%M%S"))
bak.mkdir(parents=True, exist_ok=True)
removed = 0
for p in ck.glob("fullgame_*.json"):
    n = p.stem.replace("fullgame_", "")
    if n not in keep:
        shutil.copy2(p, bak / p.name)
        p.unlink()
        removed += 1
for p in ck.glob("fullgame_*.json"):
    d = json.loads(p.read_text())
    if d.get("list_hash") != h:
        d["list_hash"] = h
        p.write_text(json.dumps(d))
have = [n for n in names if (ck / f"fullgame_{n}.json").exists()]
d = json.loads((ck / f"fullgame_{have[-1]}.json").read_text())
print(f"removed {removed} checkpoints (backed up to {bak}); re-stamped with {h}")
print(f"resume point: {have[-1]} at {d['frames']} frames | {d['summary'][40:95]}")
assert have[-1] == resume_at, have[-1]
