"""Why can't Link reach room 0x25's bomb pile once the bow has cleared the room? Clear it the same
way bow_clear_grab_policy does, then dump the item position, the tile map, what is still alive,
and a screenshot."""
import random
from zelda.emulator import BizHawk
from zelda.overworld import Navigator, read_cells, read_enemies, read_room_item
from zelda.lookahead import plan_fight
from zelda.search import nudge_into_room
from zelda import bot
try:
    from zelda.search import Recorder
except ImportError:
    from zelda.runner import Recorder

emu = BizHawk(log_name="probe_25_item.log", clean_sram=False)
nav = Navigator(emu)
for seed in (1000, 1001, 1002):
    emu.load("ckpt_fullgame_s9_25"); emu.wait(2)
    rec = Recorder(emu)
    rng = random.Random(seed)
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
    item = read_room_item(emu)
    print(f"seed {seed}: fight={res} | {s} | item={item}", flush=True)
    print("  still alive:", [(hex(e[1]), e[2], e[3], e[4] >> 4) for e in read_enemies(emu)], flush=True)
    if item is not None:
        cells = read_cells(emu)
        print("  tile map (16x11, top-left cell of each tile):", flush=True)
        for r16 in range(11):
            print("   ", f"{r16:2d}", " ".join(f"{cells[r16*2][c16*2]:02X}" for c16 in range(16)), flush=True)
        print("  shot:", emu.screenshot(f"room25_item_{seed}"), flush=True)
        break
emu.close()
