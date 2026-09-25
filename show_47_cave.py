"""Burn the tree the sweep found on 47 and photograph what is inside. The guides call it a heart
container; a screenshot makes it a fact."""
from zelda.emulator import BizHawk
from zelda.overworld import Navigator, read_cells, read_enemies
from zelda.combat import Fighter
from zelda import secrets, bot

emu = BizHawk(log_name="show_47_cave.log", clean_sram=False)
nav = Navigator(emu)
s = emu.load("ckpt_fullgame_h9_48"); s = emu.wait(4)
s = nav.exit_screen("Left")
print("screen", f"{s.room:02X}", s, flush=True)
if read_enemies(emu):
    try:
        Fighter(nav).clear_room()
    except Exception as e:
        print("clear failed:", type(e).__name__, flush=True)
root = emu.msave()
# the sweep's answer: stand (176,157) facing Down -> r16 = 6, c16 = 11
print("standing:", secrets._stand(nav, 6, 11, root), emu.state(), flush=True)
base = read_cells(emu)
print("candle selected:", bot.select_b_item(emu, emu.step, bot.B_CANDLE), flush=True)
emu.step("Down", 1); emu.step("B", 2); emu.wait(200)
op = secrets.opening(emu, base)
print("opening:", op, flush=True)
print("shot:", emu.screenshot("cave_47_opened"), flush=True)
if op:
    ox, oy = op
    st = emu.state()
    for _ in range(240):
        if st.mode != 5 or st.room != 0x47:
            break
        st = emu.step("Right" if st.x < ox else "Left" if st.x > ox else
                      "Down" if st.y < oy else "Up", 1)
    print("after walking onto it:", st, flush=True)
    emu.wait(320)
    print("shot:", emu.screenshot("cave_47_inside"), flush=True)
emu.mfree(root)
emu.close()
