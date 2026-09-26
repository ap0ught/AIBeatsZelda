"""Why did every whirlwind attempt fail on Spectacle Rock? Replay whirl_to_policy's exact steps
from the x9_out checkpoint, logging the state every 20 frames and photographing each play."""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
from zelda.emulator import BizHawk
from zelda.overworld import Navigator, read_enemies
from zelda import bot

emu = BizHawk(log_name="probe_whirl.log", clean_sram=False)
nav = Navigator(emu)
s = emu.load("ckpt_fullgame_x9_out"); s = emu.wait(4)
print("start:", s, "| B item", bot.b_item(emu), "| recorder $065C", emu.byte(0x65C), flush=True)
print("enemies:", [(hex(e[1]), e[2], e[3]) for e in read_enemies(emu)], flush=True)
print("shot:", emu.screenshot("whirl_0_start"), flush=True)
print("select recorder:", bot.select_b_item(emu, emu.step, bot.B_RECORDER),
      "| B item now", bot.b_item(emu), flush=True)
for play in range(1, 10):
    st = emu.state()
    if st.y > 200:
        emu.step("Up", 40)
    elif st.y < 80:
        emu.step("Down", 40)
    if st.x < 24:
        emu.step("Right", 24)
    elif st.x > 216:
        emu.step("Left", 24)
    st = emu.state()
    start = st.room
    print(f"play {play}: before B -> {st}", flush=True)
    emu.step("B", 2)
    trace = []
    for k in range(30):
        q = emu.step((), 20)
        trace.append(f"{q.room:02X}/{q.mode:02X}/({q.x},{q.y})/{q.hearts}")
        if k == 3:
            print("  shot:", emu.screenshot(f"whirl_{play}_playing"), flush=True)
        if q.room != start and q.mode == 5:
            break
    emu.step((), 60)
    q = emu.state()
    print("  trace:", " ".join(trace), flush=True)
    print("  after:", q, flush=True)
    print("  shot:", emu.screenshot(f"whirl_{play}_after"), flush=True)
    if q.room == 0x37 or q.hearts <= 0:
        break
emu.close()
