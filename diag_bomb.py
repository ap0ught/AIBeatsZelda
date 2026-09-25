from zelda.emulator import BizHawk
from zelda.overworld import Navigator, read_cells
from zelda import secrets, bot
emu = BizHawk(log_name="diag_bomb.log", clean_sram=False)
nav = Navigator(emu)
s = emu.load("ckpt_fullgame_n9_b05"); s = emu.wait(4)
print("state:", s, "bombs=", s.bombs)
tx, ty = 80, 173
try:
    st = nav.go(lambda x, y: abs(x-tx) <= 4 and abs(y-ty) <= 4,
                "the known bombing spot", optimistic=True, max_replans=40)
    print("walked to", (st.x, st.y))
except Exception as e:
    print("walk failed:", type(e).__name__, str(e)[:120])
print("selected bombs:", bot.select_b_item(emu, emu.step, bot.B_BOMBS))
emu.step("Up", 1); emu.step("B", 2)
for w in (30, 60, 90, 150, 240):
    emu.wait(30)
    print(f"  after ~{w}f: bombs={emu.state().bombs} opening={secrets.opening(emu)} "
          f"find_entrance={bot.find_entrance(emu)}")
cells = read_cells(emu)
print("F3 cells at:", [(r, c) for r in range(22) for c in range(32) if cells[r][c] == 0xF3])
print("24 cells at:", [(r, c) for r in range(22) for c in range(32) if cells[r][c] == 0x24][:12])
emu.close()
