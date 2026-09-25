from zelda.emulator import BizHawk
from zelda import bot
emu = BizHawk(log_name="probe_menu3.log", clean_sram=False)
s = emu.load("ckpt_fullgame_w8_67"); emu.step((), 2)
emu.step("Start", 1)
seq = [emu.byte(0xE1)]
for f in range(90):
    emu.step((), 1); seq.append(emu.byte(0xE1))
print("open seq:", seq)
b = []
for k in range(8):
    emu.step("Right", 1); emu.step((), 1); b.append(bot.b_item(emu))
print("b after presses:", b)
emu.step("Start", 1)
seq = []
for f in range(90):
    st = emu.step((), 1); seq.append(emu.byte(0xE1))
print("close seq:", seq)
emu.close()
