"""Replay a run's input log from power-on and print when Link first enters a given (level, room) in normal play,
and when he leaves it. usage: python youtube/find_room.py <inputs.txt> <level> <roomhex> [label]"""
import sys
sys.path.insert(0, ".")
from zelda import replay
from zelda.emulator import BizHawk
src, level, room = sys.argv[1], int(sys.argv[2]), int(sys.argv[3], 16)
inp = replay.load_inputs(src)
emu = BizHawk(log_name="find_room.log")
inside = None; visits = []
for k, b in enumerate(inp):
    s = emu.step(b, 1)
    here = (s.level == level and s.room == room and s.mode == 5)
    if here and inside is None:
        inside = k
    elif not here and inside is not None and s.mode == 5 and s.room != room:
        visits.append((inside, k)); inside = None
    if k % 20000 == 0:
        print("  at frame", k, flush=True)
if inside is not None:
    visits.append((inside, len(inp)))
print("VISITS", src, f"L{level} {room:02X}:", visits, flush=True)
emu.close()
