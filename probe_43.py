"""Level 9 room 0x43: the walkthroughs say kill the Wizzrobes, then push "the middle block on the
right side" for the Silver Arrow staircase. clear_push_stairs_policy failed 40/40 ("no stairs
appeared"). Find the block and side that open it, first without clearing, then after clearing."""
import random
from zelda.emulator import BizHawk
from zelda.overworld import Navigator, read_cells, read_enemies, read_room_item, BLOCK_IDS
from zelda.lookahead import plan_fight
from zelda import secrets
try:
    from zelda.search import Recorder
except ImportError:
    from zelda.runner import Recorder

emu = BizHawk(log_name="probe_43.log", clean_sram=False)
nav = Navigator(emu)
s = emu.load("ckpt_fullgame_s9_43"); s = emu.wait(4)
print("start:", s, "| bombs", s.bombs, "keys", s.keys, flush=True)
print("shot:", emu.screenshot("room43_start"), flush=True)
print("enemies:", [(hex(e[1]), e[2], e[3], e[4] >> 4) for e in read_enemies(emu)], flush=True)
cells = read_cells(emu)
print("tile map 16x11 (top-left cell of each tile):", flush=True)
for r16 in range(11):
    print(f"  {r16:2d} " + " ".join(f"{cells[r16*2][c16*2]:02X}" for c16 in range(16)), flush=True)
blocks = sorted({(r // 2, c // 2) for r in range(22) for c in range(32) if cells[r][c] in BLOCK_IDS})
print("blocks (r16,c16):", blocks, flush=True)
# right-hand blocks first, those nearest the middle row first
order = sorted(blocks, key=lambda b: (-b[1], abs(b[0] - 5)))


def try_pushes(label, root, base):
    for br, bc in order:
        for face, (dr, dc) in secrets.PUSH_FROM.items():
            emu.mload(root); emu.wait(2)
            if not secrets._stand(nav, br + dr, bc + dc, root):
                continue
            for _ in range(20):
                emu.step(face, 6)
                c2 = read_cells(emu)
                if any(c2[r][c] in secrets.STAIRS for r in range(22) for c in range(32)):
                    break
            c2 = read_cells(emu)
            stairs = sorted({(r // 2, c // 2) for r in range(22) for c in range(32) if c2[r][c] in secrets.STAIRS})
            moved = c2[br * 2][bc * 2] != base[br * 2][bc * 2]
            if moved or stairs:
                print(f"  [{label}] block {(br, bc)} pushed {face}: moved={moved} stairs={stairs}", flush=True)
            if stairs:
                print("  shot:", emu.screenshot(f"room43_stairs_{label}"), flush=True)
                return (br, bc, face, stairs)
    print(f"  [{label}] no block/side opened stairs", flush=True)
    return None


root = emu.msave()
found = try_pushes("uncleared", root, cells)
if not found:
    emu.mload(root); emu.wait(2)
    rec = Recorder(emu)
    res = plan_fight(emu, rec, max_frames=5000, rng=random.Random(1000), log=True)
    q = emu.state()
    print("clear attempt:", res, q, "| cleared flag $034D =", emu.byte(0x34D),
          "| alive:", [(hex(e[1]), e[2], e[3]) for e in read_enemies(emu)],
          "| item:", read_room_item(emu), flush=True)
    print("shot:", emu.screenshot("room43_after_fight"), flush=True)
    if q.hearts > 0:
        root2 = emu.msave()
        found = try_pushes("cleared", root2, read_cells(emu))
        emu.mfree(root2)
print("RESULT:", found, flush=True)
emu.mfree(root)
emu.close()
