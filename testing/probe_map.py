"""Investigate the compass/map bytes: what changed, where, and what it cost.

    python3 probe_map.py                  # the verified run6
    python3 probe_map.py milestone3       # any run with logs/<name>.inputs.txt

Data Crystal's RAM map documents $0667 compass and $0668 map as "one bit per
level", not 0/1 flags. This probe exists because the run first looked like it
contradicted that: $0668 went 0 -> 4 and later 4 -> 0x44. Under a per-level
reading those are level 3's map and level 7's, which is ordinary progress.

The interesting part is corroborating it independently. A map costs 15 rupees,
and $066D has already been established as the *displayed* rupee count, so a
purchase should show up as $066D dropping by exactly 0x0F on the same frame the
bit appears. A bit that changes with no rupee movement is something else - a
drop, a glitch, or a misread - and is worth knowing about.

Per the user's references, which are the canonical source for these encodings:
  https://datacrystal.tcrf.net/wiki/The_Legend_of_Zelda/RAM_map
  https://datacrystal.tcrf.net/wiki/The_Legend_of_Zelda/Notes
Both are Cloudflare-gated to scripted requests; archive.org snapshots of each are
recorded in zelda/ram.py.

Writes logs/<name>_mapcompass.json. Screenshots the frame after each transition.
"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import json
import sys
from pathlib import Path

from zelda import BizHawk, ram, replay

WATCH = {
    "compass": ram.COMPASS,
    "map": ram.MAP,
    "compass L9": ram.COMPASS_L9,
    "map L9": ram.MAP_L9,
}
MAP_PRICE = 15          # rupees, in displayed units
LEVEL_NAMES = {0: "overworld", 1: "L1 Eagle", 2: "L2 Water", 3: "L3 Tree",
               4: "L4 Gori", 5: "L5 Spikes", 6: "L6 Bridge", 7: "L7 Hammer",
               8: "L8 Statue", 9: "L9 Ganon"}

name = sys.argv[1] if len(sys.argv) > 1 else "run6"
in_runs = Path(f"runs/{name}/inputs.txt")
in_logs = Path(f"logs/{name}.inputs.txt")
src = in_runs if in_runs.exists() else in_logs
if not src.exists():
    raise SystemExit(f"no input log for {name!r}: looked for {in_runs} and {in_logs}")

frames = replay.load_inputs(src)
prev: dict[str, int] = {}
prev_rupees = None
armed = False
events: list[dict] = []
# Census of rupee movement. A map is 15, a compass 15, a candle 60, bait 60,
# arrows 80, potion 30, and 5-rupee drops are +5. If no -15 appears anywhere then
# the bot never bought a map, and a bit appearing in $0668 cannot be a purchase.
spend: dict[int, list[int]] = {}
gains: dict[int, int] = {}
PREV_PENDING = 300

print(f"{name}: {len(frames)} frames from {src}")
print("watching $%02X/$%02X/$%02X/$%02X (compass, map, compass L9, map L9) and $%02X rupees"
      % (ram.COMPASS, ram.MAP, ram.COMPASS_L9, ram.MAP_L9, ram.RUPEES))
with BizHawk(log_name="mapcompass.log") as emu:
    i = 0
    while i < len(frames):
        j = i
        while j < len(frames) and frames[j] == frames[i]:
            j += 1
        emu.step(frames[i], j - i)
        cur = {k: emu.byte(a) for k, a in WATCH.items()}
        rupees = emu.byte(ram.RUPEES)
        st = emu.state()
        if not armed:
            armed = True                      # establish a baseline before reporting
            prev, prev_rupees = cur, rupees
            i = j
            continue
        if prev_rupees is not None and rupees != prev_rupees:
            d = rupees - prev_rupees
            if d < 0:
                spend.setdefault(d, []).append(j)
            else:
                gains[d] = gains.get(d, 0) + 1
        for k in WATCH:
            a, b = prev[k], cur[k]
            if a == b:
                continue
            bits = [i2 + 1 for i2 in range(8) if (b >> i2) & 1 and not (a >> i2) & 1]
            lost = [i2 + 1 for i2 in range(8) if (a >> i2) & 1 and not (b >> i2) & 1]
            delta = None if prev_rupees is None else rupees - prev_rupees
            shot = str(emu.screenshot(f"mapcompass_f{j:06d}_{k.replace(' ', '')}_{b:02X}"))
            ev = dict(frame=j, byte=k, addr=f"${WATCH[k]:02X}", before=a, after=b,
                      gained_bits=bits, lost_bits=lost, rupees_before=prev_rupees,
                      rupees_after=rupees, rupee_delta=delta, level=st.level,
                      where=LEVEL_NAMES.get(st.level, f"level {st.level}"), room=st.room,
                      shot=Path(shot).name)
            events.append(ev)
            tag = ", ".join(f"L{i2}" for i2 in bits) or "(none)"
            money = "-" if delta is None else f"{delta:+d}"
            verdict = ""
            if delta is not None and delta == -MAP_PRICE:
                verdict = f"  <- costs exactly {MAP_PRICE}, consistent with a purchase"
            elif delta is not None and delta == 0:
                verdict = "  <- no rupees moved: NOT a shop purchase"
            print(f"  f{j:>7}  {k:<10} {a:02X} -> {b:02X}  gained {tag:<10} "
                  f"rupees {prev_rupees}->{rupees} ({money})  {ev['where']}{verdict}")
        prev, prev_rupees = cur, rupees
        i = j

out = Path(f"logs/{name}_mapcompass.json")
out.write_text(json.dumps(dict(run=name, frames=len(frames), map_price=MAP_PRICE,
                               events=events), indent=2))
print()
print("rupee census - decreases (spends):")
for d in sorted(spend, reverse=True):
    fr = spend[d]
    print(f"  {d:>5}  x{len(fr):<4} first f{fr[0]}" + ("  <- 15 = map or compass" if d == -15 else ""))
if not spend:
    print("  (none - the bot never spent a rupee in this run)")
print("rupee census - increases:", dict(sorted(gains.items())) or "(none)")

print()
if not events:
    print("no compass/map changes in this run")
else:
    print(f"{len(events)} change(s) -> {out}")
    for e in events:
        if e["rupee_delta"] is not None and e["rupee_delta"] == -MAP_PRICE:
            print(f"  confirmed: {e['byte']} L{e['gained_bits']} bought for {MAP_PRICE} rupees "
                  f"at f{e['frame']}")
