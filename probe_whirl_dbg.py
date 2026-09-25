import sys
from zelda.emulator import BizHawk
from zelda import bot
from zelda.overworld import read_enemies
emu = BizHawk(log_name="probe_whirl_dbg.log", clean_sram=False)
s = emu.load(sys.argv[1]); emu.step((), 2)
print("room", hex(s.room), "pos", (s.x, s.y), "idx", emu.byte(0x523), "tri", hex(emu.byte(0x671)), "enemies", [(e[0], hex(e[1])) for e in read_enemies(emu)])
print("types slots 0..12:", [hex(t) for t in emu.ram(0x34F, 13)])
bot.select_b_item(emu, emu.step, bot.B_RECORDER)
face = sys.argv[2]
emu.step(face, 1); emu.step("B", 2)
seq = []
for f in range(400):
    q = emu.step((), 1)
    ts = emu.ram(0x34F, 13)
    seq.append((emu.byte(0x3C), emu.byte(0x508), emu.byte(0x522), 0x2E in ts, q.room, q.x, emu.byte(0xAC)))
    if q.room != s.room and q.mode == 5 and emu.byte(0x522) == 0:
        print("landed at frame", f, "room", hex(q.room), "pos", (q.x, q.y)); break
for f in (0, 1, 2, 50, 100, 150, 151, 152, 153, 155, 160, 200, 250, 300, 350, 399):
    if f < len(seq): print(f, "flute,summoned,teleport,wind,room,x,linkstate =", seq[f])
print("idx now", emu.byte(0x523))
emu.close()
