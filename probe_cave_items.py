"""Where exactly do the potion and the heart container sit inside a TAKE-ANY-ONE cave? Walking
into the wrong one loses the heart for good, so read the live object table instead of guessing
from shop slot positions."""
from zelda.emulator import BizHawk
from zelda.overworld import Navigator, read_cells, read_enemies
from zelda.combat import Fighter
from zelda import secrets, bot

emu = BizHawk(log_name="probe_cave_items.log", clean_sram=False)
nav = Navigator(emu)
s = emu.load("ckpt_fullgame_h9_48"); s = emu.wait(4)
s = nav.exit_screen("Left")
if read_enemies(emu):
    try:
        Fighter(nav).clear_room()
    except Exception as e:
        print("clear failed:", type(e).__name__, flush=True)
root = emu.msave()
secrets._stand(nav, 6, 11, root)
base = read_cells(emu)
bot.select_b_item(emu, emu.step, bot.B_CANDLE)
emu.step("Down", 1); emu.step("B", 2); emu.wait(200)
ox, oy = secrets.opening(emu, base)
st = emu.state()
for _ in range(240):
    if st.mode != 5:
        break
    st = emu.step("Right" if st.x < ox else "Left" if st.x > ox else "Down" if st.y < oy else "Up", 1)
emu.wait_until(lambda q: q.y > 190, 400, buttons=("Up",))
emu.wait_until(lambda q: q.sub == 0, 300, buttons=("Up",))
st = bot.hold_until(emu, "Up", lambda q: q.y < 200, 600)
print("inside and moving:", st, "containers", st.containers, flush=True)
ts = emu.ram(0x34F, 12); xs = emu.ram(0x70, 12); ys = emu.ram(0x84, 12)
for i in range(12):
    if ts[i]:
        print(f"  slot {i:2d}: type {ts[i]:02X} at ({xs[i]},{ys[i]})", flush=True)
print("cave_item_x() says:", bot.cave_item_x(emu), flush=True)
print("HEARTS $066F:", hex(emu.byte(0x66F)), " potion $065E:", hex(emu.byte(0x65E)), flush=True)
print("shot:", emu.screenshot("cave_items_probe"), flush=True)
emu.mfree(root)
emu.close()
