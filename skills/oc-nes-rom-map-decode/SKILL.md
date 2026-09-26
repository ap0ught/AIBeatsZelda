---
name: oc-nes-rom-map-decode
description: Decode an NES game's map, rooms, tiles and item flags straight from the cartridge - no disassembly, no external map - then cross-validate the static tables against live RAM from an emulator. Worked example is The Legend of Zelda (NES) USA Rev 1: the iNES header, the overworld screen/column/square table chain at specific PRG offsets, the 32x22 tile grid, the dungeon room tables, and the runtime RAM map for game mode, level, room, position, hearts, inventory and Triforce flags. Use when reverse-engineering an NES ROM's world map, building a path planner or search agent for an NES game, finding where a game keeps its map tables, or reading a live game's memory map.
license: MIT
metadata:
  tags: nes, rom, ines, disassembly, reverse-engineering, zelda, overworld, tilemap, pathfinding, ram, memory-map, bizhawk, lua, decoding, game-hacking
  category: reverse-engineering
  requires_toolsets: terminal
---

# Decoding an NES map from the cartridge

You can get a usable world model for an NES game without a disassembly and
without a third-party map, by reading the ROM's own tables and then checking them
against live RAM. Worked example throughout: *The Legend of Zelda* (NES) USA
Rev 1, md5 `614fb3085826e62f3be3a3fe0b931689`.

Reference implementation: `~/code/games/aibeatszelda/src/zelda/owmap.py`
(overworld), `zelda/romdata.py` (dungeon rooms), `zelda/ram.py` (live memory
map), `zelda/owroute.py` (path planner over the decoded map).

## Sources, and how to actually read them

- **`aldonunez/zelda1-disassembly`** — the community disassembly. The offsets
  below are its symbols. `src/bins.xml` is the fastest cross-check: it lists each
  blob's ROM offset and length, so you can confirm an address without reading
  assembly. `RoomLayoutsOW.dat` is at decimal 87064, i.e. `0x15418`.
- **Data Crystal, `The_Legend_of_Zelda/ROM_map`** — corroborates the table
  addresses and *names* them, which the disassembly does not do in one place. It
  is Cloudflare-gated: scripted requests get 403 with a JS challenge, including
  the MediaWiki `api.php`. Use the Wayback Machine:
  `http://web.archive.org/web/<timestamp>/<url>`. Cite the archived copy, because
  anyone following the link from a script will otherwise just get a 403.

Two things worth knowing about Data Crystal's tables, both of which cost me an
error:

- **Its address ranges are inclusive.** `1697C..169B3` is 56 bytes, not 55 —
  `0x169B3 - 0x1697C = 0x37`, plus the end byte. Cross-check any size against
  code before "correcting" it.
- **Tables are three columns: start, end, description.** Naive row-pairing
  yields start→end, not start→description.

It also confirms bit layouts outright — e.g. the dungeon door byte is documented
as `%NNNS SSPP` (north door bits 7–5, south 4–2, palette low), which is exactly
what you would otherwise have to infer from the code.

| table | range | what Data Crystal calls it |
|---|---|---|
| `15418..15BD7` | 1984 B | "Overworld screens. Each byte refers to 1 of 150 (256 addressable) columns." |
| `1697C..169B3` | 56 B | "Primary square table: squares specified as first of four tiles" |
| `18400..1847F` | 128 B | "Overworld screen data Table 1. `%HHHH ZWPP`" |
| `18700..1877F` | 128 B | "N / S & outer color for Levels 1 through 6. `%NNNS SSPP`" |
| `19D0F..19D2E` | 32 B | "Column directory pointer table: 16-bit pointers to the start of each of 16 column tables." |

The 150/256 column note matters: it is why the room→uid byte is masked with
`0x7F`, and why a 128-entry uid space is addressable through 150 layouts.


## Pin the ROM first

Everything below is revision-specific. Collections hold several dumps differing
only in filename, and a wrong revision does not fail loudly — it decodes into
something plausible and subtly wrong. Check the hash before writing a single
offset:

```
md5  614fb3085826e62f3be3a3fe0b931689   Legend of Zelda, The (USA) (Rev 1)
```

## Strip the iNES header and get PRG

An `.nes` file is a 16-byte header followed by one or more 16 KB PRG banks (and
optionally CHR). Almost every table offset quoted in documentation is a **PRG
offset**, so subtract the header before indexing:

```python
prg = rom_bytes[16:]      # everything below is an index into this
```

If the file is 131,088 bytes: 16 header + 8 × 16,384 = 131,088. That size is a
useful sanity check, and a ROM that is *not* a multiple of 1024 past the header
usually means a non-standard header — BizHawk will say so at boot.

## The overworld: a four-step table chain

The overworld is 128 screens in an 8×16 grid. Reaching a screen's tile grid from
its id is four indirections, and you need all four.

