"""After Ganon: look at the room, then validate the last three steps exactly as the run would use them,
each from the end of the previous one (random_search restores its own savestate per attempt, so the
winner is replayed forward into a scratch savestate before the next step starts).

  1. take the Triforce of Power (room item 0x0E; no inventory byte: Z_01 TakePowerTriforce only raises $509)
  2. go north into Zelda's room 0x32
  3. zelda_policy: sword the four guard fires ($3F), stand at X $70..$80 / Y $95, wait for mode $13

usage: python probe_ending.py [checkpoint]   (default ckpt_fullgame_g9_ganon)"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import sys
import fullgame
from zelda.emulator import BizHawk
from zelda.overworld import Navigator, read_enemies, read_room_item, read_cells
from zelda.search import random_search
from zelda import romdata

ckpt = sys.argv[1] if len(sys.argv) > 1 else "ckpt_fullgame_g9_ganon"
emu = BizHawk(log_name="probe_ending.log", clean_sram=False)
nav = Navigator(emu)


def look(tag):
    s = emu.state()
    print(f"[{tag}] {s} | mode byte {emu.byte(0x12):02X} fanfare {emu.byte(0x509):02X} cleared {emu.byte(0x34D):02X}", flush=True)
    if s.level:
        print("   ROM doors:", romdata.doors(s.level, s.room), flush=True)
    print("   objects:", [(e[0], hex(e[1]), e[2], e[3], e[4] >> 4) for e in read_enemies(emu)],
          "| room item:", read_room_item(emu), flush=True)
    print("   shot:", emu.screenshot(f"ending_{tag}"), flush=True)


def step(tag, state_in, policy, success, tries, max_frames):
    best = random_search(emu, state_in, policy, success, tries=tries, max_frames=max_frames,
                         label=f"probe {tag}", log=print, prefer_hearts=True, patience=3)
    if best is None:
        print(f"[{tag}] FAILED", flush=True)
        return None
    emu.load(state_in)
    for b in best.inputs:
        emu.step(b, 1)
    out = f"probe_ending_{tag}"
    emu.save(out)
    look(tag)
    return out


s = emu.load(ckpt); s = emu.wait(2)
look("start")
st = step("power", ckpt, fullgame.take_triforce_policy(nav),
          lambda e, q: q.hearts > 0 and q.room == 0x42 and read_room_item(e) is None, 12, 1500)
if st:
    st = step("north", st, fullgame.walk_out_policy(nav, "Up", 0x32),
              lambda e, q: q.hearts > 0 and q.room == 0x32 and q.mode == 5, 12, 1500)
if st:
    st = step("zelda", st, fullgame.zelda_policy(nav),
              lambda e, q: e.byte(0x12) == 0x13, 12, 4000)
if st:
    st = step("credits", st, fullgame.credits_policy(nav),
              lambda e, q: e.byte(0x12) == 0x13 and e.byte(0x13) == 4, 1, 20000)
print("DONE:", st, flush=True)
emu.close()
