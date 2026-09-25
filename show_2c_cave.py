"""Walk into the cave the sweep opened on 2C and photograph what is inside.

A black doorway is not proof of a heart container - it could be a shop, a money cave or a hint.
The screenshot is the proof.
"""
from zelda.emulator import BizHawk
from zelda.overworld import Navigator, read_cells
from zelda.combat import Fighter
from zelda import secrets, bot

emu = BizHawk(log_name="show_2c_cave.log", clean_sram=False)
nav = Navigator(emu)
s = emu.load("ckpt_fullgame_c8_2d"); s = emu.wait(4)
s = nav.exit_screen("Left")
print("screen", f"{s.room:02X}", s, "bombs", s.bombs, flush=True)
try:
    Fighter(nav).clear_room()
except Exception as e:
    print("clear failed:", type(e).__name__, flush=True)
root = emu.msave()
# the sweep's answer: stand (176,157) facing Left -> c16 = 11, r16 = 6
print("standing:", secrets._stand(nav, 6, 11, root), emu.state(), flush=True)
before = read_cells(emu)
print("select bombs:", bot.select_b_item(emu, emu.step, bot.B_BOMBS), flush=True)
emu.step("Left", 1); emu.step("B", 2); emu.wait(160)
print("opening:", secrets.opening(emu, before), flush=True)
try:
    nav.go(lambda x, y: abs(x - 144) <= 2 and abs(y - 173) <= 4, "just below the new doorway",
           optimistic=True, max_replans=40)
except Exception as e:
    print("walk below doorway failed:", type(e).__name__, str(e)[:80], flush=True)
st = emu.state()
for _ in range(120):
    st = emu.step("Up", 1)
    if st.mode != 5 or st.room != 0x2C:
        break
print("after walking in:", st, flush=True)
emu.wait(320)
print("shot:", emu.screenshot("problem_5_inside_2c_cave"), flush=True)
emu.close()
