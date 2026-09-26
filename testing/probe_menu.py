"""Measure the subscreen: how many frames to open, per cursor move, and to close."""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
from zelda.emulator import BizHawk
from zelda import bot
emu = BizHawk(log_name="probe_menu.log", clean_sram=False)
s = emu.load("ckpt_fullgame_l8_3b")
emu.step((), 2)
print("start bitem", bot.b_item(emu), "menu", emu.byte(0xE1), "mode", s.mode)
emu.step("Start", 1)
seq = []
for f in range(80):
    emu.step((), 1)
    seq.append(emu.byte(0xE1))
print("MenuState after Start:", seq)
opened = next(i for i, v in enumerate(seq) if v == seq[-1])
print("stable from frame", opened, "value", seq[-1])
# cursor moves: press Right 1 frame, then count frames until b_item changes
for k in range(4):
    b0 = bot.b_item(emu)
    emu.step("Right", 1)
    n = 0
    while bot.b_item(emu) == b0 and n < 30:
        emu.step((), 1); n += 1
    print(f"  move {k}: b_item {b0} -> {bot.b_item(emu)} after {n} extra frames")
# minimal spacing: alternate Right 1 frame / nothing 1 frame
b0 = bot.b_item(emu)
for k in range(6):
    emu.step("Right", 1); emu.step((), 1)
print("6 x (Right 1, none 1):", b0, "->", bot.b_item(emu))
emu.step("Start", 1)
seq = []
for f in range(80):
    st = emu.step((), 1)
    seq.append((emu.byte(0xE1), st.mode))
closed = next(i for i, v in enumerate(seq) if v[0] == 0)
print("MenuState after closing Start:", [v[0] for v in seq][:closed + 3], "closed at", closed)
x0 = emu.state().x
st = emu.step("Left", 4)
print("moved after close:", x0, "->", st.x)
emu.close()
