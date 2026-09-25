"""Validate the ride_dock fix on the real case that broke it: Level 4's island (0x45) to the lake
screen (0x55). It should return only once Link has stopped moving on the pier - not the moment the
screen changes - and a path down off the pier should exist from where he lands."""
from zelda.emulator import BizHawk
from zelda.overworld import Navigator, plan, read_cells, EDGE_GOALS
from zelda import bot

emu = BizHawk(log_name="probe_ride_dock.log", clean_sram=False)
nav = Navigator(emu)
s = emu.load("ckpt_fullgame_rb_w45"); s = emu.wait(4)
print("start:", s, flush=True)
s = bot.ride_dock(nav, log=lambda *a: print(*a, flush=True))
print("ride_dock returned:", s, flush=True)
a = emu.state(); emu.wait(20); b = emu.state()
print("20 frames later:", b, "| still moving:", (a.x, a.y) != (b.x, b.y), flush=True)
p = plan(read_cells(emu), nav.kb, (b.x, b.y), EDGE_GOALS["Down"], optimistic=True)
print("plan Down from the landing:", None if p is None else f"{len(p)} steps", flush=True)
print("VERDICT:", "PASS" if (b.room == 0x55 and b.y >= 125 and (a.x, a.y) == (b.x, b.y) and p) else "FAIL", flush=True)
print("shot:", emu.screenshot("ride_dock_landed"), flush=True)
emu.close()
