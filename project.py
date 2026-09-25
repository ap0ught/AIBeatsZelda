"""Projected finish: frames so far + the first run's per-segment frames for every segment still ahead."""
import json, pathlib
import fullgame
p = pathlib.Path("logs/archive/20260915_225349/checkpoints")
old = json.loads((p / "fullgame_g9_credits.json").read_text())["segments"]
prev = 0; dd = {}
for n in old:
    f = p / f"fullgame_{n}.json"
    if f.exists():
        fr = json.loads(f.read_text())["frames"]; dd[n] = fr - prev; prev = fr
PROXY = {"dm9_w0b": "r9_w0b", "enter_L9": "enter_L9", "hc_w37": "hc_w37"}
names = [s[0] for s in fullgame.segments()]
ck = pathlib.Path("logs/checkpoints")
have = [n for n in names if (ck / f"fullgame_{n}.json").exists()]
cur = json.loads((ck / f"fullgame_{have[-1]}.json").read_text())["frames"]
rest = names[names.index(have[-1]) + 1:]
def old_cost(n):
    if n in dd: return dd[n]
    if n.startswith("dm9_"): return dd.get("r9_" + n[4:], 400)
    return dd.get(PROXY.get(n, ""), 400)
est = sum(old_cost(n) for n in rest)
if "cave_6b" in rest: est -= dd["cave_6b"]      # skipped when the purse covers the arrows
tot = cur + est
print(f"at {have[-1]} {cur}; {len(rest)} segments left ~{est}")
print(f"PROJECTED {tot} = {tot/60.0988/60:.2f} min; margin to 216,000: {216000-tot:+d}; at the rescue (minus credits {dd['g9_credits']}): {(tot-dd['g9_credits'])/60.0988/60:.2f} min")
# live vs old over the segments both runs share since L6_done
live = [n for n in have[have.index('L6_done'):] if n in dd] if 'L6_done' in have else []
lp = {n: json.loads((ck / f"fullgame_{n}.json").read_text())["frames"] for n in have}
diffs = []
for a, b in zip(have, have[1:]):
    if b in dd and have.index(b) > have.index("L6_done"):
        diffs.append((lp[b] - lp[a] - dd[b], b))
print("since L6_done, live minus old per segment:", sum(d for d, _ in diffs), "| worst:", sorted(diffs, reverse=True)[:5])
