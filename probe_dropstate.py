"""Read the game's drop bookkeeping at a checkpoint (addresses from aldonunez/zelda1-disassembly
Variables.inc): WorldKillCycle $52A picks the drop-table column, HelpDropCount $50 / HelpDropValue $51
make the tenth-kill forced drop, WorldKillCount $627. usage: python probe_dropstate.py <ckpt>"""
import sys
from zelda.emulator import BizHawk
from zelda.overworld import read_enemies
ckpt = sys.argv[1]
emu = BizHawk(log_name="probe_drop.log", clean_sram=False)
s = emu.load(ckpt); s = emu.wait(30)
print("state:", s, "| bombs", s.bombs, "rupees", s.rupees)
print(f"WorldKillCycle={emu.byte(0x52A)} HelpDropCount={emu.byte(0x50)} HelpDropValue={emu.byte(0x51)} "
      f"WorldKillCount={emu.byte(0x627)} RoomKillCount={emu.byte(0x34F)}")
print("enemies:", [(e[0], hex(e[1]), e[2], e[3], e[4] >> 4) for e in read_enemies(emu)])
emu.close()
