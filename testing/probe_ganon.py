"""Survey Ganon before trusting ganon_policy. The generic tactics.survey measures health going DOWN,
and Ganon's does not behave that way: four Magical Sword hits refill his HP to $F0 and turn him brown
(disassembly: Z_04 Ganon_CheckCollisions). So this probe watches his own state bytes instead.

Part 1 - a trace with Link standing still (from an in-memory savestate, not recorded): scene phase
$445, Ganon's slot, ObjState $AC+slot (0 blue, nonzero brown countdown), ObjTimer $28+slot (0 =
invisible and hittable), HP $485+slot, position, and Ganon_ObjPhase $42C+slot.
Part 2 - ganon_policy through random_search exactly as the run would use it.

usage: python probe_ganon.py <checkpoint-state-name> [tries]"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import sys
import fullgame
from zelda.emulator import BizHawk
from zelda.overworld import Navigator
from zelda.search import random_search

ckpt = sys.argv[1]
tries = int(sys.argv[2]) if len(sys.argv) > 2 else 6
emu = BizHawk(log_name="probe_ganon.log", clean_sram=False)
nav = Navigator(emu)
s = emu.load(ckpt); s = emu.wait(2)
print("state:", s, "| bombs", s.bombs, "rupees", s.rupees, "arrows", emu.byte(0x659), flush=True)
snap = emu.msave()
try:
    last = None
    for f in range(900):
        sl = fullgame.ganon_slot(emu)
        row = (emu.byte(0x445),) + ((sl, emu.byte(0xAC + sl), emu.byte(0x28 + sl), emu.byte(0x485 + sl),
                                     emu.byte(0x70 + sl), emu.byte(0x84 + sl), emu.byte(0x42C + sl))
                                    if sl is not None else (None,))
        key = row[:4] if sl is not None else row
        if key != last:
            st = emu.state()
            print(f"  f+{f:3d} scene {row[0]} " + (f"slot {row[1]} state {row[2]:02X} timer {row[3]:02X} "
                  f"hp {row[4]:02X} at ({row[5]},{row[6]}) phase {row[7]:02X}" if sl is not None else "no Ganon")
                  + f" | Link ({st.x},{st.y}) hp {st.hearts}", flush=True)
            last = key
        if emu.state().hearts <= 0:
            print("  Link died standing still", flush=True)
            break
        emu.step((), 1)
finally:
    emu.mload(snap)
    emu.mfree(snap)

best = random_search(emu, ckpt, fullgame.ganon_policy(nav),
                     lambda e, st: st.hearts > 0 and fullgame.ganon_dead(e),
                     tries=tries, max_frames=12000, label="probe ganon", log=print, prefer_hearts=True, patience=3)
print("BEST:", None if best is None else (best.frames, best.hearts), flush=True)
emu.close()