**1. Screen id → layout uid.** Six 0x80-byte tables based at PRG `0x18400`; the
room-to-uid map is **table 3**, which is `0x18400 + 3*0x80 = 0x18580` — *not*
`0x18400` itself, which is table 0 ("Overworld screen data Table 1"). Mask off
the high bit:

```python
lb = 0x18400
tables = [prg[lb + k*0x80 : lb + (k+1)*0x80] for k in range(6)]
uid = tables[3][room] & 0x7F        # byte lives at 0x18580
```

**2. uid → 16 column descriptors.** `RoomLayoutsOW` at PRG `0x15418`, 16 bytes per
uid, one byte per column:

```python
cols = prg[0x15418 + uid*16 : 0x15418 + uid*16 + 16]
```

**3. Column descriptor → 11 square codes.** This is the fiddly one. A descriptor
is an index into a *shared compressed* column table, addressed through a
directory, and the squares are run-length coded with two independent flag bits:

- The **column directory** at PRG `0x19D0F` holds 16 little-endian 16-bit
  pointers. The descriptor's high nybble selects the pointer; subtract `0x8000`
  to get a PRG index.
- From there, walk forward until you have seen `desc & 0x0F` **terminator bytes**
  — bytes with bit `0x80` set.
- Then read squares: each byte's low 6 bits are the square code, and bit `0x40`
  toggles a repeat flag. A repeat byte that lands on repeat skips itself; the
  alternation is a two-state toggle, not a run length.

```python
col_dir = [0x14000 + ((prg[0x19D0F + 2*k] | prg[0x19D10 + 2*k] << 8) - 0x8000)
           for k in range(16)]
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
```

**4. Square code → 4 tile ids.** Two tables sit either side of PRG `0x16970`: the
*primary* table at `0x1697C` (56 bytes) and the *secondary* at `0x169A8` (64
bytes). Codes ≥ `0x10` are *primary*: four consecutive tiles from `prim[code]`.
Codes < `0x10` are *secondary*: four bytes read directly at
`sec[code*4 : code*4+4]`. Order is TL, BL, TR, BR — column major, which surprises
people.

```python
prim = prg[0x16970 + 12 : 0x16970 + 12 + 0x38]              # 0x1697C, 56 bytes
sec  = prg[0x16970 + 12 + 0x38 : 0x16970 + 12 + 0x38 + 64]  # 0x169A8, 64 bytes
```

That yields **16 squares × 11 rows × 8 px = a 32 × 22 grid of 8 px tiles per
screen**, which is exactly what the running game hands you, so the two are
directly comparable. See "Validate against live RAM" — that comparability is the
point and you should exploit it.

## Secrets that are still shut

A secret that has not been opened is drawn as ordinary scenery, so a naive decode
makes bombable walls and burnable trees look like rock. Override the four corner
tiles per secret type (TL, BL, TR, BR):

```
0x26 push rock  -> C8 C9 CA CB
0x27 bomb wall  -> D8 D9 DA DB
0x28 burn tree  -> C4 C5 C6 C7
0x29 push grave -> BC BD BE BF
```

This matters for a planner: without it, every wall looks solid and the search
concludes the room is impassable.

## Dungeon rooms: six parallel 128-byte planes

Levels 1–6 share one 128-room grid, levels 7–9 another, based at PRG `0x18700`
(plus `0x300` for 7–9). Each room's properties live in a separate plane, 128 bytes
each:

| offset | plane |
|---|---|
| `+0x000` | doors N/S + outer colour |
| `+0x080` | doors E/W + inner colour |
| `+0x100` | monsters |
| `+0x180` | room type |
| `+0x200` | floor item |
| `+0x280` | special |

Door codes: `0` open, `1` wall, `4` bombable, `5` locked, `7` shutter (opens when
the room is cleared or the boss dies). The N/S and E/W planes pack a door code in
bits 5–7 and another in bits 2–4, so one byte carries two doors plus a colour.

Floor item `0x00` is bombs. Special `0x07` means the item only appears once the
room is cleared.

## Item ids (shared vocabulary)

```
0 bombs   1 wood sword   2 white sword   3 magic sword   4 bait
5 recorder  6 blue candle  7 red candle  8 arrows  9 silver arrows
A bow    B magic key     C raft          D ladder
12 blue ring  13 red ring  14 bracelet  15 letter
18 rupee  19 key  1A heart container  1C magic shield  1D boomerang
1F blue potion  20 red potion  22 heart  23 fairy
```

Cave types share the high nibble: `0x21`/`0x22`/`0x23` are the 30-, 100- and
10-rupee secret caves, whose "old man" hands over money for nothing — free income
a route planner should know about. `0x1D`–`0x20` are shops, and the wares are
*not* in the object table, only the shopkeeper, so a planner must model shop
stock separately.

