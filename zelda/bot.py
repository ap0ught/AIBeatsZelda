"""High-level game actions built on the BizHawk bridge: menus, walking, caves.

Everything here works purely from RAM feedback (no vision), so it is deterministic
and the input log can be replayed frame-exactly.
"""
from __future__ import annotations

from .emulator import BizHawk, State
from . import ram


class BotError(RuntimeError):
    pass


# ---------------------------------------------------------------- menus
def new_game(emu: BizHawk, log=print) -> State:
    """From power-on: title -> file select -> register a one-letter name -> start file 1.

    Empirically (this ROM, PRG1):
      * title screen is mode 0; Start goes to file select (mode 1)
      * with no saves the select cursor already sits on REGISTER YOUR NAME
      * register screen is mode 0x0E; a blank name is rejected, one letter is enough
      * Select x3 moves the heart slot1 -> slot2 -> slot3 -> REGISTER END; Start confirms
      * back at select the cursor is on file 1; Start begins play (mode 3 wipe, then mode 5)
    """
    # The title ignores input for a while after power-on, so tap until it reacts.
    emu.note("POWER ON. Waiting for the title screen to accept input; tapping START")
    s = tap_until(emu, "Start", lambda s: s.mode == ram.MODE_SELECT, max_taps=300)
    emu.note("File select reached (mode 01). Letting the screen settle")
    s = emu.wait(20)
    emu.note("No save file exists, so the cursor is on REGISTER YOUR NAME. Pressing START")
    s = tap_until(emu, "Start", lambda s: s.mode != ram.MODE_SELECT)     # -> register (or play, if a save exists)
    s = emu.wait(20)                                                     # let the transition settle
    if s.mode == ram.MODE_REGISTER:
        emu.note("Register screen (mode 0E). Blank names are rejected, typing one letter: A")
        s = emu.press("A", hold=2, release=10)              # letter 'A'
        emu.note("Moving the heart cursor down 3 slots to REGISTER END")
        for _ in range(3):
            s = emu.press("Select", hold=2, release=10)     # heart -> REGISTER END
        emu.note("Confirming registration with START")
        s = tap_until(emu, "Start", lambda s: s.mode == ram.MODE_SELECT)     # confirm registration
        s = emu.wait(20)
        emu.note("Back at file select with file 1 created. Pressing START to begin")
        s = tap_until(emu, "Start", lambda s: s.mode != ram.MODE_SELECT)     # start file 1
    else:
        log("warning: a save file already existed; started it instead of registering")
    emu.note("Screen wipe in progress, waiting for normal play (mode 05)")
    s = emu.wait_until(lambda s: s.mode == ram.MODE_NORMAL, 300)
    emu.note(f"In the overworld, room {s.room:02X}, Link at ({s.x},{s.y})")
    log(f"new game started: {s}")
    return s


def tap_until(emu: BizHawk, button: str, pred, *, hold: int = 2, release: int = 4,
              max_taps: int = 60) -> State:
    """Tap a button (press/release) repeatedly until pred(state) holds."""
    s = emu.state()
    for _ in range(max_taps):
        if pred(s):
            return s
        s = emu.step(button, hold)
        if pred(s):
            return s
        s = emu.step((), release)
    raise BotError(f"tap_until({button}) gave up at {s}")


# ---------------------------------------------------------------- movement
def _dir_for(dx: int, dy: int) -> str:
    if dx != 0:
        return "Right" if dx > 0 else "Left"
    return "Down" if dy > 0 else "Up"


def walk_to(emu: BizHawk, tx: int | None, ty: int | None, *, max_frames: int = 900,
            order: str = "xy", stop=None, tol: int = 0) -> State:
    """Walk Link to (tx, ty) one axis at a time using position feedback.

    `order` is "xy" (horizontal first) or "yx". Either target may be None to skip that axis.
    `stop(state)` may return True to end early (e.g. a mode change when entering a cave).
    Raises BotError if Link stops making progress.
    """
    s = emu.state()
    stall = 0
    last = (s.x, s.y)
    for _ in range(max_frames):
        if stop is not None and stop(s):
            return s
        dx = 0 if tx is None else tx - s.x
        dy = 0 if ty is None else ty - s.y
        if abs(dx) <= tol:
            dx = 0
        if abs(dy) <= tol:
            dy = 0
        if dx == 0 and dy == 0:
            return s
        if order == "xy":
            btn = _dir_for(dx, 0) if dx else _dir_for(0, dy)
        else:
            btn = _dir_for(0, dy) if dy else _dir_for(dx, 0)
        s = emu.step(btn, 1)
        if (s.x, s.y) == last:
            stall += 1
            if stall > 40:
                raise BotError(f"walk_to({tx},{ty}) stalled at {s}")
        else:
            stall = 0
        last = (s.x, s.y)
    raise BotError(f"walk_to({tx},{ty}) timed out at {s}")


