"""Watch RAM for the moment a major item is acquired.

One contiguous window, read once per frame, which the harness already pays for:
the item flags at $656-$668 plus the counts at $66D-$671. A Triforce piece is a
new bit in $671, so all eight fall out of one comparison, and a heart container is
the high nybble of $66F incrementing.

MAJOR means *does this change what is possible*. Consumables - rupees, small keys,
bomb refills, a heart restored by a fairy or a fountain - are deliberately not
events: they are a budget problem, not a change in the map, and recording them
would mean hundreds of entries per route that nobody would resume from or look at.

Use Tracker.acquired() to get the deltas since the last call. It is deliberately
dumb about *why* an item changed: the game sometimes rewrites a flag, and it is
better to report the observed transition than to guess at intent.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import ram

# Item flags, in RAM order. Value 0 = not held for the boolean ones; SWORD is a
# level (0 none, 1 wood, 2 white, 3 magical) so it moves through several values.
# $656 (B_ITEM) is deliberately NOT here. It is which item is *selected in slot B*,
# not something acquired - it changes every time the bot switches items, and
# including it produced ~20 phantom events on a single run. Found by running the
# tracker against the verified run rather than by reading the address.
ITEM_FLAGS: dict[str, int] = {
    "sword":       ram.SWORD,
    "bombs":       ram.BOMBS,
    "arrows":      ram.ARROWS,
    "bow":         ram.BOW,
    "candle":      ram.CANDLE,
    "whistle":     ram.WHISTLE,
    "bait":        ram.BAIT,          # Data Crystal: "Food in Inventory"
    "potion":      ram.POTION,
    "rod":         ram.ROD,
    "raft":        ram.RAFT,
    "book":        ram.BOOK,
    "ring":        ram.RING,
    "ladder":      ram.LADDER,
    "magic key":   ram.MAGIC_KEY,
    "bracelet":    ram.BRACELET,
    "letter":      ram.LETTER,
    "compass":     ram.COMPASS,
    "map":         ram.MAP,
    "compass L9":  ram.COMPASS_L9,
    "map L9":      ram.MAP_L9,
    "clock":       ram.CLOCK,
}

# Bomb and bait refills are consumables, not acquisitions. Off by default.
COUNT_REFILLS = False

# Report count decreases (bombs spent, bait used) as events. Off by default; see
# TRANSIENT. Useful for a search that wants to know where the bombs went.
REPORT_DROPS = False

# $0667 compass and $0668 map are NOT 0/non-zero flags. Data Crystal's RAM map
# documents both as "One bit per level" - a per-dungeon bitmask, not an inventory
# bit. The verified run's $668 going 0 -> 4 and then 4 -> 0x44 is that: bit 2 is
# level 3's map, and 0x44 adds bit 6, level 7's. They were flagged UNVERIFIED
# until the RAM map explained them; the address was right and the reading was wrong.
# https://datacrystal.tcrf.net/wiki/The_Legend_of_Zelda/RAM_map
PER_LEVEL = {"compass": ram.COMPASS, "map": ram.MAP}

# $0669/$066A are the level-9 compass and map, separate bytes. Tracked, because
# buying the map for Death Mountain is a real acquisition.
PER_LEVEL_L9 = {"compass L9": ram.COMPASS_L9, "map L9": ram.MAP_L9}

# 3-state statuses, not booleans and not counts. Reading $659 as a count produced
# nonsense like "arrows x2" where the byte actually means "Silver Arrow".
STATUS = {
    "sword":  {1: "wooden sword", 2: "white sword", 3: "magical sword"},
    "arrows": {1: "arrow", 2: "silver arrow"},
    "candle": {1: "blue candle", 2: "red candle"},
    "potion": {1: "life potion", 2: "second potion"},
    "ring":   {1: "blue ring", 2: "red ring"},
}

# $065D is bait, but Data Crystal names it "Food in Inventory" - bait is what you
# buy and what a hook takes. Recorded under its own name so the events read well.

# Genuine counts. $0658 is "Number of Bombs"; $065D is "Food in Inventory" (bait).
# Arrows is NOT here - $0659 is a 3-state status (none / arrow / silver arrow).
COUNT_FLAGS = {"bombs", "bait"}

# A decrease in one of these is ordinary play, not an event. An earlier version
# emitted them as "consumed" and a single run produced 33 of them - almost all of
# them bombs being spent in fights - which buried the 8 Triforce pieces and 10
# heart containers that actually matter. A dungeon clock is the same: handed over
# on clearing a room, gone shortly after. Only acquisitions are events.
TRANSIENT = {"bombs", "bait", "clock"}

# The window we snapshot each frame: the item flags plus the four count bytes.
_WINDOW = sorted({*ITEM_FLAGS.values(), ram.RUPEES, ram.KEYS, ram.HEARTS,
                  ram.HEART_FRAC, ram.TRIFORCE})
_LO, _HI = min(_WINDOW), max(_WINDOW) + 1


@dataclass(frozen=True)
class Pickup:
    """One acquisition. `kind` is item | triforce | heart_container."""
    frame: int
    kind: str
    name: str
    detail: str = ""


@dataclass
class Tracker:
    """Feed it the emulator each frame; it returns what was acquired since last time.

    `read` is anything callable as read(addr, length) -> bytes - BizHawk.ram fits
    exactly, so the usual call is tracker.acquired(emu.ram, frame).
    """

    prev: dict[str, int] = field(default_factory=dict)
    events: list[Pickup] = field(default_factory=list)
    started: bool = False
    armed: bool = False

    def arm(self) -> None:
        """Begin comparing. Until this is called, acquired() reports nothing.

        Do not let the first call establish the baseline by accident: at power-on
        the item bytes are 0xFF, and the game clearing them to 0 a few frames
        later reads as every item being *lost* at once. Arm on the first frame the
        game is actually in play.
        """
        self.armed = True
        self.started = False

    def _read(self, read) -> dict[str, int]:
        raw = read(_LO, _HI - _LO)
        v = {name: raw[addr - _LO] for name, addr in ITEM_FLAGS.items()}
        v["rupees"] = raw[ram.RUPEES - _LO]
        v["keys"] = raw[ram.KEYS - _LO]
        v["triforce"] = raw[ram.TRIFORCE - _LO]
        v["hearts"] = raw[ram.HEARTS - _LO]
        return v

    def acquired(self, read, frame: int) -> list[Pickup]:
        if not self.armed:
            return []
        # One RAM read per frame, the same cost the state read already costs.
        cur = self._read(read)
        if not self.started:
            # First call establishes the baseline. Starting mid-run, whatever is
            # already held must NOT be reported as acquired - that would invent
            # events for a run that began before the tracker did.
            self.prev = cur
            self.started = True
            return []
        out: list[Pickup] = []

        # Triforce: a new bit, highest set bit first so the pieces come in order.
        old, new = self.prev["triforce"], cur["triforce"]
        gained = new & ~old
        for i in range(7, -1, -1):
            if gained & (1 << i):
                out.append(Pickup(frame, "triforce", f"Triforce piece {i + 1} of 8",
                                  f"triforce {old:02X} -> {new:02X}"))

        # Heart container: high nybble of $66F is containers - 1.
        oh, nh = self.prev["hearts"] >> 4, cur["hearts"] >> 4
        if nh > oh:
            out.append(Pickup(frame, "heart_container",
                              f"heart container {nh + 1}", f"containers {oh + 1} -> {nh + 1}"))
        elif nh < oh:
            out.append(Pickup(frame, "heart_container", f"heart container LOST",
                              f"containers {oh + 1} -> {nh + 1}"))

        # Per-level bitmasks: each new bit is one dungeon's compass/map.
        for name, addr in {**PER_LEVEL, **PER_LEVEL_L9}.items():
            a, b = self.prev[name], cur[name]
            for i in range(8):
                if (b >> i) & 1 and not (a >> i) & 1:
                    out.append(Pickup(
                        frame, "unverified", f"{name} bit {i + 1} set",
                        f"$0x{addr:02X} {a:02X} -> {b:02X} - not a purchase, "
                        f"no rupees moved; see testing/probe_map_window.py"))

        for name, addr in ITEM_FLAGS.items():
            if name in PER_LEVEL or name in PER_LEVEL_L9:
                continue
            a, b = self.prev[name], cur[name]
            if a == b:
                continue
            if name in STATUS:
                # 3-state: 0 none, 1 first, 2 upgraded. Going up is an acquisition,
                # going down is not one.
                if b > a:
                    out.append(Pickup(frame, "item", STATUS[name].get(b, f"{name} {b}"),
                                      f"$0x{addr:02X} {a} -> {b}"))
            elif name in COUNT_FLAGS:
                if b > a and COUNT_REFILLS:
                    out.append(Pickup(frame, "item", f"{name} x{b}", f"{a} -> {b}"))
                elif b < a and REPORT_DROPS:
                    out.append(Pickup(frame, "consumed", name, f"{a} -> {b}"))
            elif b < a and name not in TRANSIENT:
                # A key item going backwards is a real observation - report it
                # rather than dropping it, but do not call it a pickup.
                out.append(Pickup(frame, "lost", name, f"$0x{addr:02X} {a} -> {b}"))
            else:
                out.append(Pickup(frame, "item", name, f"$0x{addr:02X} {a} -> {b}"))

        self.prev = cur
        self.events.extend(out)
        return out

    def to_events(self) -> list[tuple[int, str]]:
        """[(frame, text)] shaped for emu.note() - the overlay splits on ||."""
        return [(p.frame, f"PICKUP||{p.name}||{p.kind}: {p.detail}") for p in self.events]

    def summary(self) -> str:
        by_kind: dict[str, int] = {}
        for p in self.events:
            by_kind[p.kind] = by_kind.get(p.kind, 0) + 1
        return ", ".join(f"{v} {k}" for k, v in sorted(by_kind.items())) or "nothing"
