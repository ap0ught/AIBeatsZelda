"""Replay one segment of the archived fourth run from its own checkpoint state and print what happened:
every `every` frames - Link, the buttons held, and the live threats. usage: python replay_seg.py <seg> [every]"""
import json, pathlib, sys
from zelda import replay
from zelda.emulator import BizHawk
from zelda.overworld import Navigator, enemy_name
ARCH = pathlib.Path("logs/archive/fourth_run_20260919")
INPUTS = replay.load_inputs(ARCH / "fullgame.inputs.txt")
seg = sys.argv[1]; every = int(sys.argv[2]) if len(sys.argv) > 2 else 8
order = sorted(((json.load(open(f))["frames"], f.stem[9:]) for f in (ARCH / "checkpoints").glob("fullgame_*.json")))
names = [n for _, n in order]; ends = dict((n, fr) for fr, n in order)
i = names.index(seg); prev = names[i - 1]; a, b = ends[prev], ends[seg]
emu = BizHawk(log_name="replay_seg.log", clean_sram=False); nav = Navigator(emu)
s = emu.load(f"run4/ckpt_fullgame_{prev}")
print(f"{seg}: frames {a}..{b} ({b - a}); starts L{s.level} room {s.room:02X} at ({s.x},{s.y}) hearts {s.hearts}")
for k in range(a, b):
    s = emu.step(INPUTS[k], 1)
    if (k - a) % every == 0:
        th = nav.threats() if s.mode == 5 else []
        print(f"  {k - a:4d} m{s.mode} ({s.x:3d},{s.y:3d}) {','.join(INPUTS[k]) or '-':8s} h{s.hearts} | "
              + " ".join(f"{enemy_name(e[1])[:8]}@({e[2]},{e[3]})" for e in th))
emu.close()
