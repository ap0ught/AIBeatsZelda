"""Level 7 room 0D: where is the block, where do the stairs appear, how long after the push starts, and
does a push from the other side work? Loads the current run's l7_0d checkpoint, clears the room first."""
import random
import sys
from zelda.emulator import BizHawk
from zelda.overworld import Navigator, read_cells, BLOCK_IDS, snap, NavError
from zelda.lookahead import plan_fight
from zelda.search import Recorder

STAIRS = {0x70, 0x71, 0x72, 0x73}
emu = BizHawk(log_name="probe_l7_0d.log", clean_sram=False)
nav = Navigator(emu)
for seed in range(8):
    emu.load("ckpt_fullgame_l7_0d")
    rec = Recorder(emu)
    rec.step((), 2 + seed)
    res = plan_fight(emu, rec, max_frames=2500, rng=random.Random(seed))
    print("fight seed", seed, res, "frames", len(rec.inputs), "cleared flag", emu.byte(0x34D), flush=True)
    if res == "clear":
        break
cells = read_cells(emu)
for r in range(22):
    print("".join("#" if cells[r][c] in BLOCK_IDS else "~" if cells[r][c] == 0xF4 else "." if cells[r][c] < 0x80 else "X"
                  for c in range(32)), r)
s = emu.state()
print("link at", s.x, s.y)
cleared = emu.msave()
for push, ox, oy in (("Left", 21, 3), ("Right", -19, 3), ("Up", 0, 21), ("Down", 0, -19)):
    emu.mload(cleared)
    br, bc = 5, 12
    bx, by = bc * 16, 64 + br * 16
    sx, sy = snap(bx + ox, by + oy)
    try:
        nav.go(lambda x, y: x == sx and y == sy, "beside the block", max_replans=40)
    except NavError as e:
        print(push, "cannot reach", (sx, sy), e)
        continue
    before = read_cells(emu)
    f0 = emu.state().frame
    first = None
    for i in range(120):
        emu.step(push, 1)
        now = read_cells(emu)
        if first is None and any(now[r][c] != before[r][c] for r in range(22) for c in range(32)):
            first = i
        spots = sorted({(r // 2, c // 2) for r in range(22) for c in range(32) if now[r][c] in STAIRS})
        if spots:
            print(push, "from", (sx, sy), ": map first changed at push frame", first, "; stairs at frame", i, spots,
                  "-> px", [(c * 16, 64 + r * 16) for r, c in spots], "link", emu.state().x, emu.state().y)
            break
    else:
        print(push, "from", (sx, sy), ": no stairs in 120 frames; first change", first)
emu.close()
