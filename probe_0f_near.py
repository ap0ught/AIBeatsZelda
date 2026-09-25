"""The guide: on 0x1F, move around the top JUST RIGHT of the cave entrance and you go up to the next
screen (0x0F, the 100-rupee cave). The stump's door is at x=96; the last probe only tried x>=136."""
from zelda.emulator import BizHawk
from zelda.overworld import Navigator, NavError, LinkDied
from zelda import secrets

emu = BizHawk(log_name="probe_0f_near.log", clean_sram=False)
nav = Navigator(emu)
emu.load("ckpt_fullgame_l5w03_2d"); emu.wait(4)
s = nav.exit_screen("Up", at=120); s = nav.exit_screen("Right"); s = nav.exit_screen("Right")
print(f"on {s.room:02X} at ({s.x},{s.y})", flush=True)
snap = emu.msave()
found = False
for col in (104, 112, 120, 128, 88, 80):
    emu.mload(snap)
    try:
        s = nav.exit_screen("Up", at=col)
        print(f"  Up at x={col}: REACHED {s.room:02X} at ({s.x},{s.y}) hearts {s.hearts}", flush=True)
        print("  opening on arrival:", secrets.opening(emu), flush=True)
        print("  shot:", emu.screenshot(f"probe_0f_reached_{col}"), flush=True)
        found = True
        break
    except (NavError, LinkDied) as e:
        print(f"  Up at x={col}: {str(e)[:60]}", flush=True)
if not found:
    # the navigator may simply not believe the gap exists: hold Up by hand along the top near the door
    for col in (104, 112, 120, 128):
        emu.mload(snap)
        try:
            nav.go(lambda x, y: x == col and y <= 93, f"top of the screen at x={col}", optimistic=True, max_replans=40)
        except (NavError, LinkDied):
            pass
        st = emu.state()
        for _ in range(120):
            if st.room != 0x1F:
                break
            st = emu.step("Up", 1)
        print(f"  hand-held Up from x={col}: now {st.room:02X} at ({st.x},{st.y})", flush=True)
        if st.room != 0x1F:
            print("  shot:", emu.screenshot(f"probe_0f_hand_{col}"), flush=True)
            break
emu.mfree(snap)
emu.close()
