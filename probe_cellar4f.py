"""Why did s9_silver fail? 33 attempts 'no item' in cellar 0x4F, 5 'item' but still in the cellar,
2 'item' back in room 0x10 that still failed the Silver Arrow check ($0659 >= 2). Look at the RAM
directly instead of trusting either the pickup detector or my assumption about $0659."""
import random
import fullgame
from zelda.emulator import BizHawk
from zelda.overworld import Navigator, read_cells, read_enemies
try:
    from zelda.search import Recorder
except ImportError:
    from zelda.runner import Recorder

emu = BizHawk(log_name="probe_cellar4f.log", clean_sram=False)
nav = Navigator(emu)
s = emu.load("ckpt_fullgame_s9_10_st"); s = emu.wait(4)


def inv(tag):
    b = emu.ram(0x656, 26)
    print(f"  [{tag}] inventory $0656..$066F:", " ".join(f"{x:02X}" for x in b),
          f"| $0659 arrows={emu.byte(0x659):02X} $065A bow={emu.byte(0x65A):02X}", flush=True)


print("start:", s, flush=True)
inv("start")
cells = read_cells(emu)
ids = sorted({cells[r][c] for r in range(22) for c in range(32)})
print("cellar tile ids:", " ".join(f"{i:02X}" for i in ids), flush=True)
for r in range(22):
    print("   " + "".join("#" if cells[r][c] == 0xFA else "=" if cells[r][c] == 0x6F else "." if cells[r][c] == 0x24 else "?"
                          for c in range(32)), flush=True)
print("objects (type,x,y,hp):", [(hex(e[1]), e[2], e[3], e[4] >> 4) for e in read_enemies(emu)], flush=True)
ts = emu.ram(0x34F, 20); xs = emu.ram(0x70, 20); ys = emu.ram(0x84, 20)
print("all slots:", [(i, f"{ts[i]:02X}", xs[i], ys[i]) for i in range(20) if ts[i]], flush=True)
print("item slot $AB/$83/$97/$BF:", f"{emu.byte(0xAB):02X}", emu.byte(0x83), emu.byte(0x97), f"{emu.byte(0xBF):02X}", flush=True)
print("shot:", emu.screenshot("cellar4f_start"), flush=True)

for seed in (1000, 1001, 1002):
    emu.load("ckpt_fullgame_s9_10_st"); emu.wait(2)
    rec = Recorder(emu)
    watch = {}
    real = rec.step
    def traced(buttons=(), frames=1, real=real):
        q = real(buttons, frames)
        v = emu.byte(0x659)
        if watch.get("last") != v:
            print(f"    frame {q.frame}: $0659 -> {v:02X} at room {q.room:02X} mode {q.mode:02X} ({q.x},{q.y})", flush=True)
            watch["last"] = v
        return q
    rec.step = traced
    out = fullgame.cellar_item_policy(nav, 0x659)(emu, rec, random.Random(seed), 3000)
    q = emu.state()
    print(f"seed {seed}: outcome={out} | end {q}", flush=True)
    inv(f"seed {seed} end")
    print("  shot:", emu.screenshot(f"cellar4f_end_{seed}"), flush=True)
emu.close()
