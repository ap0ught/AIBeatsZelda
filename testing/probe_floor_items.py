"""Which rooms put a key on the floor, and which rooms a kill drops a bomb in.

    python3 testing/probe_floor_items.py [inputs] [rom]

Issue #6 needs concrete rooms to test against, and there are two different questions hiding
behind the phrase "key rooms", which is why this records both:

- **Change 2 (keys).**  A key cannot come from a monster drop - the complete set a monster
  produces is bomb / 5 rupees / rupee / clock / heart / fairy, confirmed 43/43 over run6.
  A key is a *room item*: object slot 0x13, read by `read_room_item`. The planner already
  reads those and now prices them by scarcity, so the rooms to test that fix are the rooms
  whose room item is a key.

- **Change 1 (future drops).**  The thing still unimplemented is shaping a fight toward
  where the *next kill's* drop will land. That is about monster drops, so its test rooms
  are the rooms where a kill actually produced a bomb or a rupee - not key rooms. A key
  room is the wrong test for it, and using one would test a code path the change does not
  touch.

Recording both in one pass is cheaper than two runs, and the room ids line up so the two
lists can be compared: if a room gives a key *and* drops bombs, it exercises everything.

A room is identified by `(level, room)` from the game's own counters, which is the only
identity that survives a scroll - screen coordinates do not, and two rooms can share them.
Positions are recorded too, but as a within-room offset, for a human reading the room.

## Cost

Two RAM reads a frame plus one `state()` per event, and there are few events, so this is
about as slow as the drop probe (~3 minutes for the full run6). Progress unbuffered, so it
can be run detached:

    nohup python3 -u testing/probe_floor_items.py > /tmp/floor.txt 2>&1 &
"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # runs/, logs/ are repo-relative
del _os, _sys, _pathlib

import collections
import hashlib
import json
import sys
import time
from pathlib import Path

from zelda import BizHawk, replay
from zelda.emulator import ROM

OBJ_TYPE = 0x34F     # $60 is UpdateItem, i.e. a monster's drop
ITEM_ID = 0xAC       # Item_ObjItemId, the drop's item
OBJ_X, OBJ_Y = 0x70, 0x84
ITEM_SLOT = 0xBF     # room item status: FF = nothing lying here
ITEM_ID_ADDR = 0xAB  # the room item's id
ITEM_X, ITEM_Y = 0x83, 0x97
NSLOT = 12
DROP_TYPE = 0x60

NAMES = {0x00: "bombs", 0x0F: "5 rupees", 0x18: "rupee", 0x19: "KEY",
         0x21: "clock", 0x22: "heart", 0x23: "fairy"}


def name(i: int) -> str:
    return NAMES.get(i, f"${i:02X}")


def main() -> int:
    inputs = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("runs/run6/inputs.txt")
    rom = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(ROM)
    frames = replay.load_inputs(inputs)

    print(f"cartridge : {rom}")
    print(f"md5       : {hashlib.md5(rom.read_bytes()).hexdigest()}")
    print(f"input log : {inputs}  ({len(frames)} frames)\n", flush=True)

    t0 = time.time()
    drops: list[dict] = []      # monster drops, $60 objects
    room_items: list[dict] = []  # slot 0x13, the room's own item
    prev_room = None
    nframes = 0

    with BizHawk(rom=rom, log_name="flooritems.log") as emu:
        print("  connected", flush=True)
        prev_types = emu.ram(OBJ_TYPE, NSLOT)
        for i, btn in enumerate(frames):
            emu.step(btn, 1)
            nframes = i + 1
            types = emu.ram(OBJ_TYPE, NSLOT)

            for s in range(1, NSLOT):
                if types[s] == DROP_TYPE and prev_types[s] != DROP_TYPE:
                    st = emu.state()
                    item = emu.ram(ITEM_ID, NSLOT)[s]
                    drops.append(dict(frame=i, level=st.level, room=st.room,
                                      x=emu.ram(OBJ_X, NSLOT)[s],
                                      y=emu.ram(OBJ_Y, NSLOT)[s], item=item,
                                      keys_held=st.keys, rupees=st.rupees,
                                      bombs=st.bombs))

            # The room item sits on the floor until taken, so record the frame it APPEARS
            # rather than every frame it is there - otherwise one key produces 400 rows.
            status = emu.byte(ITEM_SLOT)
            sig = None if status == 0xFF else (status, emu.byte(ITEM_ID_ADDR))
            if sig is not None and sig != prev_room:
                stt = emu.state()
                room_items.append(dict(frame=i, level=stt.level, room=stt.room,
                                       item=sig[1], x=emu.byte(ITEM_X),
                                       y=emu.byte(ITEM_Y), keys_held=stt.keys))
            prev_room = sig
            prev_types = types

            if nframes % 5000 == 0:
                el = time.time() - t0
                rate = nframes / el
                print(f"  f{nframes:>7}  {rate:6.1f} f/s  {len(drops)} drops  "
                      f"{len(room_items)} room items  "
                      f"eta {(len(frames) - nframes) / rate / 60:5.1f} min", flush=True)

    return report(drops, room_items, nframes, time.time() - t0)


def report(drops, room_items, nframes, elapsed) -> int:
    print(f"\n{nframes} frames in {elapsed:.0f}s")
    print(f"  {len(drops)} monster drops, {len(room_items)} room-item appearances\n")

    keys = [r for r in room_items if r["item"] == 0x19]
    print("=" * 72)
    print(f"ROOMS WITH A KEY AS THE ROOM ITEM - the test set for Change 2 ({len(keys)} seen)")
    print("=" * 72)
    if not keys:
        print("  none in this run. See the caveat below: one route does not visit every room.")
    by_room = collections.defaultdict(list)
    for r in keys:
        by_room[(r["level"], r["room"])].append(r)
    print(f"  {'level':>6} {'room':>5}  {'at':>10}  {'frames':>18}  keys held when it appeared")
    for (lv, rm), rs in sorted(by_room.items()):
        at = f"({rs[0]['x']},{rs[0]['y']})"
        fr = f"{rs[0]['frame']}" + (f"-{rs[-1]['frame']}" if len(rs) > 1 else "")
        print(f"  {lv:>6} {rm:>5}  {at:>10}  {fr:>18}  {rs[0]['keys_held']}")

    print()
    print("=" * 72)
    print("ROOMS WHERE A KILL DROPPED A BOMB OR RUPEE - the test set for Change 1")
    print("=" * 72)
    useful = [d for d in drops if d["item"] in (0x00, 0x0F, 0x18)]
    by_room2 = collections.defaultdict(lambda: collections.Counter())
    for d in useful:
        by_room2[(d["level"], d["room"])][name(d["item"])] += 1
    print(f"  {len(useful)} bomb/rupee drops across {len(by_room2)} rooms\n")
    print(f"  {'level':>6} {'room':>5}  {'what landed':<34} first frame")
    for (lv, rm), c in sorted(by_room2.items(), key=lambda kv: -sum(kv[1].values())):
        first = min(d["frame"] for d in useful if (d["level"], d["room"]) == (lv, rm))
        print(f"  {lv:>6} {rm:>5}  {', '.join(f'{k} x{v}' for k, v in c.most_common()):<34} {first}")

    print()
    print("=" * 72)
    print("BOTH AT ONCE - rooms that exercise keys and future drops together")
    print("=" * 72)
    both = sorted(set(by_room) & set(by_room2))
    print(f"  {len(both)} room(s): "
          + (", ".join(f"L{lv}R{rm}" for lv, rm in both) if both else "none in this run"))

    out = Path("logs/floor_items.json")
    out.write_text(json.dumps(dict(drops=drops, room_items=room_items, frames=nframes),
                              indent=1))
    print(f"\nper-event log: {out}")
    print("\nCaveat worth keeping on the ticket: these are the rooms ONE route happens to")
    print("walk through. Absence from this list is not evidence a room has no key - it is")
    print("evidence this run never stood in it. A room list for a regression test wants")
    print("every room, which means reading the room-item table out of the cartridge the way")
    print("probe_drop_table.py reads the drop table, not sampling a route.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
