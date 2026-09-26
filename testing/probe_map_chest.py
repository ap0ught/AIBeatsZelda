"""What writes $0668? Answer: a treasure chest in the dungeon, not a purchase.

    python3 testing/probe_map_chest.py [inputs]

This settles issue #5. The observed puzzle was that $0668 - the "map in
inventory, one bit per level" byte - changes twice in the verified run with no
rupee movement and no purchase, and the bits latch. Three readings had been
proposed and none confirmed: *reveal rather than ownership*, *a dual-purpose
byte*, and *a drop or bonus item*.

## The answer, from the code

Exactly one routine in the cartridge can write $0668, and it is not the shop.
"TakeClass0Complex" (Z_01.asm:4604 in aldonunez/zelda1-disassembly) reaches it
through a single indexed store that serves four variables at once:

    TakeClass0Complex:
        LDA CurLevel          ; $10
        BEQ @Exit             ; in the overworld, do nothing
        CPY #$11              ; the MAP item slot
        BNE :-
        LDX #$01
        STX StatusBarMapTrigger
        SEC / SBC #$01        ; level - 1
        CMP #$08 / BCC / INY / INY     ; level 9 uses $669/$66A instead
        AND #$07 / TAX
        LDA Items, Y          ; Items = $0657, so Y = $11 lands on $0668
        ORA LevelMasks, X     ; 01 02 04 08 10 20 40 80
        STA Items, Y

That shared store is *why* the byte is so hard to pin down from the outside: no
instruction in the ROM names $0668 as an operand, so a byte-pattern search for
the operand pair `68 06` finds nothing anywhere in PRG-ROM. A 6502 disassembler
reading straight from the ROM is worse than useless here - the address is not
where a reader expects it to be.

Y is an item slot, from ItemIdToSlot (Z_01.asm:4318): item id $16 -> slot $10
(compass, $0667), item id $17 -> slot $11 (map, $0668). The mask is
LevelMasks[level-1] = 01 02 04 08 10 20 40 80. So **bit 2 of $0668 is level 3's
map** and 0x44 adding bit 6 is level 7's - the RAM map's encoding, exactly.

The bit is not a purchase because the caller is a dungeon. The one `JSR TakeItem`
at Z_01.asm:833 is the cave/shop handler, but TakeItem is *also* reached from
TryTakeItem (Z_01.asm:4432), which TryTakeRoomItem calls with X = $13 - the room
item. And a room item in a dungeon is a treasure chest, which has no price.

## What this measures, and why it is not inference

Three independent observables agree on the same frame, and the third is the one
that matters because it is the only one the game writes for exactly this purpose:

  1. `$00AB` is already `$17` - the room's contents, from the frame the room was
     created, not the frame the chest was opened.
  2. `$00BF` (ObjState+19) and `$0097` (ObjY+19) both go to `$FF` on the change
     frame - the signature at Z_01.asm:4432-4434, with X = $13.
  3. `$04E5` StatusBarMapTrigger pulses `00 -> 01 -> 00`. That byte has exactly
     two references in the entire disassembly: the write at Z_01.asm:4616,
     reachable only through the map slot, and a read-and-clear. Nothing else can
     set it.

The geometry confirms the frame independently. TryTakeRoomItem requires
|LinkX - $83| < 9 and |(LinkY+3) - $97| < 9, and the item sits at ($80, $90) =
(128, 144):

  L3  f9803  LinkX 119 -> |119-128| = 9  rejected
      f9804  LinkX 120 -> |120-128| = 8  accepted   <- $0668 changes here
  L7  f92996 LinkY 150 -> |150+3-144| = 9 rejected
      f92997 LinkY 149 -> |149+3-144| = 8 accepted   <- $0668 changes here

Both are off by one pixel at the boundary, which is what makes it the frame and
not a coincidence.

## Cost

One replay of the run, to the second transition, with a per-frame read only
inside the two windows. About 80 seconds. Run it detached and tail the file.
"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, states/ are repo-relative
del _os, _sys, _pathlib

import sys
import time
from pathlib import Path

from zelda import BizHawk, replay
from zelda.emulator import ROM
from zelda import ram, romdata

# The two frames, from logs/run6_pickups.events.txt at 6-frame scan granularity.
# probe_map_window.py pins them exactly; the geometry in the docstring confirms them.
TRANSITIONS = [(9804, "L3 map bit"), (92997, "L7 map bit")]
WINDOW = 8                  # frames either side to read per frame

# $00AB is the room item, $0010 the level, $00EB the room, $04E5 the map trigger,
# $00BF/$0097 the room-item object's state and Y, $066D rupees, $0668 the byte.
WATCH = {
    0x0010: "level", 0x00AB: "room item id", 0x00EB: "room",
    0x0083: "item X", 0x0097: "item Y", 0x00BF: "item state",
    0x04E5: "map trigger", 0x0668: "$0668", 0x066D: "rupees",
}


def hexs(b: bytes) -> str:
    return " ".join(f"{x:02X}" for x in b)


def main() -> int:
    inputs = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("runs/run6/inputs.txt")
    frames = replay.load_inputs(inputs)
    stop = max(f for f, _ in TRANSITIONS) + WINDOW

    print(f"cartridge : {ROM}")
    print(f"input log : {inputs}  ({len(frames)} frames, stopping at {stop})")
    print(f"replaying, watching {len(WATCH)} bytes per frame inside the two windows\n", flush=True)

    wanted: dict[int, set[int]] = {}
    for f, _ in TRANSITIONS:
        wanted[f] = {f + d for d in range(-WINDOW, WINDOW + 1)}
    marks = sorted(set().union(*wanted.values()))

    seen: dict[int, list[tuple[int, dict[int, int]]]] = {f: [] for f, _ in TRANSITIONS}
    t0 = time.time()
    i = 0
    try:
        with BizHawk(log_name="mapchest.log") as emu:
            # Advance to each mark and read there. Batching has to STOP at a mark:
            # an earlier version batched to the end of each run of identical input
            # and only sampled on a boundary, so a window sitting inside a long
            # held input - f9796..f9812 is entirely inside a 103-frame hold of
            # Right - was never read at all, and the block came back empty.
            def advance_to(target: int) -> None:
                nonlocal i
                while i < target:
                    j = i
                    while j < target and frames[j] == frames[i]:
                        j += 1
                    if j == i:
                        j = i + 1          # never stall on a boundary
                    emu.step(frames[i], j - i)
                    i = j

            for target in marks:
                advance_to(target)
                row = {a: emu.byte(a) for a in WATCH}
                for f, rows in seen.items():
                    if target in wanted[f]:
                        rows.append((target, row))
            advance_to(stop)
            print(f"replayed {stop} frames in {time.time() - t0:.0f}s "
                  f"({stop / (time.time() - t0):.0f} f/s), {len(marks)} frames sampled\n",
                  flush=True)
    except Exception as e:
        print(f"\nDIED after {i} frames ({time.time() - t0:.0f}s): {type(e).__name__}: {e}")
        print("  see logs/mapchest.log", flush=True)
        return 1

    for f, label in TRANSITIONS:
        rows = seen[f]
        print(f"=== {label}: $0668 at f{f} " + "=" * max(4, 52 - len(label)))
        if not rows:
            print(f"  NO DATA - {len(wanted[f])} frames were to be sampled and none were. "
                  f"The probe is broken, not the game.\n")
            continue
        prev = None
        for fr, vals in rows:
            mark = "  <<<" if prev is not None and vals[0x0668] != prev else ""
            prev = vals[0x0668]
            print(f"  f{fr}  level={vals[0x0010]} room=${vals[0x00EB]:02X} "
                  f"item=${vals[0x00AB]:02X} objstate=${vals[0x00BF]:02X} "
                  f"objY=${vals[0x0097]:02X} trigger=${vals[0x04E5]:02X} "
                  f"$0668={vals[0x0668]:02X} rupees=${vals[0x066D]:02X}{mark}")
        print()
        level = rows[0][1][0x0010]
        room = rows[0][1][0x00EB]
        item = rows[0][1][0x00AB]
        # Two independent sources for the same fact: the ROM's static room table and
        # the live RAM room-item byte. They agree, which is what makes the label a
        # reading rather than an assumption.
        try:
            info = romdata.room_info(level, room)
            agree = info["item"] == (item & 0x1F)
            print(f"  ROM room table: level {level} room ${room:02X} holds "
                  f"{info['item_name']} (id ${info['item']:02X}), "
                  f"after_clear={info['item_after_clear']}, monsters={info['monsters']:02X}")
            print(f"  live RAM said ${item:02X} -> static and live agree: {agree}"
                  f"{'' if agree else '   <-- MISMATCH, investigate before trusting the label'}")
        except Exception as e:
            print(f"  (romdata could not read level {level} room ${room:02X}: {e})")
        print()

    print("Reading: $00AB was the room's item from the frame the room was created, the\n"
          "object state/Y went to $FF in the signature at Z_01.asm:4432-4434, and the\n"
          "map trigger pulsed on that same frame. A chest has no price, which is why\n"
          "$066D does not move. See the docstring for the disassembly and the geometry.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
