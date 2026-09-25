import sys
from zelda.emulator import BizHawk
from zelda import bot
from zelda.overworld import read_enemies, enemy_name
emu = BizHawk(log_name="probe_whirl_dbg2.log", clean_sram=False)
s = emu.load("ckpt_fullgame_hc_47_heart"); emu.step((), 2)
print("room", hex(s.room), "pos", (s.x, s.y), "idx", emu.byte(0x523), "enemies", [(e[0], enemy_name(e[1]), e[2], e[3]) for e in read_enemies(emu)])
bot.select_b_item(emu, emu.step, bot.B_RECORDER)
for n in range(3):
    emu.step("Left", 1); emu.step("B", 2)
    k = 0
    while emu.byte(0x3C) and k < 200:
        emu.step((), 1); k += 1
    q = emu.state()
    print(f"note {n}: tune {k} frames, idx {emu.byte(0x523)}, wind {[ (i, emu.byte(0x70+i), emu.byte(0x84+i)) for i,t in enumerate(emu.ram(0x34F,12)) if t == 0x2E]}, link ({q.x},{q.y}) hearts {q.hearts} summoned {emu.byte(0x508)}")
for f in range(300):
    q = emu.step((), 1)
    if f % 20 == 0 or q.room != s.room:
        print(f"  f{f}: link ({q.x},{q.y}) state {emu.byte(0xAC):02X} tele {emu.byte(0x522)} wind {[ (emu.byte(0x70+i), emu.byte(0x84+i)) for i,t in enumerate(emu.ram(0x34F,12)) if t == 0x2E]} room {q.room:02X} mode {q.mode}")
    if q.room != s.room and q.mode == 5:
        break
emu.close()
