"""Fact sheet for the caption audit: every segment of a recorded run with where Link really is (room at the start,
the room he spends most of it in, room at the end) and what he carries, next to the caption the overlay shows.
usage: python caption_sheet.py <archive dir> [first] [last]"""
import json, pathlib, re, sys
from zelda import intent
ARCH = pathlib.Path(sys.argv[1]); lo = int(sys.argv[2]) if len(sys.argv) > 2 else 0; hi = int(sys.argv[3]) if len(sys.argv) > 3 else 9999
order = sorted(((json.load(open(f))["frames"], f.stem[9:]) for f in (ARCH / "checkpoints").glob("fullgame_*.json")))
rows = []
with open(ARCH / "fullgame_run.trace.txt", encoding="utf-8", errors="replace") as f:
    for line in f:
        p = line.rstrip("\n").split("\t")
        kv = dict(t.split("=") for t in p[2].split() if "=" in t)
        rows.append((int(kv["mode"]), int(kv["level"]), int(kv["room"]), int(kv["hp"]), int(kv["bombs"]), int(kv["keys"]),
                     int(kv["rupees"]), int(kv["triforce"]), int(kv["sword"])))
prev = 0
for k, (fr, n) in enumerate(order):
    a, b = prev, min(fr, len(rows) - 1); prev = fr
    if not (lo <= k < hi):
        continue
    rooms = {}
    for j in range(a, b):
        if rows[j][0] == 5:
            rooms[(rows[j][1], rows[j][2])] = rooms.get((rows[j][1], rows[j][2]), 0) + 1
    main = max(rooms, key=rooms.get) if rooms else (rows[a][1], rows[a][2])
    r = rows[a]
    head, why = intent.for_segment(n, {})
    flag = ""
    m = re.search(r"LEVEL (\d)", head)
    if m and int(m.group(1)) != main[0] and not re.search(r"^TO |DONE|OUT OF|WARP|TOWARD|RIDE|WHIRLWIND", head):
        flag = " <<LEVEL?"
    tri = bin(r[7]).count("1")
    print(f"{k:3d} {n:12s} L{r[1]}:{r[2]:02X}>L{main[0]}:{main[1]:02X}>L{rows[b][1]}:{rows[b][2]:02X} h{r[3] / 16:.0f}? b{r[4]} k{r[5]} r{r[6]} t{tri} s{r[8]}{flag} | {head} | {why}")
