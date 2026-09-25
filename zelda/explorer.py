"""Screen-graph exploration: find a route across overworld screens to a target room.

Nodes are (room, entry_edge). Expanding a node means actually standing there (from a savestate),
reading the map, and walking out of each exit to see where it leads. A* on room coordinates keeps
the search pointed at the target. Everything discovered is cached to knowledge/rooms.json.
"""
from __future__ import annotations

import heapq
import json
from pathlib import Path

from .emulator import BizHawk, State, HARNESS_DIR
from .overworld import Navigator, NavError, LinkDied, read_cells, read_enemies, read_room_item, enemy_name, plan, EDGE_GOALS, DOOR_GOALS, snap
from . import ram

ROOMS_PATH = HARNESS_DIR / "knowledge" / "rooms.json"
OPPOSITE = {"Left": "Right", "Right": "Left", "Up": "Down", "Down": "Up"}


def room_xy(room: int) -> tuple[int, int]:
    return room & 0x0F, room >> 4


class Explorer:
    def __init__(self, emu: BizHawk, nav: Navigator, log=print):
        self.emu, self.nav, self.log = emu, nav, log
        self.level = 0
        self.rooms: dict = {}
        if ROOMS_PATH.exists():
            self.rooms = json.loads(ROOMS_PATH.read_text())

    def key(self, room: int) -> str:
        return f"L{self.level}_{room:02x}" if self.level else f"{room:02x}"

    def _remember(self, room: int, cells) -> None:
        key = self.key(room)
        if key not in self.rooms:
            self.rooms[key] = {"cells": "".join(f"{cells[r][c]:02x}" for r in range(22) for c in range(32)), "exits": {}}
            ROOMS_PATH.parent.mkdir(parents=True, exist_ok=True)
            ROOMS_PATH.write_text(json.dumps(self.rooms))

    def _remember_exit(self, room: int, entry: str, d: str, result) -> None:
        self.rooms[self.key(room)]["exits"][f"{entry}:{d}"] = result
        ROOMS_PATH.write_text(json.dumps(self.rooms))

    def _exit_with_force(self, d: str):
        """Try the exit; if the door won't open and enemies are present, it's probably a shutter:
        clear the room and try once more."""
        emu, nav = self.emu, self.nav
        import random
        from .combat import Fighter
        for attempt in range(6):
            if attempt:
                # same state + same inputs = same death. A random pause shifts the game's RNG.
                delay = random.Random(attempt * 7919 + emu.state().frame).randint(4, 70)
                emu.note(f"Retry {attempt}: waiting {delay} frames first so the enemies roll different moves")
                emu.wait(delay)
            try:
                if attempt == 3 and read_enemies(emu):
                    emu.note("Dodging keeps failing here. Trying to kill everything first (drops may give hearts)")
                    Fighter(nav).clear_room()
                return nav.exit_screen(d)
            except LinkDied:
                if attempt == 5:
                    raise
                emu.load(self._retry_state); emu.wait(2)
            except NavError as e:
                if "did not open" not in str(e) or not read_enemies(emu):
                    raise
                emu.note(f"The {d} door is shut and there are enemies here: a shutter door. Clearing the room first")
                from .combat import Fighter
                if not Fighter(nav).clear_room():
                    raise NavError(f"couldn't clear the room to open the {d} door")
                return nav.exit_screen(d)

    def route(self, target: int | None, start_state: str, max_nodes: int = 60) -> list[str]:
        """Return the list of exit directions from the start state to the target room.
        target=None explores everything reachable (up to max_nodes) and returns []."""
        emu, nav = self.emu, self.nav
        s = emu.load(start_state); s = emu.wait(2)
        self.level = s.level
        start = (s.room, "start")
        tx, ty = room_xy(target if target is not None else s.room)

        def h(room):
            x, y = room_xy(room)
            return abs(x - tx) + abs(y - ty)

        states = {start: start_state}
        came: dict = {start: None}
        g = {start: 0}
        pq = [(h(s.room), 0, start)]
        seen = set()
        if target is None:
            emu.note(f"EXPLORING everything reachable from room {s.room:02X}" + (f" in level {s.level}" if s.level else ""))
        else:
            emu.note(f"EXPLORING for room {target:02X}. Start room {s.room:02X}, straight-line distance {h(s.room)} screens")
        while pq and len(seen) < max_nodes:
            _, cost, node = heapq.heappop(pq)
            if node in seen:
                continue
            seen.add(node)
            room, entry = node
            if target is not None and room == target:
                path = []
                while came[node] is not None:
                    node, d = came[node]
                    path.append(d)
                emu.note(f"ROUTE FOUND: {' -> '.join(reversed(path))} ({len(path)} screens)")
                return path[::-1]
            s = emu.load(states[node]); s = emu.wait(2)
            cells = read_cells(emu)
            self._remember(room, cells)
            ens = read_enemies(emu)
            self.rooms[self.key(room)]["enemies"] = [[e[1], e[2], e[3], e[4]] for e in ens]
            emu.note(f"Expanding room {room:02X} (entered from {entry})"
                     + (f": {len(ens)} enemies here: " + ", ".join(enemy_name(e[1]) for e in ens) if ens else ": no enemies"))
            item = read_room_item(emu)
            if item is not None:
                self.rooms[self.key(room)]["item"] = list(item)
                try:
                    if ens:
                        from .combat import Fighter
                        s = Fighter(nav).grab_key_by_dodging() or s
                    else:
                        s = nav.grab_room_item() or s
                    if read_room_item(emu) is None:
                        name = f"explore_L{self.level}_{room:02x}_{entry}_item"
                        emu.save(name)
                        states[node] = name
                        cells = read_cells(emu)
                except LinkDied:
                    emu.note("Died going for the item; leaving it")
                s = emu.load(states[node]); s = emu.wait(2)
            for d in ("Left", "Right", "Up", "Down"):
                if d == entry:
                    continue
                cached = self.rooms[self.key(room)]["exits"].get(f"{entry}:{d}")
                if cached is None:
                    goals = DOOR_GOALS if self.level else EDGE_GOALS
                    if plan(cells, nav.kb, (s.x, s.y), goals[d], optimistic=True) is None:
                        continue        # situational: do not cache, the bot keeps improving
                    emu.load(states[node]); emu.wait(2)
                    self._retry_state = states[node]
                    try:
                        s2 = self._exit_with_force(d)
                    except LinkDied as e:
                        emu.note(f"Exit {d} from {room:02X}: Link died trying. Not caching that as impossible, just unlucky")
                        continue
                    except NavError as e:
                        emu.note(f"Exit {d} from {room:02X} failed: {e}")
                        continue        # situational failure; not cached

                    if s2.mode != ram.MODE_NORMAL or s2.level != self.level:
                        continue
                    frames = s2.frame - s.frame
                    cached = {"ok": True, "room": s2.room, "frames": frames, "x": s2.x, "y": s2.y}
                    self._remember_exit(room, entry, d, cached)
                    name = f"explore_L{self.level}_{s2.room:02x}_{OPPOSITE[d]}"
                    emu.save(name)
                    states[(s2.room, OPPOSITE[d])] = name
                elif cached["ok"] and (cached["room"], OPPOSITE[d]) not in states:
                    # known from a previous session but no savestate this session: walk it again
                    emu.load(states[node]); emu.wait(2)
                    try:
                        s2 = nav.exit_screen(d)
                    except (NavError, LinkDied):
                        continue
                    if s2.mode != ram.MODE_NORMAL or s2.level != self.level:
                        continue
                    name = f"explore_L{self.level}_{s2.room:02x}_{OPPOSITE[d]}"
                    emu.save(name)
                    states[(s2.room, OPPOSITE[d])] = name
                    # believe the walk, not the note: if this exit no longer lands where it once
                    # did, the cache is stale and following it would queue a room we cannot reach
                    if s2.room != cached["room"]:
                        cached = {"ok": True, "room": s2.room, "frames": s2.frame - s.frame,
                                  "x": s2.x, "y": s2.y}
                        self._remember_exit(room, entry, d, cached)
                if not cached["ok"]:
                    continue
                nxt = (cached["room"], OPPOSITE[d])
                if nxt not in states:
                    continue          # nothing to expand it from; do not queue a dead node
                ng = cost + cached["frames"]
                if ng < g.get(nxt, 1 << 30):
                    g[nxt] = ng
                    came[nxt] = (node, d)
                    heapq.heappush(pq, (ng / 100 + h(cached["room"]) * 3, ng, nxt))
        if target is None:
            emu.note(f"Exploration finished: {len(seen)} rooms expanded")
            return []
        raise NavError(f"no route to room {target:02X} after expanding {len(seen)} screens")