## The live RAM map

Static tables tell you the world. RAM tells you the state. Both are needed, and
the RAM side is what makes a planner verifiable. Addresses are stable for this
game and are the kind of thing to re-derive rather than trust:

| addr | meaning |
|---|---|
| `$10` | level — 0 overworld, 1–9 dungeons |
| `$12` | game mode (`05` normal play, `0B` grotto, `02` transition) |
| `$13` | submode / routine index |
| `$15` | frame counter |
| `$EB` | room — high nybble row, low nybble column |
| `$70` / `$84` | Link x / y |
| `$98` | facing — 1 R, 2 L, 4 D, 8 U (a bitmask) |
| `$66F` | high nybble = containers − 1, low nybble = full hearts |
| `$66D` | rupees |
| `$66E` | keys |
| `$671` | Triforce — **bit flags, one per dungeon** |
| `$656` | **selected B item slot — a cursor, never an acquisition** |
| `$657`–`0x666` | inventory, but see the encodings below (sword, bombs, arrows, candle, …) |
| `$67C` | bomb capacity |
| `$485` | enemy HP, high nybble, 12-slot array |
| `$71`/`$85`/`$350` | enemy x / y / type, 12-slot parallel arrays |
| `$34F` | object types, 12-slot (object `0x2F` is the overworld fairy) |

Two encodings to respect:

- **Hearts are a packed nybble pair.** `$66F` high is *containers minus one* and
  low is current hearts. Reading it as a byte gives nonsense.
- **The Triforce is a bitmask.** Progression and "have all eight" are one AND,
  which is what makes a hard gate on the final dungeon a one-line check.
- **Facing is a bitmask, not an enum**, so "up" is `x & 8`.

### The inventory bytes are not all the same kind

This is where a Zelda tracker goes wrong, and it cost me three real bugs that a
synthetic unit test passed clean through. The run of `$656`–`$666` mixes four
different encodings under names that look alike:

| addr | what it is | encoding |
|---|---|---|
| `$656` | selected B item **slot** | a cursor — changes every item switch; **not** an acquisition |
| `$657` | sword | 3-state: none / wooden / white / magical |
| `$658` | bombs | a real **count** — up on refill, down when spent |
| `$659` | arrows | 3-state: none / arrow / **silver** arrow — *not* a count |
| `$65B` | candle | 3-state: none / blue / red |
| `$65D` | bait | a real count ("Food in Inventory" in Data Crystal) |
| `$662` | ring | 3-state: none / blue / red |
| `$667` | compass | **one bit per level** — not 0/1 |
| `$668` | map | **one bit per level** — not 0/1 |
| `$669`/`$66A` | compass/map for level 9 | separate bytes |
| `$66C` | clock | flag, but **transient** — given on clearing a room, gone shortly after |

Consequences worth internalising:

- **A `0 -> 4` transition is not a bug.** Per-level bitmasks make `4` mean "level
  3's map" and `0x44` mean "levels 3 and 7". I filed that as a suspected wrong
  address before reading the map; the address was right and my reading was wrong.
  Reach for the RAM map before you suspect the address.
- **Status bytes and count bytes live adjacently.** `$658` bombs and `$659`
  arrows are one apart and one is a count while the other is an enum. Treating
  arrows as a count yields events like "arrows x2" where the byte actually means
  *Silver Arrow*.
- **A decrease is not an event.** With counts tracked, one run emitted 33
  "consumed" events — nearly all bombs spent in ordinary fights — which buried
  the 8 Triforce pieces that actually mattered. Mark transient items and report
  acquisitions only; gate drops behind a flag for searches that want them.
- **Absence is evidence, and it has to be checked.** A bot run with no ring,
  bracelet, rod, book or magic key is not a detection failure: those are the
  Treasure Dungeon items, behind the cursor sequence the bot does not perform. So
  distinguish "Ganon-capable clear" from "100% run" explicitly.

### Authoritative references for this game

These two Data Crystal pages are the reference this skill works from. They are the
user's own links and they are the authority for every encoding above — when a
byte disagrees with a guess, these pages win, and when they contradict the
observed data, the observed data gets reported rather than the page being quietly
stretched to fit.

- **RAM map** — <https://datacrystal.tcrf.net/wiki/The_Legend_of_Zelda/RAM_map>
- **Notes** (text pointers, shop item IDs, enemy drop table, tile IDs) —
  <https://datacrystal.tcrf.net/wiki/The_Legend_of_Zelda/Notes>

Both are Cloudflare-gated to scripted requests and will return nothing to a tool.
Read them through an archive.org snapshot when there is no browser:

```bash
curl -s "http://archive.org/wayback/available?url=datacrystal.tcrf.net/wiki/<page>"
curl -sL "http://web.archive.org/web/<timestamp>/<url>"
```