def hold_until(emu: BizHawk, button: str, pred, max_frames: int = 900) -> State:
    """Hold one button until pred(state) is true."""
    s = emu.state()
    for _ in range(max_frames):
        if pred(s):
            return s
        s = emu.step(button, 1)
    raise BotError(f"hold_until({button}) timed out at {s}")


def wait_movable(emu: BizHawk, button: str = "Up", max_frames: int = 600) -> State:
    """Hold a direction until Link actually moves (used for the cave text freeze)."""
    # Link can twitch a pixel on entry and then freeze again, so demand 3 consecutive moving frames.
    s = emu.state()
    last = (s.x, s.y)
    moving = 0
    for _ in range(max_frames):
        s = emu.step(button, 1)
        moving = moving + 1 if (s.x, s.y) != last else 0
        last = (s.x, s.y)
        if moving >= 3:
            return s
    raise BotError(f"wait_movable({button}) timed out at {s}")


# ---------------------------------------------------------------- dungeon bombs
BOMB_SPOTS = {  # where to stand to bomb a wall in the middle of each side (measured: east from x=184 works)
    "Right": (184, 141), "Left": (56, 141), "Up": (120, 93), "Down": (120, 181),
}


BOMB_CANDIDATES = {   # (stand x, stand y, face): nearest the measured spot first
    "Right": [(184, 141, "Right"), (192, 141, "Right"), (200, 141, "Right"), (208, 141, "Right"),
              (208, 125, "Down"), (208, 157, "Up")],
    "Left":  [(56, 141, "Left"), (48, 141, "Left"), (40, 141, "Left"), (32, 141, "Left"),
              (32, 125, "Down"), (32, 157, "Up")],
    "Up":    [(120, 93, "Up"), (104, 93, "Right"), (136, 93, "Left")],
    "Down":  [(120, 181, "Down"), (120, 189, "Down"), (104, 189, "Right"), (136, 189, "Left")],
}


def bomb_spot(emu, direction: str):
    """The first bombing candidate that is floor and reachable from where Link stands, or the standard one."""
    from .lookahead import Lattice
    lat = Lattice(emu)
    s = emu.state()
    field = lat.field([(s.x, s.y)])
    for x, y, face in BOMB_CANDIDATES[direction]:
        if (x, y) in lat.free and (x, y) in field:
            return x, y, face
    x, y = BOMB_SPOTS[direction]
    return x, y, direction


def bomb_door(nav, direction: str, log=print):
    """Stand a tile and a half from the wall's centre, face it, drop a bomb, wait for the hole."""
    emu = nav.emu
    s = emu.state()
    if s.bombs <= 0:
        raise BotError("no bombs")
    tx, ty, face = bomb_spot(emu, direction)
    emu.note(f"Bombable wall on the {direction} side: standing at ({tx},{ty}) facing {face} and placing a bomb")
    s = nav.go(lambda x, y: x == tx and y == ty, f"the bombing spot for the {direction} wall")
    doors0 = emu.byte(0xEE)
    emu.step(face, 1)
    emu.step("B", 2)
    for _ in range(100):
        s = emu.step((), 1)
        if emu.byte(0xEE) != doors0:
            emu.note(f"The wall is open (doors byte {doors0:02x} -> {emu.byte(0xEE):02x}), {s.bombs} bombs left")
            return s
    raise BotError("the bomb didn't open the wall")


# ---------------------------------------------------------------- caves
def enter_cave_up(emu: BizHawk, cave_x: int, log=print) -> State:
    """On the overworld, align to cave_x and walk up into the cave until inside (mode 0x0B)."""
    emu.note(f"Cave entrance is in column x={cave_x}. Walking sideways until Link.x == {cave_x}")
    walk_to(emu, cave_x, None)
    emu.note("Aligned. Holding UP until the game mode says we're inside a cave (mode 0B)")
    s = hold_until(emu, "Up", lambda s: s.mode == ram.MODE_GROTTO and s.sub == 0 and s.y > 200, 900)
    emu.note("Inside the cave")
    log(f"inside cave: {s}")
    return s


def cave_item_x(emu: BizHawk) -> int | None:
    """x of the item on display in a one-item cave, read from the object slots.

    The old man, his fire torches and the item all sit in the object table; the item is the
    lone object on the item row (y ~ 128) that is not one of the two flanking flames (type 40)."""
    ts = emu.ram(0x34F, 20); xs = emu.ram(0x70, 20); ys = emu.ram(0x84, 20)
    cands = [xs[i] for i in range(20) if ts[i] and ts[i] != 0x40 and 112 <= ys[i] <= 136]
    if not cands:
        return None
    # if a stray projectile is crossing the item row, take the one nearest the middle of the cave
    return min(cands, key=lambda x: abs(x - 120))


