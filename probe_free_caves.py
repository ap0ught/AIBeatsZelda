"""Verify the three pre-candle caves from the Zelda Dungeon guide before re-routing through them.

  0x3D - 30 rupees, touch the Armos on the right (no item)
  0x2D - 30 rupees, bomb the rocks at the top (one screen east of 0x2C, which the route walks)
  0x0F - 100 rupees, no item: reached by walking UP from 0x1F, just right of the cave entrance there

For each: get there, open it, report the opening and screenshot it. Payouts come in a second probe
once the openings are confirmed, using bomb_cave_policy-style walk-north collection.
"""
from zelda.emulator import BizHawk
from zelda.overworld import Navigator, NavError, LinkDied, read_cells
from zelda import secrets

emu = BizHawk(log_name="probe_free_caves.log", clean_sram=False)
nav = Navigator(emu)


def show(tag):
    s = emu.state()
    print(f"   [{tag}] {s} | rupees {emu.byte(0x66D)} bombs {s.bombs}", flush=True)
    print("   shot:", emu.screenshot(f"freecave_{tag}"), flush=True)
    return s


# ---- 0x3D: Armos touch
print("\n== 0x3D (Armos, no item) ==", flush=True)
try:
    s = emu.load("ckpt_fullgame_l5w02_3d"); s = emu.wait(4)
    show("3d_arrive")
    print("   sweep(push):", secrets.sweep(emu, nav, methods=("push",)), flush=True)
except Exception as e:
    print("   FAILED:", type(e).__name__, str(e)[:100], flush=True)

# ---- 0x2D: bomb the top rocks
print("\n== 0x2D (bombs) ==", flush=True)
try:
    s = emu.load("ckpt_fullgame_l5w04_2c"); s = emu.wait(4)
    s = nav.exit_screen("Right")
    show("2d_arrive")
    print("   sweep(bomb):", secrets.sweep(emu, nav, methods=("bomb",)), flush=True)
except Exception as e:
    print("   FAILED:", type(e).__name__, str(e)[:100], flush=True)

# ---- 0x0F: via 0x1F, walking up
print("\n== 0x0F via 0x1F (no item) ==", flush=True)
try:
    s = emu.load("ckpt_fullgame_l5w05_1c"); s = emu.wait(4)
    for d in ("Right", "Right", "Right"):
        s = nav.exit_screen(d)
        print(f"   {d} -> {s.room:02X}", flush=True)
    show("1f_arrive")
    print("   opening on 0x1F:", secrets.opening(emu), flush=True)
    s = nav.exit_screen("Up")
    show("0f_arrive")
    print("   opening on 0x0F:", secrets.opening(emu), flush=True)
except Exception as e:
    print("   FAILED:", type(e).__name__, str(e)[:100], flush=True)
emu.close()
