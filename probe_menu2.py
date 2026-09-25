from zelda.emulator import BizHawk
from zelda import bot
emu = BizHawk(log_name="probe_menu2.log", clean_sram=False)
for state in ("ckpt_fullgame_w8_67", "ckpt_fullgame_dm9_w0b"):
    s = emu.load(state); emu.step((), 2)
    print(state, "bitem", bot.b_item(emu), "inventory bytes 0x657..0x667:", [f"{emu.byte(a):02X}" for a in range(0x657, 0x668)])
    emu.step("Start", 1)
    n = 0
    while emu.byte(0xE1) != 7 and n < 90:
        emu.step((), 1); n += 1
    print("  open after", n, "frames; cursor byte candidates 0x656:", emu.byte(0x656))
    seq = []
    for k in range(14):
        emu.step("Right", 1); emu.step((), 1)
        seq.append(bot.b_item(emu))
    print("  after each Right press:", seq)
    seq = []
    for k in range(6):
        emu.step("Left", 1); emu.step((), 1)
        seq.append(bot.b_item(emu))
    print("  after each Left press:", seq)
emu.close()
