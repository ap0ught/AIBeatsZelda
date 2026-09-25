"""Walk into the visible stump cave on 0x1F and read what it pays - the community map calls it a
gambling cave, the guide's garbled text may mean it is the 100-rupee one. Look, don't guess."""
from zelda.emulator import BizHawk
from zelda.overworld import Navigator, NavError, LinkDied, read_room_item

emu = BizHawk(log_name="probe_1f_cave.log", clean_sram=False)
nav = Navigator(emu)
emu.load("ckpt_fullgame_l5w03_2d"); emu.wait(4)
s = nav.exit_screen("Up", at=120); s = nav.exit_screen("Right"); s = nav.exit_screen("Right")
before = emu.byte(0x66D)
print(f"on {s.room:02X} at ({s.x},{s.y}), rupees {before}", flush=True)
try:
    nav.go(lambda x, y: x == 96 and y in (141, 149), "below the stump cave", max_replans=40)
    st = emu.state()
    for _ in range(200):
        if st.mode in (0x0B, 0x10):
            break
        st = emu.step("Up", 1)
    for _ in range(400):
        st = emu.state()
        if st.mode == 0x0B and st.y > 150:
            break
        emu.step((), 2)
    for _ in range(120):
        emu.step((), 1)
    print("inside:", emu.state(), "| room item:", read_room_item(emu), flush=True)
    print("shot:", emu.screenshot("stump_cave_inside"), flush=True)
    for _ in range(400):
        st = emu.state()
        if emu.byte(0x66D) != before:
            break
        emu.step("Right" if st.x < 116 else "Left" if st.x > 124 else ("Up" if st.y > 140 else ()), 1)
    for _ in range(90):
        emu.step((), 1)
    print(f"RUPEES {before} -> {emu.byte(0x66D)} (+{emu.byte(0x66D) - before})", flush=True)
    print("shot:", emu.screenshot("stump_cave_after"), flush=True)
except (NavError, LinkDied) as e:
    print(f"FAILED: {type(e).__name__}: {str(e)[:90]}", flush=True)
emu.close()