Known-good snapshots: RAM map `20251116061046`, Notes `20250825035708`.

**Verify a page's claim against the run before you ship code that depends on
it.** The RAM map says `$0668` is the map, one bit per level, and that part is
right — but the bits in the verified run appear with *zero* rupee movement, which
means they are not a bought map. A documentation page tells you the encoding; it
does not tell you what a particular run did. Those are different questions and
conflating them produces events that say "map for level 3" when no map was bought.

The Notes page's enemy drop table independently confirms the drop IDs that route
planners hardcode: `$22=Heart`, `$23=Fairy`, `$24=Glitched (Fairy)`, `$3F=Glitched
Items`. Its shop-item ID list is what tells you `$669`/`$66A` are the level-9
compass and map rather than more per-level bits.

Reading RAM over a BizHawk Lua bridge is a single command — `mainmemory.readbyte`
or BizHawk's `memorysavestate` helpers — and 2 KB of work RAM in one go is cheap
enough to snapshot every frame.

## Validate against live RAM — do not skip this

The static decode is a hypothesis until it matches the running game. The cheap,
decisive test: dump the live tile grid for every screen the agent has actually
walked, and diff it against the decode, cell by cell.

```python
seen = [[raw[r*32 + c] for c in range(32)] for r in range(22)]   # from RAM
mine = cells(room)                                               # from the ROM
bad  = [(r, c, seen[r][c], mine[r][c])
        for r in range(22) for c in range(32) if seen[r][c] != mine[r][c]]
```

Two immediate payoffs. It turns "I think the run-length toggle is right" into a
count. And it produces `knowledge/rooms.json` — a record of what was actually
observed, which is the artefact you re-check against after any change to the
decoder.

Store the live grid as a hex string keyed by screen id; it costs 1408 bytes a
screen and makes regressions obvious.

**Also validate semantics, not just bytes.** Door code `7` was decoded as
"shutter" by playing rooms, not by reading them. Any value read out of a table
should have at least one behavioural test.

## Then build the planner, and price it before you search

Decoded map in hand, the useful next step is a router: a weighted shortest path
over screen adjacency, with the current unlocks (raft, ladder, whistle) selecting
which transitions are legal. Cost it on the map, not in the emulator — pure
planning arithmetic prices a candidate route in seconds, which is the only
affordable way to compare orders.

Then model the **dependency graph** explicitly. For this game it is short enough
to write down, and it is what makes some routes impossible rather than slow:

```
L3 → raft, bombs        L4 → needs raft → gives ladder
L1 → bow                L5 → needs ladder → gives whistle
L6 → needs bow+arrows   L7 → needs whistle+bait+ladder
L8 → needs candle+ladder
L9 → needs all eight dungeons + bow + arrows + bombs
White Sword needs 5 hearts; Magic Sword needs 12
```

A legal order is a topological sort of that graph, not a permutation. And the
graph is not sufficient on its own: **rupee and key budgets bind too**, and a
route that satisfies every prerequisite can still fail on money. Model both, and
expect the model — not the dependency graph — to be what rejects a candidate.

An **open question worth flagging rather than assuming**: whether the rupee byte
`$66D` is the *displayed* number or an internal encoded value was never settled.
The shop sticker says 200 and a route model priced the candle at 60, which is the
sort of gap that means the counter is compressed. Settle it by forcing a known
pickup and diffing the byte against the HUD — two minutes with an emulator — or
leave it labelled unknown rather than quietly picking a reading.

## Method, in order

1. Pin the ROM by hash.
2. Skip the 16-byte header; work in PRG indices.
3. Find one table you can *check visually* — the overworld's screen-id → uid map
   is a good first because you can print a screen's layout and compare it to a
   screenshot.
4. Follow indirections one at a time, decoding each in isolation and testing it
   before building the next layer.
5. Reach a representation that matches what the running game exposes. That
   comparability is the whole prize.
6. Diff against live RAM for every screen you can reach. Fix the decode until it
   is exact.
7. Build the router, then the dependency model, then search.
8. Write down which claims are corroborated by artefacts and which are inference.

## Traps

- Documentation offsets are usually **PRG** offsets. Off by `0x10` and you get
  plausible garbage.
- Room ids are **not** linear grid coordinates. `$EB` packs row in the high
  nybble and column in the low one; the ROM's uid table adds another indirection.
- Shut secrets decode as scenery (see above) and will make a room look sealed.
- Packed fields hide in plain sight: hearts are two nybbles in one byte, doors are
  two codes in one byte, facing is a bitmask.
- The same byte means different things at different addresses across games, and
  across *revisions* of one game. Re-derive; do not port.
- A decoded map tells you what is *there*, never what is *reachable*. Locks,
  one-way drops and boss gates are behavioural and belong in the model.
