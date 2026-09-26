"""Room-path audit of every dungeon from the cartridge's door tables.

For each level: the start, boss and Triforce rooms and the cellars (item cellars and passages) from the level's
info block, then the cheapest room path   start -> required item -> boss -> Triforce   under a simple cost model
in which BOMBS ARE PLENTIFUL (what forced drops would make true), compared with the rooms the third run walked.

    open door 1 room, bombable wall 1 room + BOMB, locked door 1 room + KEY, shutter = the room must be cleared
    first (CLEAR), a passage counts as a room.

This is a finder of candidates, not a verdict: every candidate still has to be walked in the emulator.
usage: python dungeon_paths.py [level ...]"""
from __future__ import annotations
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib

import glob
import heapq
import json
import os
import re
import sys

from zelda import romdata

ROOM = 400          # frames for one more room: ~172 of scroll + a crossing
BOMB = 330          # lay it, wait for the wall, (sometimes) a subscreen trip
KEY = 40
CLEAR = 900         # killing a room to open its shutter - the big one
REQUIRED_ITEM = {1: 0x0A, 3: 0x0C, 4: 0x0D, 5: 0x05, 9: 0x09}      # bow, raft, ladder, recorder, silver arrows
ITEM_NAMES = {0x0A: "bow", 0x0C: "raft", 0x0D: "ladder", 0x05: "recorder", 0x09: "silver arrows", 0x07: "red candle",
              0x1D: "boomerang", 0x1E: "magic boomerang", 0x0B: "magic key", 0x10: "wand", 0x11: "book", 0x13: "red ring",
              0x1A: "heart container"}
OPP = {"N": "S", "S": "N", "W": "E", "E": "W"}
STEP = {"N": -16, "S": 16, "W": -1, "E": 1}


def level_info(level: int) -> dict:
    prg = romdata.rom()[16:]
    base = 0x19300 + level * 0xFC
    cellars = [c for c in prg[base + 0x34: base + 0x3E] if c != 0xFF]
    return {"start": prg[base + 0x2F], "triforce": prg[base + 0x30], "boss": prg[base + 0x3E], "cellars": cellars}


def raw_ab(level: int, room: int):
    r = romdata.rom()
    base = 16 + (0x18700 if level <= 6 else 0x18A00)
    return r[base + room], r[base + 0x80 + room], r[base + 0x200 + room] & 0x1F


def build(level: int):
    info = level_info(level)
    passages, item_rooms = [], {}
    for c in info["cellars"]:
        a, b, item = raw_ab(level, c)
        if a == b:
            item_rooms[a] = item
        else:
            passages.append((a, b))
    # flood the level from its start room
    rooms, todo = set(), [info["start"]]
    while todo:
        r = todo.pop()
        if r in rooms or not (0 <= r < 0x80):
            continue
        rooms.add(r)
        d = romdata.doors(level, r)
        for k, kind in d.items():
            if kind != "wall":
                todo.append(r + STEP[k])
        for a, b in passages:
            if r == a:
                todo.append(b)
            if r == b:
                todo.append(a)
    return info, rooms, passages, item_rooms


def edges(level, room, rooms, passages):
    d = romdata.doors(level, room)
    for k, kind in d.items():
        n = room + STEP[k]
        if kind == "wall" or n not in rooms:
            continue
        # a door is as hard as its harder side (a shutter on the far side does not stop Link leaving through it)
        yield n, kind, k
    for a, b in passages:
        if room == a:
            yield b, "passage", "st"
        if room == b:
            yield a, "passage", "st"


def cost_of(kind: str) -> tuple:
    return {"open": (ROOM, 0, 0, 0), "bombable": (ROOM + BOMB, 1, 0, 0), "locked": (ROOM + KEY, 0, 1, 0),
            "shutter": (ROOM + CLEAR, 0, 0, 1), "passage": (ROOM + CLEAR * 0.6, 0, 0, 0)}.get(kind, (ROOM, 0, 0, 0))


def shortest(level, src, dst, rooms, passages):
    dist, prev = {src: 0.0}, {}
    pq = [(0.0, src)]
    while pq:
        dcur, r = heapq.heappop(pq)
        if r == dst:
            break
        if dcur > dist.get(r, 1e18):
            continue
        for n, kind, k in edges(level, r, rooms, passages):
            c = cost_of(kind)[0]
            if dcur + c < dist.get(n, 1e18):
                dist[n] = dcur + c
                prev[n] = (r, kind)
                heapq.heappush(pq, (dcur + c, n))
    if dst not in dist:
        return None, []
    path, r = [], dst
    while r in prev:
        p, kind = prev[r]
        path.append((r, kind))
        r = p
    return dist[dst], path[::-1]


def walked(level: int) -> list:
    rows = []
    for f in glob.glob("logs/archive/third_run_20260919b/checkpoints/fullgame_*.json"):
        d = json.load(open(f))
        m = re.search(r"mode=(\w\w)/\w\w L(\d) room=([0-9a-f]{2})", d["summary"])
        rows.append((d["frames"], int(m.group(2)), int(m.group(3), 16), os.path.basename(f)[9:-5]))
    rows.sort()
    out, prev, frames0, frames1 = [], None, None, None
    for fr, lvl, room, name in rows:
        if lvl == level and not name.endswith("_done"):
            frames0 = frames0 or fr
            frames1 = fr
            if room != prev:
                out.append(room)
            prev = room
        elif out and lvl != level:
            pass
    return out, (frames1 - frames0 if frames0 else 0)


def report(level: int):
    info, rooms, passages, item_rooms = build(level)
    print(f"\n=== LEVEL {level}: {len(rooms)} rooms, start {info['start']:02X}, boss {info['boss']:02X}, "
          f"Triforce {info['triforce']:02X}")
    print("    item cellars: " + ", ".join(f"{r:02X}={ITEM_NAMES.get(i, hex(i))}" for r, i in item_rooms.items())
          + "   passages: " + ", ".join(f"{a:02X}<->{b:02X}" for a, b in passages))
    stops = [info["start"]]
    want = REQUIRED_ITEM.get(level)
    for r, i in item_rooms.items():
        if i == want:
            stops.append(r)
    stops += [info["boss"], info["triforce"]]
    total, bombs, keys, clears, seq = 0.0, 0, 0, 0, [f"{info['start']:02X}"]
    for a, b in zip(stops, stops[1:]):
        c, path = shortest(level, a, b, rooms, passages)
        if c is None:
            print(f"    no path {a:02X} -> {b:02X}")
            continue
        total += c
        for r, kind in path:
            _, nb, nk, nc = cost_of(kind)
            bombs += nb; keys += nk; clears += nc
            seq.append({"open": "", "bombable": "B>", "locked": "K>", "shutter": "S>", "passage": "~>"}[kind] + f"{r:02X}")
    print(f"    model path ({len(seq) - 1} room entries, {bombs} bombs, {keys} keys, {clears} shutter rooms): " + " ".join(seq))
    mine, frames = walked(level)
    print(f"    third run  ({len(mine) - 1} room entries, {frames} frames): " + " ".join(f"{r:02X}" for r in mine))


if __name__ == "__main__":
    for lvl in ([int(a) for a in sys.argv[1:]] or range(1, 10)):
        report(lvl)
