"""Replay a run and list every major acquisition, with frame numbers.

    python3 pickup_scan.py                 # the verified run6
    python3 pickup_scan.py milestone3      # any run with logs/<name>.inputs.txt

Screenshots every Triforce piece, heart container and sword upgrade. Writes
logs/<name>_pickups.json (machine-readable) and logs/<name>_pickups.events.txt
(shaped for emu.note(), so the overlay picks the labels up).
"""
import json
import sys
from pathlib import Path

from zelda import BizHawk, ram, replay
from zelda.pickups import Tracker

name = sys.argv[1] if len(sys.argv) > 1 else "run6"
in_runs = Path(f"runs/{name}/inputs.txt")
in_logs = Path(f"logs/{name}.inputs.txt")
src = in_runs if in_runs.exists() else in_logs
if not src.exists():
    raise SystemExit(f"no input log for {name!r}: looked for {in_runs} and {in_logs}")

SHOT_KINDS = ("triforce", "heart_container")


def wanted(p) -> bool:
    return p.kind in SHOT_KINDS or "sword" in p.name


frames = replay.load_inputs(src)
tr = Tracker()
shots: list[str] = []

print(f"{name}: {len(frames)} frames from {src}")
with BizHawk(log_name="pickups.log") as emu:
    i = 0
    while i < len(frames):
        j = i
        while j < len(frames) and frames[j] == frames[i]:
            j += 1
        emu.step(frames[i], j - i)
        st = emu.state()
        if not tr.armed and st.mode == ram.MODE_NORMAL and st.level == 0 and st.room == ram.START_ROOM:
            tr.arm()                     # first frame the game is really running
        for p in tr.acquired(emu.ram, j):
            if wanted(p):
                shots.append(str(emu.screenshot(f"pickup_f{j:06d}_{p.name.replace(' ', '_')}")))
        i = j

# "unverified" rows are bytes that changed with no explanation attached - reported,
# but never counted as something the route acquired.
acq = [p for p in tr.events if p.kind not in ("consumed", "unverified")]
unver = [p for p in tr.events if p.kind == "unverified"]
print(f"\n{len(acq)} major acquisitions over {len(frames)} frames"
      + (f"  (+{len(unver)} unverified byte change(s))" if unver else ""))
print("summary:", tr.summary())
print()
for p in tr.events:
    print(f"  f{p.frame:>7}  {p.kind:<16} {p.name:<28} {p.detail}")

# The dungeon order falls out of the Triforce bitmask, in acquisition order.
order = [p.name.split()[2] for p in tr.events if p.kind == "triforce"]  # "Triforce piece N of 8"
print()
print("dungeon order derived from the Triforce bitmask:", "-".join(order))

Path(f"logs/{name}_pickups.json").write_text(json.dumps(
    [{"frame": p.frame, "kind": p.kind, "name": p.name, "detail": p.detail} for p in tr.events],
    indent=1), encoding="utf-8")
Path(f"logs/{name}_pickups.events.txt").write_text(
    "".join(f"{fr}\t{txt}\n" for fr, txt in tr.to_events()), encoding="utf-8")
print(f"wrote logs/{name}_pickups.json and logs/{name}_pickups.events.txt")
print(f"screenshots: {len(shots)}")
