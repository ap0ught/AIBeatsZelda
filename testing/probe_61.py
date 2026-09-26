"""Walk the walkthroughs' Silver Arrow route from the s9_43 checkpoint instead of deducing it:
0x43 -> 0x53 -> 0x63 -> (locked) 0x62 -> 0x61, the Patra room. Dump each room that matters, fight
the Patra, push blocks (leftmost first, without touching knowledge/blocks.json), take the stairs
and report where the passage really comes out."""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import random
from zelda.emulator import BizHawk
from zelda.overworld import Navigator, read_cells, read_enemies, read_room_item, BLOCK_IDS, snap
from zelda.lookahead import plan_fight
from zelda.cellar import walk_passage
from zelda import secrets
try:
    from zelda.search import Recorder
except ImportError:
    from zelda.runner import Recorder

emu = BizHawk(log_name="probe_61.log", clean_sram=False)
nav = Navigator(emu)
s = emu.load("ckpt_fullgame_s9_43"); s = emu.wait(4)
# An old man's room freezes Link while the text types out: moving at once reads as "stuck".
emu.wait(600)
print("after waiting:", emu.state(), flush=True)
print("shot:", emu.screenshot("probe61_room43_text"), flush=True)
_a = emu.state(); emu.step("Up", 8); _b = emu.state()
print("can move:", (_a.x, _a.y), "->", (_b.x, _b.y), flush=True)


def dump(tag):
    s = emu.state()
    cells = read_cells(emu)
    print(f"== {tag}: {s} | keys {s.keys} bombs {s.bombs}", flush=True)
    print("  enemies (type,x,y,hp):", [(hex(e[1]), e[2], e[3], e[4] >> 4) for e in read_enemies(emu)], flush=True)
    for r16 in range(11):
        print(f"   {r16:2d} " + " ".join(f"{cells[r16*2][c16*2]:02X}" for c16 in range(16)), flush=True)
    blocks = sorted({(r // 2, c // 2) for r in range(22) for c in range(32) if cells[r][c] in BLOCK_IDS})
    print("  blocks:", blocks, "| item:", read_room_item(emu), flush=True)
    print("  shot:", emu.screenshot(f"probe61_{tag}"), flush=True)
    return cells, blocks


for d in ("Down", "Down", "Left", "Left"):
    try:
        s = nav.exit_screen(d)
        print(f"exit {d} -> room {s.room:02X} (hp {s.hearts}, keys {s.keys})", flush=True)
    except Exception as e:
        print(f"exit {d} FAILED: {type(e).__name__}: {str(e)[:90]}", flush=True)
        break
room = emu.state().room
cells, blocks = dump(f"room{room:02x}_arrival")
if room != 0x61:
    print("did not reach 0x61; stopping", flush=True)
    emu.close(); raise SystemExit
emu.save("probe_room61")

rec = Recorder(emu)
res = plan_fight(emu, rec, max_frames=8000, rng=random.Random(7), log=True)
print("fight:", res, "| cleared flag $034D =", emu.byte(0x34D), flush=True)
cells, blocks = dump("room61_after_fight")
if emu.state().hearts <= 0:
    emu.close(); raise SystemExit

root = emu.msave()
base = read_cells(emu)
found = None
for br, bc in sorted(blocks, key=lambda b: (b[1], abs(b[0] - 5))):          # leftmost first
    for face, (dr, dc) in secrets.PUSH_FROM.items():
        emu.mload(root); emu.wait(2)
        if not secrets._stand(nav, br + dr, bc + dc, root):
            continue
        for _ in range(20):
            emu.step(face, 6)
        c2 = read_cells(emu)
        stairs = sorted({(r // 2, c // 2) for r in range(22) for c in range(32) if c2[r][c] in secrets.STAIRS})
        if c2[br * 2][bc * 2] != base[br * 2][bc * 2] or stairs:
            print(f"  block {(br, bc)} pushed {face}: moved={c2[br*2][bc*2] != base[br*2][bc*2]} stairs={stairs}", flush=True)
        if stairs:
            found = stairs[0]
            print("  shot:", emu.screenshot("probe61_stairs"), flush=True)
            break
    if found:
        break
print("stairs:", found, flush=True)
if found:
    tr, tc = found
    tx, ty = snap(tc * 16, 64 + tr * 16 - 3)
    try:
        nav.go(lambda x, y: abs(x - tx) <= 8 and abs(y - ty) <= 8, "the stairs", optimistic=True, max_replans=80)
    except Exception as e:
        print("  walk to stairs failed:", type(e).__name__, str(e)[:80], flush=True)
    st = emu.state()
    for _ in range(200):
        if st.mode != 5:
            break
        st = emu.step("Right" if st.x < tx else "Left" if st.x > tx else "Down" if st.y < ty else "Up", 1)
    st = emu.wait_until(lambda q: q.mode == 9 and q.sub >= 9, 900)
    print("  in the passage:", st, flush=True)
    try:
        walk_passage(emu, emu.step)
        emu.wait_until(lambda q: q.mode == 5, 400)
    except Exception as e:
        print("  passage walk failed:", type(e).__name__, str(e)[:80], flush=True)
    dump(f"passage_end_room{emu.state().room:02x}")
emu.mfree(root)
emu.close()
