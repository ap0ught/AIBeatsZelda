"""Read dungeon room data straight from the ROM (Data Crystal ROM map, verified against play).

Levels 1-6 share one 128-room grid; levels 7-9 share another. Per room, one byte each in:
  doors N/S + outer colour, doors E/W + inner colour, monsters, room type, floor item, special.
Door codes (decoded 2026-09-11 against rooms the bot had walked): 0 open, 1 wall, 4 bombable,
5 locked, 7 shutter (opens when the room is cleared / boss dead).
Floor item id 0x00 is bombs; special 0x07 means the item appears only once the room is cleared.
"""
from __future__ import annotations

from . import profile as _profile

DOOR = {0: "open", 1: "wall", 2: "door2", 3: "door3", 4: "bombable", 5: "locked", 6: "door6", 7: "shutter"}
ITEMS = {0x00: "bombs", 0x16: "compass", 0x17: "map", 0x19: "key", 0x1A: "heart container", 0x1B: "triforce",
         0x03: "none", 0x0C: "raft", 0x0D: "ladder", 0x21: "clock", 0x22: "heart"}

def rom() -> bytes:
    """Cartridge bytes for the currently selected cartridge.

    This was a bare module global `_rom`, assigned once and never invalidated, keyed on
    nothing. It is now the profile's md5-keyed cache, so a second cartridge in the same
    process gets its own bytes and neither can serve the other's. See issue #9.
    """
    return _profile.rom_bytes()


def room_info(level: int, room: int) -> dict:
    g = _profile.active().geometry
    base = g.room_tables if level <= 6 else g.room_tables_l7_9   # levels 7-9 tables follow
    r = rom()
    h = _profile.HEADER
    ns = r[h + base + room]
    ew = r[h + base + 0x80 + room]
    mon = r[h + base + 0x100 + room]
    rtype = r[h + base + 0x180 + room]
    item = r[h + base + 0x200 + room]
    special = r[h + base + 0x280 + room]
    return {
        "room": room,
        "N": DOOR[ns >> 5], "S": DOOR[(ns >> 2) & 7],
        "W": DOOR[ew >> 5], "E": DOOR[(ew >> 2) & 7],
        "monsters": mon, "type": rtype,
        "item": item & 0x1F, "item_name": ITEMS.get(item & 0x1F, f"item {item & 0x1F:02X}"),
        "item_flags": item >> 5, "special": special,
        "item_after_clear": bool(special & 0x04),
    }


def doors(level: int, room: int) -> dict:
    i = room_info(level, room)
    return {d: i[d] for d in ("N", "S", "E", "W")}


if __name__ == "__main__":
    for rm in (0x7C, 0x7B, 0x6B, 0x5B, 0x4B, 0x4C, 0x4D, 0x3D, 0x5C, 0x5D, 0x59, 0x5A, 0x4A, 0x49):
        i = room_info(3, rm)
        print(f"{rm:02X}: N={i['N']:8s} S={i['S']:8s} W={i['W']:8s} E={i['E']:8s} item={i['item_name']:16s}"
              f"{' (after clear)' if i['item_after_clear'] else ''} monsters={i['monsters']:02x}")
