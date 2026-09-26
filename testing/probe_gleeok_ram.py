"""B4: why does the Level 4 Gleeok fight burn its entire 6000-frame budget standing still?
All four logged attempts ended at 6012-6020 frames - the signature of a budget cap, not a fight.
Suspicion (from the audit): boss.gleeok_dead falls through to a stale-health scan, so the fight's
done() never returns True even though the boss is dead. Measure, don't guess: look at the object
table and the room-cleared flag at the END of the recorded fight, and at the start for contrast."""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import fullgame
from zelda.emulator import BizHawk
from zelda.overworld import read_enemies
from zelda import boss

names = [s[0] for s in fullgame.segments()]
before = names[names.index("gleeok") - 1]
emu = BizHawk(log_name="probe_gleeok.log", clean_sram=False)


def look(tag, ckpt):
    try:
        s = emu.load(ckpt)
    except Exception as e:
        print(f"[{tag}] cannot load {ckpt}: {str(e)[:70]}", flush=True)
        return
    s = emu.wait(2)
    ts, hp = emu.ram(0x34F, 12), emu.ram(0x485, 12)
    print(f"[{tag}] {ckpt}\n   {s}", flush=True)
    print(f"   room-cleared $034D = {emu.byte(0x34D):02X}", flush=True)
    print("   slots:", [(i, f"{ts[i]:02X}", hp[i] >> 4) for i in range(12) if ts[i] or hp[i]], flush=True)
    print("   read_enemies:", [(e[0], hex(e[1]), e[4] >> 4) for e in read_enemies(emu)], flush=True)
    for fn in ("gleeok_dead", "gleeok_parts"):
        f = getattr(boss, fn, None)
        if f:
            try:
                print(f"   boss.{fn}() = {f(emu)}", flush=True)
            except Exception as e:
                print(f"   boss.{fn}() raised {str(e)[:60]}", flush=True)
    print("   shot:", emu.screenshot(f"gleeok_{tag}"), flush=True)


look("start", f"ckpt_fullgame_{before}")
look("end", "ckpt_fullgame_gleeok")
emu.close()
