"""Show the secret finder's blind spot, with screenshots, on the one rock we KNOW opens.

Screen 05 is Spectacle Rock. This run already blew its door open to get into Level 9 - stand at
(80,173), face up, one bomb. Do exactly that from the same savestate, photograph it, and ask both
detectors about the very same frame.
"""
import random
from zelda.emulator import BizHawk
from zelda.overworld import Navigator, read_cells
from zelda.lookahead import plan_reach, Goal
from zelda import secrets, bot

emu = BizHawk(log_name="show_problem.log", clean_sram=False)
nav = Navigator(emu)
s = emu.load("ckpt_fullgame_n9_b05"); s = emu.wait(4)
print("start:", s, "bombs", s.bombs, flush=True)
print("shot:", emu.screenshot("problem_1_spectacle_rock_before"), flush=True)
base = read_cells(emu)

res = "not tried"
for seed in range(10):
    root = emu.msave()
    res = plan_reach(emu, None, Goal(80, 173, 6), max_frames=4000, rng=random.Random(seed))
    if res == "arrived":
        emu.mfree(root)
        break
    emu.mload(root); emu.mfree(root); emu.wait(2)
print("reach the known spot:", res, emu.state(), flush=True)
print("shot:", emu.screenshot("problem_2_at_the_known_spot"), flush=True)

print("select bombs:", bot.select_b_item(emu, emu.step, bot.B_BOMBS), flush=True)
emu.step("Up", 1); emu.step("B", 2); emu.wait(160)
print("shot:", emu.screenshot("problem_3_after_the_bomb"), flush=True)

after = read_cells(emu)
new24 = [(r, c) for r in range(22) for c in range(32) if after[r][c] == 0x24 and base[r][c] != 0x24]
print("cells that turned into black doorway 0x24:", new24, flush=True)
print("  ...with the 0xF3 arch above them (what the old finder demands):",
      [(r, c) for r, c in new24 if r > 0 and after[r - 1][c] == 0xF3], flush=True)
print("OLD detector, opening(emu):       ", secrets.opening(emu), flush=True)
print("NEW detector, opening(emu, before):", secrets.opening(emu, base), flush=True)
emu.close()
