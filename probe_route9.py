import sys
from zelda.emulator import BizHawk
from zelda.overworld import Navigator
from zelda.explorer import Explorer
ckpt, target, budget = sys.argv[1], int(sys.argv[2], 16), int(sys.argv[3])
emu = BizHawk(log_name="probe_route9.log", clean_sram=False)
nav = Navigator(emu)
ex = Explorer(emu, nav)
try:
    print("ROUTE:", ex.route(target, ckpt, max_nodes=budget))
except Exception as e:
    print("FAILED:", type(e).__name__, str(e)[:120])
emu.close()