def take_cave_item(emu: BizHawk, item_x: int | None = None, flag_addr: int = ram.SWORD, log=print) -> State:
    """Inside a one-item cave: wait out the text freeze, then walk into the item from below.

    The item's pickup box is only hit when Link walks up through y~157 at the item's x;
    standing on the top row (y=141) directly under it does nothing, so line up at y=173 first.
    """
    before = emu.byte(flag_addr)
    # The game flips to cave mode while Link is still standing outside; only once the room is
    # actually swapped in does he appear on the cave's bottom row (y > 190). Submode 8 on top of
    # that means the room is still being set up and the object slots still hold the overworld's
    # enemies, so reading the item out of them now would return garbage.
    emu.wait_until(lambda s: s.y > 190, 400, buttons=("Up",))
    emu.wait_until(lambda s: s.sub == 0, 300, buttons=("Up",))
    # Link takes a couple of steps in on his own, then freezes while the old man's text writes
    # out. Waiting for "he moved" is not enough - that first scripted step looks like movement.
    emu.note("Link is frozen while the old man's text writes out. Holding UP until he really walks")
    s = hold_until(emu, "Up", lambda s: s.y < 200, 600)
    if s.y >= 200:
        raise BotError(f"never got moving inside the cave at {s}")
    if item_x is None:
        item_x = cave_item_x(emu)
        if item_x is None:
            item_x = 120        # every one-item cave centres the item; fall back rather than fail
            emu.note("Item not visible in the object table; assuming the usual centre x=120")
        else:
            emu.note(f"Found the item in the object table at x={item_x}")
    emu.note("Walking up to y=173, clear of the entrance corridor but below the item")
    s = walk_to(emu, None, 173, order="yx")
    emu.note(f"Lining up under the item: walking to x={item_x}")
    s = walk_to(emu, item_x, None)
    emu.note(f"Walking UP into the item. Watching RAM ${flag_addr:04X} for the pickup")
    s = hold_until(emu, "Up", lambda s: emu.byte(flag_addr) != before or s.y <= 141, 200)
    if emu.byte(flag_addr) == before:
        raise BotError(f"item not picked up at {s}")
    emu.note(f"GOT IT. RAM ${flag_addr:04X} changed {before} -> {emu.byte(flag_addr)}")
    log(f"picked up item: {s}")
    return s


def exit_cave_down(emu: BizHawk, log=print) -> State:
    """Walk down out of a cave until back in normal overworld play."""
    emu.note("Item-get animation. Holding DOWN until Link can move again")
    s = wait_movable(emu, "Down")
    emu.note("Walking to x=112, the exit corridor")
    s = walk_to(emu, 112, None, order="xy", stop=lambda s: s.mode != ram.MODE_GROTTO)
    emu.note("Holding DOWN to leave the cave; waiting for overworld mode 05")
    s = hold_until(emu, "Down", lambda s: s.mode == ram.MODE_NORMAL and s.level == 0 and s.y > 90, 900)
    emu.note(f"Back on the overworld in room {s.room:02X}")
    log(f"back outside: {s}")
    return s


# ---------------------------------------------------------------- the raft
# The raft pier has two graphics: 76/77 on the mainland dock, 74/75 on the island side. Both are
# "walk onto this and the raft sails", and the island one is how Link gets back off Level 4.
DOCK_IDS = {0x74, 0x75, 0x76, 0x77}


