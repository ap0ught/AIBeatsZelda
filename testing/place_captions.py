"""Rebuild logs/<name>_run.events.txt from the recorded trace: one caption per segment, placed where the segment
is really happening.

The owner, after the fourth run: captions were "a screen or two away from where you actually are, but then they
catch up". A segment such as l4_13 ("five Vires, then Gleeok") starts in the room BEFORE 13 - its first job is to walk
through the bombed wall - and the caption used to go up at the segment's first frame, describing a room Link had not
entered yet. Now a caption goes up at the first frame Link spends in the room the segment mostly happens in; a plain
crossing (which mostly happens in the room it starts in) still captions from its first frame. Counts in the text are
filled from the game state at that frame.

usage: ZELDA_ROUTE=4 python place_captions.py [name]     (then closing_captions.py, then render_overlay.py)"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import pathlib
import sys

import record_run
from zelda import intent
from zelda.emulator import State

name = sys.argv[1] if len(sys.argv) > 1 else "fullgame"
LOGS = pathlib.Path("logs")
marks = record_run.boundaries(name)
ks = sorted(marks)
rows: list[State] = []
with open(LOGS / f"{name}_run.trace.txt", encoding="utf-8", errors="replace") as f:
    for line in f:
        rows.append(State.parse(line.rstrip("\n").split("\t")[2]))
n = len(rows)
out = []
for i, k in enumerate(ks):
    a, b = k, (ks[i + 1] if i + 1 < len(ks) else n)
    if a >= n:
        at = n - 1
        st = rows[-1]
    else:
        counts: dict = {}
        for j in range(a, min(b, n)):
            r = rows[j]
            if r.mode in (5, 9) and not r.paused:          # 9: cellars, caves and passages
                counts[(r.level, r.room)] = counts.get((r.level, r.room), 0) + 1
        start_room = (rows[a].level, rows[a].room)
        main = max(counts, key=counts.get) if counts else start_room
        at = a
        # Only a segment that merely PASSES through its first room (a few steps to a bombed hole or a door,
        # under a second and a half) and then spends real time in the next (five seconds or more) captions from
        # the next room. A walk, a warp, a Triforce pickup or the title screen keeps its caption at its first frame.
        if main != start_room and counts.get(start_room, 0) < 90 and counts.get(main, 0) >= 300 and a > 0:
            for j in range(a, min(b, n)):
                if (rows[j].level, rows[j].room) == main and rows[j].mode in (5, 9):
                    at = j
                    break
        st = rows[at]
    head, why = intent.for_segment(marks[k], record_run.NARRATION)
    facts = intent.facts_from(st)
    out.append((at, intent.fill(head, facts), intent.fill(why, facts), marks[k], at - a))
moved = [(d, s) for at, h, w, s, d in out if d > 0]
ev = LOGS / f"{name}_run.events.txt"
# the recorder stamps a note with the emulator's frame counter, which runs one ahead of the input index
ev.write_text("".join(f"{at + 1}\t{h}||{w}\n" for at, h, w, s, d in out), encoding="utf-8")
print(f"{len(out)} captions written to {ev}; {len(moved)} placed later than their segment's first frame, "
      f"the furthest by {max((d for d, _ in moved), default=0)} frames: "
      + ", ".join(f"{s} +{d}" for d, s in sorted(moved, reverse=True)[:12]))
