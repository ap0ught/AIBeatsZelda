"""Find the hidden entrance on an overworld screen by trying everything.

Hyrule is full of caves that are not drawn until Link does something to the scenery: bomb a rock
face, burn a tree with a candle, push a gravestone or an Armos. The guides disagree about which
screen wants which, and a wrong guess is expensive - one whole sweep was spent bombing a screen
whose secret is not a bomb at all.

So: from one savestate, try every method at every plausible spot, reloading an in-memory snapshot
between trials. Nothing is spent - no bombs, no game time - and the answer is a fact rather than
a reading of somebody's table.
"""
from __future__ import annotations

from .emulator import BizHawk
from .overworld import Navigator, read_cells, snap
from . import bot

STAIRS = {0x70, 0x71, 0x72, 0x73}
# 2x2 scenery blocks, by the tile that sits in their top-left corner
ROCK = {0xC4, 0xC5, 0xC6, 0xC7}
TREE = {0xD8, 0xD9, 0xDA, 0xDB, 0xDC, 0xDD, 0xDE, 0xDF}
PUSHABLE = {0xC0, 0xC1, 0xC2, 0xC3, 0xCE, 0xCF, 0xD0, 0xD1, 0xD2, 0xD3, 0xE0, 0xE1, 0xE2, 0xE3}
GROUND = {0x26, 0x24}

PUSH_FROM = {"Up": (1, 0), "Down": (-1, 0), "Right": (0, -1), "Left": (0, 1)}


def cell(cells, r16: int, c16: int) -> int:
    return cells[r16 * 2][c16 * 2]


