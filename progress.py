"""Progress of the running full-game attempt: what committed since the last resume, milestone deltas
against the first finished run, and any segment that exhausted its tries."""
import csv
import pathlib
import re
import sys

base = {r["milestone"]: int(r["old_frames"]) for r in
        csv.DictReader(open("knowledge/baseline_milestones.tsv", encoding="utf-8"), delimiter="\t")}
text = pathlib.Path("logs/run_until.log").read_text(encoding="utf-8", errors="replace")
marks = [m.start() for m in re.finditer(r"^=== attempt \d+ \(", text, re.M)]
tail = text[marks[-1]:] if marks else text
rows = re.findall(r"\[(\w+)\] (\d+) frames, hearts ([\d.]+) ->.*?rup=(\d+).*?\(total (\d+) frames", tail)
show = int(sys.argv[1]) if len(sys.argv) > 1 else 8
print(f"committed since resume: {len(rows)}")
for n, f, h, rup, tot in rows[-show:]:
    print(f"   {n:14s} {f:>5} frames  {h:>4} hearts  {rup:>3} rupees  total {tot}")
if rows:
    cur = int(rows[-1][4])
    print(f"now at {cur} frames = {cur / 60.0988 / 60:.1f} min of game time")
for n, f, h, rup, tot in rows:
    if n in base:
        print(f"   milestone {n:10s} new {int(tot):7d}  old {base[n]:7d}  {int(tot) - base[n]:+7d}")
fails = re.findall(r"no success; most common: ([^\n]{0,90})", tail)
print(f"failed: {len(fails)}", fails[-1] if fails else "")
print("last lines:")
for line in tail.strip().splitlines()[-3:]:
    print("   ", line[:150])
