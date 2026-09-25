"""The whole overworld, decoded from the cartridge: every screen as the same 22 x 32 grid of 8 px tile ids that
read_cells() returns from RAM, plus what each screen hides (cave type, shop wares, secrets, Armos items).

This is reading the ROM file on disk, not the running game: planning knowledge, like a map on the table. The
decoder was worked out against the disassembly (RoomLayoutsOW at PRG $15418, the column directory at $19D0F,
primary/secondary square tables at $1697C) and is validated against every screen the bot has actually walked
(knowledge/rooms.json) by check()."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent
ROM_PATH = HARNESS.parent / "BizHawk-2.11.1-win-x64" / "Legend of Zelda, The (USA) (Rev 1).nes"

ITEM = {0: 'bombs', 1: 'wood sword', 2: 'white sword', 3: 'magic sword', 4: 'bait', 5: 'recorder', 6: 'blue candle',
        7: 'red candle', 8: 'arrows', 9: 'silver arrows', 0xA: 'bow', 0xB: 'magic key', 0xC: 'raft', 0xD: 'ladder',
        0x12: 'blue ring', 0x13: 'red ring', 0x14: 'bracelet', 0x15: 'letter', 0x18: 'rupee', 0x19: 'key',
        0x1A: 'heart container', 0x1C: 'magic shield', 0x1D: 'boomerang', 0x1F: 'blue potion', 0x20: 'red potion',
        0x22: 'heart', 0x3F: '-'}
CAVE = {0x10: 'wood sword', 0x11: 'heart container', 0x12: 'white sword', 0x13: 'magic sword', 0x14: 'warp',
        0x15: 'hint', 0x16: 'gamble', 0x17: 'door repair', 0x18: 'letter', 0x19: 'hint', 0x1A: 'potion shop',
        0x1B: 'pay hint', 0x1C: 'pay hint', 0x1D: 'shop', 0x1E: 'shop', 0x1F: 'shop', 0x20: 'shop',
        0x21: 'secret 30', 0x22: 'secret 100', 0x23: 'secret 10'}
SPECIAL = {0x26: 'push rock', 0x27: 'bomb wall', 0x28: 'burn tree', 0x29: 'push grave'}
# how a shut secret is drawn (TL, BL, TR, BR): boulder, rock face, tree; measured against walked screens
CLOSED = {0x26: (0xC8, 0xC9, 0xCA, 0xCB), 0x27: (0xD8, 0xD9, 0xDA, 0xDB), 0x28: (0xC4, 0xC5, 0xC6, 0xC7),
          0x29: (0xBC, 0xBD, 0xBE, 0xBF)}


@lru_cache(maxsize=1)
def _prg() -> bytes:
    return ROM_PATH.read_bytes()[16:]


def _tables():
    prg = _prg()
    lb = 0x18400
    return [prg[lb + k * 0x80: lb + (k + 1) * 0x80] for k in range(6)]


def _column(desc: int) -> list[int]:
    prg = _prg()
    col_dir = [0x14000 + ((prg[0x19D0F + 2 * k] | prg[0x19D10 + 2 * k] << 8) - 0x8000) for k in range(16)]
    base, idx = col_dir[desc >> 4], desc & 0x0F
    p = base - 1
    while True:
        p += 1
        if prg[p] & 0x80:
            idx -= 1
            if idx < 0:
                break
    sq, rep = [], 0
    while len(sq) < 11:
        b = prg[p]
        sq.append(b & 0x3F)
        if b & 0x40:
            rep ^= 1
            if rep:
                continue
        p += 1
    return sq


@lru_cache(maxsize=None)
def squares(room: int) -> tuple:
    """16 columns x 11 square codes (16 px squares) for an overworld screen."""
    prg = _prg()
    uid = _tables()[3][room] & 0x7F
    cols = prg[0x15418 + uid * 16: 0x15418 + uid * 16 + 16]
    return tuple(tuple(_column(c)) for c in cols)


def _square_tiles(s: int) -> list[int]:
    prg = _prg()
    prim = prg[0x16970 + 12: 0x16970 + 12 + 0x38]
    sec = prg[0x16970 + 12 + 0x38: 0x16970 + 12 + 0x38 + 64]
    if s >= 0x10:
        p = prim[s]
        return [p, p + 1, p + 2, p + 3]          # TL, BL, TR, BR
    return list(sec[s * 4: s * 4 + 4])


@lru_cache(maxsize=None)
def cells(room: int) -> tuple:
    """cells[row][col] of 8 px tile ids, as read_cells() would return on that screen (secrets still closed)."""
    g = [[0] * 32 for _ in range(22)]
    for sx, col in enumerate(squares(room)):
        for sy, s in enumerate(col):
            if s in CLOSED:                       # a secret still shut looks like the scenery around it
                tl, bl, tr, br = CLOSED[s]
            else:
                tl, bl, tr, br = _square_tiles(s)
            g[2 * sy][2 * sx], g[2 * sy + 1][2 * sx] = tl, bl
            g[2 * sy][2 * sx + 1], g[2 * sy + 1][2 * sx + 1] = tr, br
    return tuple(tuple(r) for r in g)


def info(room: int, quest: int = 1) -> dict:
    """What the screen hides in the given quest: cave kind, wares, the secret that opens it and where."""
    a, b, c, d, e, f = _tables()
    prg = _prg()
    q = f[room] >> 6                                  # 0 both quests, 1 first only, 2 second only
    cave = b[room] >> 2
    out = {"room": room, "cave": None, "kind": None, "wares": [], "secret": None, "armos_item_x": None}
    armos = dict(zip(prg[0x10CB2:0x10CB9], prg[0x10CB9:0x10CC0]))
    if room in armos:
        out["armos_item_x"] = armos[room]
    if q not in (0, quest):
        return out
    out["cave"] = cave
    out["kind"] = CAVE.get(cave, f"level {cave}" if 0 < cave < 10 else None)
    if 0x1A <= cave <= 0x20:
        i = cave - 0x10
        items, prices = e[i * 3: i * 3 + 3], e[60 + i * 3: 60 + i * 3 + 3]
        out["wares"] = [(ITEM.get(x & 0x3F, hex(x & 0x3F)), p) for x, p in zip(items, prices) if x & 0x3F != 0x3F]
    for cx, col in enumerate(squares(room)):
        for ry, s in enumerate(col):
            if s in SPECIAL:
                out["secret"] = (SPECIAL[s], cx * 16, ry * 16 + 64)
    return out


def check() -> tuple[int, int, list]:
    """Compare the decoded screens with every overworld screen the bot has walked. Returns (screens, exact, diffs)."""
    rooms = json.loads((HARNESS / "knowledge" / "rooms.json").read_text(encoding="utf-8"))
    n = exact = 0
    diffs = []
    for key, v in rooms.items():
        if key.startswith("L") or len(v.get("cells", "")) != 1408:
            continue
        room = int(key, 16)
        raw = bytes.fromhex(v["cells"])
        seen = [[raw[r * 32 + c] for c in range(32)] for r in range(22)]
        mine = cells(room)
        bad = [(r, c, seen[r][c], mine[r][c]) for r in range(22) for c in range(32) if seen[r][c] != mine[r][c]]
        n += 1
        if not bad:
            exact += 1
        else:
            diffs.append((key, len(bad), bad[:4]))
    return n, exact, diffs


if __name__ == "__main__":
    n, exact, diffs = check()
    print(f"{n} walked overworld screens, {exact} decode exactly")
    for key, k, sample in diffs[:20]:
        print(f"   {key}: {k} cells differ, e.g. " + ", ".join(f"(r{r},c{c}) seen {a:02x} decoded {b:02x}" for r, c, a, b in sample))
