"""Room 0x25's bomb pile sits in the MIDDLE lane, walled in by two full columns of blocks and the
unopened north and south bombable walls; Link enters from the east into the right lane. Test the
two ways in that need no bomb: the boomerang (it fetches items) and pushing a block of the
right-hand column."""
import random
from zelda.emulator import BizHawk
from zelda.overworld import Navigator, read_cells, read_room_item
from zelda.lookahead import plan_fight
from zelda.search import nudge_into_room
from zelda import bot
try:
    from zelda.search import Recorder
except ImportError:
    from zelda.runner import Recorder

emu = BizHawk(log_name="probe_25_reach.log", clean_sram=False)
nav = Navigator(emu)
emu.load("ckpt_fullgame_s9_25"); emu.wait(2)
rec = Recorder(emu)
rng = random.Random(1000)
rec.step((), rng.randint(0, 20))
nudge_into_room(emu, rec.step)
bot.select_b_item(emu, rec.step, bot.B_BOW)
res = plan_fight(emu, rec, max_frames=4500, rng=rng, log=True, use_bow=True,
                 miss_penalty=0.0, hp_weight=140.0)
for _ in range(14):
    if read_room_item(emu) is not None:
        break
    rec.step((), 8)
s = emu.state()
print("cleared:", res, s, "| item:", read_room_item(emu), "| bombs:", s.bombs, flush=True)
root = emu.msave()


def go(x, y):
    try:
        nav.go(lambda px, py: abs(px - x) <= 1 and abs(py - y) <= 1, f"({x},{y})",
               optimistic=True, max_replans=40)
        return True
    except Exception as e:
        print("   could not reach", (x, y), type(e).__name__, str(e)[:60], flush=True)
        return False


B_BOOM = getattr(bot, "B_BOOMERANG", 0)
# A. the boomerang, thrown left from the right lane level with the item
for (x, y) in ((160, 141), (160, 149), (160, 133)):
    emu.mload(root); emu.wait(2)
    if not go(x, y):
        continue
    sel = bot.select_b_item(emu, emu.step, B_BOOM)
    b0 = emu.state().bombs
    emu.step("Left", 1); emu.step("B", 2); emu.wait(90)
    q = emu.state()
    print(f"A boomerang from ({x},{y}): selected={sel} B-item={emu.byte(0x656)} "
          f"bombs {b0}->{q.bombs} item now {read_room_item(emu)}", flush=True)
    if q.bombs > b0:
        print("   shot:", emu.screenshot("room25_boomerang_ok"), flush=True)
        break
# B. push each block of the right-hand column (c16 = 9) toward the left, from the right lane
for r16 in range(2, 9):
    emu.mload(root); emu.wait(2)
    y = 64 + r16 * 16 - 3
    before = read_cells(emu)
    if not go(160, y):
        continue
    for _ in range(20):
        emu.step("Left", 6)
    after = read_cells(emu)
    moved = before[r16 * 2][9 * 2] != after[r16 * 2][9 * 2]
    print(f"B push block at row {r16} (y={y}) leftward: moved={moved}", flush=True)
    if moved:
        print("   shot:", emu.screenshot(f"room25_push_row{r16}"), flush=True)
        break
emu.mfree(root)
emu.close()
