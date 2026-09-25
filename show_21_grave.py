"""The Magical Sword gravestone, per Thonky and the ROM: screen 21 (the graveyard's top-right
screen), middle row, third stone from the left. Push it from every side - then every other stone -
and photograph any staircase. Enemies are cleared first: touching graveyard stones calls Ghinis."""
from zelda.emulator import BizHawk
from zelda.overworld import Navigator, read_cells, read_enemies
from zelda.combat import Fighter
from zelda import secrets

emu = BizHawk(log_name="show_21_grave.log", clean_sram=False)
nav = Navigator(emu)
s = emu.load("ckpt_fullgame_bw3_31"); s = emu.wait(4)
s = nav.exit_screen("Up")
print("screen", f"{s.room:02X}", s, flush=True)
print("shot:", emu.screenshot("grave_21_before"), flush=True)
cells = read_cells(emu)
stones = sorted({(r // 2, c // 2) for r in range(22) for c in range(32) if cells[r][c] == 0xBC})
print("gravestones (r16,c16):", stones, flush=True)
if read_enemies(emu):
    try:
        Fighter(nav).clear_room()
    except Exception as e:
        print("clear failed:", type(e).__name__, flush=True)
root = emu.msave()
base = read_cells(emu)
rows = sorted({r for r, _ in stones})
mid = rows[len(rows) // 2]
target = (mid, sorted(c for r, c in stones if r == mid)[2])
print("target stone:", target, flush=True)
found = None
for sr, sc in [target] + [st for st in stones if st != target]:
    for face, (dr, dc) in secrets.PUSH_FROM.items():
        emu.mload(root); emu.wait(2)
        if not secrets._stand(nav, sr + dr, sc + dc, root):
            print(f"  stone {(sr, sc)} push {face}: could not stand", flush=True)
            continue
        for _ in range(20):
            emu.step(face, 6)
        op = secrets.opening(emu, base)
        print(f"  stone {(sr, sc)} push {face}: {op}", flush=True)
        if op:
            found = ((sr, sc), face, op, emu.state())
            print("shot:", emu.screenshot("grave_21_found"), flush=True)
            break
    if found:
        break
print("RESULT:", found, flush=True)
emu.mfree(root)
emu.close()