def find_dock(emu):
    """(x, y) of the dock pier on this overworld screen, or None. The pier is a 16x16 tile of
    ids 76/77 sticking into the water; walking onto it with the raft auto-sails Link across."""
    from .overworld import read_cells
    cells = read_cells(emu)
    spots = sorted({(r // 2, c // 2) for r in range(22) for c in range(32) if cells[r][c] in DOCK_IDS})
    if not spots:
        return None
    r16, c16 = spots[0]
    return c16 * 16, 64 + r16 * 16 - 3


def ride_dock(nav, log=print):
    """Walk onto this screen's dock and ride the raft to the next screen."""
    emu = nav.emu
    s = emu.state()
    if not emu.byte(0x660):
        raise BotError("no raft")
    spot = find_dock(emu)
    if spot is None:
        raise BotError("no dock on this screen")
    dx, dy = spot
    # A pier in the top half of the screen is walked onto from below; the island's pier is at the
    # bottom and has to be walked onto from above. Getting this backwards asks the navigator to
    # stand in open water.
    from_above = dy >= 140
    wait_y = dy - 32 if from_above else dy + 32
    push = "Down" if from_above else "Up"
    emu.note(f"Dock at ({dx},{dy}). Walking to its column and stepping on from "
             + ("above" if from_above else "below"))
    nav.go(lambda x, y: x == dx and abs(y - wait_y) <= 8,
           ("above the dock" if from_above else "below the dock"), max_replans=60)
    room0 = s.room
    for _ in range(240):
        s = emu.step(push, 1)
        if s.room != room0 or s.mode not in (5, 9):
            break
    # Hold the SAILING direction while the raft crosses: this used to hold Up both ways, which on
    # the island-to-mainland trip (sailing Down) is the wrong way.
    s = emu.wait_until(lambda s: s.mode in (5, 9) and s.room != room0, 900, buttons=(push,))
    # The screen changes long before the raft reaches the far pier. Returning here (as this once
    # did) handed the next segment a Link still afloat: it planned from open water - "no path to
    # the Down edge from (128,90)" - or pressed Up and sailed back to the island. So wait, pressing
    # nothing, until he has actually stopped moving.
    last, still = (s.x, s.y), 0
    for _ in range(300):
        s = emu.step((), 1)
        still = still + 1 if (s.x, s.y) == last else 0
        last = (s.x, s.y)
        if still >= 10:
            break
    emu.note(f"Sailed to room {s.room:02X}, landed at ({s.x},{s.y})")
    log(f"rafted to room {s.room:02X}")
    return s


def find_entrance(emu):
    """(x, y) of a cave/dungeon doorway on this overworld screen, or None.
    The doorway is drawn as the black tile 0x24 with the dark arch 0xF3 directly above it."""
    from .overworld import read_cells
    cells = read_cells(emu)
    for r in range(2, 21):
        for c in range(1, 31):
            if cells[r][c] == 0x24 and cells[r - 1][c] == 0xF3 and cells[r][c + 1] == 0x24:
                return (c // 2) * 16, 64 + (r // 2) * 16 - 3
    return None


def enter_entrance(nav, level=None, log=print):
    """Walk under this screen's doorway and go in."""
    emu = nav.emu
    spot = find_entrance(emu)
    if spot is None:
        raise BotError("no entrance on this screen")
    ex, ey = spot
    emu.note(f"Entrance at ({ex},{ey}). Walking below it and holding UP")
    nav.allow_entrances = True
    try:
        nav.go(lambda x, y: x == ex and y == ey + 16, "below the entrance", max_replans=80)
    finally:
        nav.allow_entrances = False
    s = emu.wait_until(lambda s: (s.level != 0 if level is None else s.level == level), 300, buttons=("Up",))
    s = emu.wait_until(lambda s: s.mode in (5, 9), 400)
    emu.note(f"Inside level {s.level}, room {s.room:02X}")
    return s


# ---------------------------------------------------------------- the B slot
# Pressing B uses whatever is in the B slot, and picking up a new item does NOT change it. Link
# carried the boomerang out of Level 1, so every "bomb" the bot dropped after that was a boomerang
# toss: the bomb count never moved and Dodongo never ate anything. The selection lives at $0656
# and is changed on the inventory subscreen (Start opens it; the game mode byte does not change,
# so the only way to tell is to watch $0656 itself).
# B-slot item ids as they appear at $0656. Only items Link actually owns can be selected,
# so cycling the cursor skips the rest: with no bombs left the slot offers boomerang and recorder
# only. Measured in game, not guessed.
B_BOOMERANG, B_BOMBS, B_BOW, B_RECORDER = 0, 1, 2, 5
B_CANDLE, B_BAIT, B_POTION, B_WAND = 4, 6, 7, 8


def b_item(emu) -> int:
    return emu.byte(0x656)


def select_b_item(emu, step, want: int, log=print) -> bool:
    """Open the inventory, move the cursor onto `want`, close it again. No-op if already set."""
    if b_item(emu) == want:
        return True
    emu.note(f"B slot holds item {b_item(emu)}; opening the inventory to select item {want}")
    # Measured (probe_menu.py): the subscreen takes 62 frames to scroll in (MenuState $E1 counts 2..6, then 7
    # = ready), the cursor moves on every fresh press, and it takes 58 frames to scroll out. Poll instead of
    # waiting a flat 60 + 12 per move + 60.
    step("Start", 1)
    # MenuState ($E1) counts up, sits on one value for the ~56-frame scroll, then steps once more when the
    # menu goes live (6 -> 7 in a dungeon, 7 -> 8 outside): wait for the step that ends the long plateau.
    last, run = emu.byte(0xE1), 0
    for _ in range(120):
        step((), 1)
        v = emu.byte(0xE1)
        if v != last:
            if run > 20:
                break
            last, run = v, 0
        else:
            run += 1
    for _ in range(12):
        if b_item(emu) == want:
            break
        step("Right", 1); step((), 1)
    step("Start", 1)
    for _ in range(90):
        if emu.byte(0xE1) == 0:
            break
        step((), 1)
    ok = b_item(emu) == want
    emu.note("B slot set to " + ("bombs" if want == B_BOMBS else f"item {want}") if ok
             else "could not change the B slot")
    return ok
