"""Screen 2C: the giant rock three sources say hides a heart container. Sweep it again, now
that the detector can see a bombed doorway at all."""
from zelda.emulator import BizHawk
from zelda.overworld import Navigator
from zelda import secrets

emu = BizHawk(log_name="show_2c.log", clean_sram=False)
nav = Navigator(emu)
s = emu.load("ckpt_fullgame_c8_2d"); s = emu.wait(4)
s = nav.exit_screen("Left")
print("screen", f"{s.room:02X}", s, "bombs", s.bombs, flush=True)
print("shot:", emu.screenshot("problem_4_giant_rock_2c"), flush=True)
print("sweep:", secrets.sweep(emu, nav, methods=("bomb",)), flush=True)
emu.close()