def opening(emu: BizHawk, baseline=None) -> tuple[int, int] | None:
    """A staircase tile or a cave mouth on this screen, as (x, y), or None.

    With `baseline` (the tile map before Link did anything) it also reports any black doorway
    tile 0x24 that was not there before. A bombed rock face opens as bare 0x24 with NO arch
    above it - bomb_entry_policy's own docstring says so - and the arch-hunting cave finder
    below therefore reported "nothing opened" after 220 bombs at Spectacle Rock, a rock this
    run had already blown open. Every bomb secret on the map was invisible until this check.
    """
    st = emu.state()
    if st.mode not in (5, 9) or st.hearts <= 0:
        # A dying Link repaints the screen, and the tile diff reads that as a doorway: the first
        # gravestone test on screen 21 "found" an opening at the bottom edge in mode 0x11.
        return None
    cells = read_cells(emu)
    spots = sorted({(r // 2, c // 2) for r in range(22) for c in range(32)
                    if cells[r][c] in STAIRS})
    if spots:
        r16, c16 = spots[0]
        return snap(c16 * 16, 64 + r16 * 16 - 3)
    if baseline is not None:
        new = sorted((r, c) for r in range(22) for c in range(32)
                     if cells[r][c] == 0x24 and baseline[r][c] != 0x24)
        if len(new) >= 2:
            r, c = new[-1]          # the doorway's bottom edge is where Link walks in
            return snap((c // 2) * 16, 64 + (r // 2) * 16 - 3)
    return bot.find_entrance(emu)


def _stand(nav: Navigator, r16: int, c16: int, snapshot=None) -> bool:
    emu = nav.emu
    tx, ty = snap(c16 * 16, 64 + r16 * 16 - 3)
    try:
        nav.go(lambda x, y: abs(x - tx) <= 4 and abs(y - ty) <= 4, "the spot",
               optimistic=True, max_replans=40)
        return True
    except Exception:
        pass
    # nav.go plans as if nothing on the screen can hurt Link, so on a screen with live enemies
    # it walks him into them. Fall back to the damage-aware planner for those spots only - it is
    # far slower, so it is not worth paying on a quiet screen.
    from .overworld import read_enemies
    if snapshot is None:
        return False
    emu.mload(snapshot); emu.wait(2)
    if not read_enemies(emu):
        return False
    from .lookahead import plan_reach, Goal
    try:
        return plan_reach(emu, None, Goal(tx, ty, 6), max_frames=1200) == "arrived"
    except Exception:
        return False


def sweep(emu: BizHawk, nav: Navigator, methods=("bomb", "push", "burn"), log=print) -> dict | None:
    """Try every method at every plausible spot. Returns {'method', 'stand', 'face', 'opening'}."""
    s = emu.state()
    cells = read_cells(emu)
    have = {"bomb": s.bombs > 0, "burn": emu.byte(0x65B) > 0, "push": True}
    before = opening(emu)
    if before is not None:
        log(f"screen {s.room:02X} already has an opening at {before}")
        return {"method": "open", "stand": None, "face": None, "opening": before}
    # A sweep that cannot walk anywhere measures nothing. Spectacle Rock is Lynel country: the
    # spot that actually opens it - stand (80,173), face Up - was unreachable on every one of
    # 132 attempts because Link kept dying on the way, and the sweep duly reported "nothing
    # opened" about a rock this run had already blown open. Clear the screen first. Nothing is
    # spent: the whole sweep runs inside an in-memory snapshot.
    #
    # Take the pristine snapshot BEFORE fighting. Clearing can kill Link, and a snapshot taken
    # afterwards is a snapshot of a corpse - which reachable-spot count 0 out of 274 duly was.
    from .combat import Fighter
    from .overworld import read_enemies
    snapshot = emu.msave()
    if read_enemies(emu):
        log(f"  {len(read_enemies(emu))} enemies here; clearing them so every spot is reachable")
        try:
            Fighter(nav).clear_room()
            if emu.state().hearts > 0 and not read_enemies(emu):
                cleared = emu.msave()
                emu.mfree(snapshot)
                snapshot = cleared
                log("  screen cleared; sweeping from there")
            else:
                emu.mload(snapshot); emu.wait(2)
                log("  could not clear the screen; sweeping the original")
        except Exception as e:
            emu.mload(snapshot); emu.wait(2)
            log(f"  could not clear the screen ({type(e).__name__}); sweeping the original")
    base = read_cells(emu)   # the screen before any bomb, flame or shove
    try:
        for method in methods:
            if not have.get(method):
                log(f"  skipping {method}: Link has none")
                continue
            tried = 0
            unreachable = 0
            # Iterate over the places Link can STAND, not over the scenery. Walking out from
            # each rock tile misses any spot the path planner cannot reach from that side, and
            # on Level 8's screen - which is solid mountain, not the burnable bush the guides
            # describe - that left most of the screen untried.
            #
            # Do NOT skip a spot because the tile it faces looks walkable. Screen 05 is the
            # bombable rock this run already opened to get into Level 9, and its known solution
            # - stand (80,173), face Up - faces a tile the knowledge base calls ground. Filtering
            # on that made the sweep report "nothing opened" on a screen we had personally blown
            # open. Try the promising spots first, then every remaining spot anyway.
            spots = []
            for r16 in range(11):
                for c16 in range(16):
                    if cell(cells, r16, c16) not in GROUND:
                        continue
                    for face, (dr, dc) in PUSH_FROM.items():
                        tr, tc = r16 - dr, c16 - dc      # the tile Link would be facing
                        if not (0 <= tr < 11 and 0 <= tc < 16):
                            continue
                        solid = cell(cells, tr, tc) not in GROUND
                        spots.append((0 if solid else 1, r16, c16, face))
            spots.sort(key=lambda s: s[0])
            if True:
                    for _rank, r16, c16, face in spots:
                        emu.mload(snapshot); emu.wait(2)
                        if not _stand(nav, r16, c16, snapshot):
                            unreachable += 1
                            continue
                        tried += 1
                        if method == "push":
                            for _ in range(20):
                                emu.step(face, 6)
                                # Stop the moment anything appears. Still holding the direction after the Magical
                                # Sword's gravestone slid walked Link straight down the new staircase - and a cave
                                # interior diffed against the graveyard is nonsense.
                                if emu.state().mode != 5 or opening(emu, base):
                                    break
                        else:
                            item = bot.B_BOMBS if method == "bomb" else bot.B_CANDLE
                            if not bot.select_b_item(emu, emu.step, item):
                                break
                            emu.step(face, 1); emu.step("B", 2); emu.wait(150)
                        spot = opening(emu, base)
                        now = emu.state()
                        if spot is None and now.hearts > 0 and now.mode in (0x0B, 0x10):
                            spot = (now.x, now.y)      # walked straight into whatever opened
                        if spot:
                            stand = snap(c16 * 16, 64 + r16 * 16 - 3)
                            log(f"  FOUND: {method} from {stand} facing {face} -> opening at {spot}")
                            try:
                                log(f"  screenshot: {emu.screenshot(f'secret_{s.room:02x}_{method}')}")
                            except Exception:
                                pass
                            emu.mload(snapshot)
                            return {"method": method, "stand": stand, "face": face, "opening": spot}
            log(f"  {method}: {tried} spots tried ({unreachable} unreachable), nothing opened")
        emu.mload(snapshot)
    finally:
        emu.mfree(snapshot)
    return None
