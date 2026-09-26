"""Sweep an overworld screen for its hidden entrance.  usage: find_secret.py <checkpoint> [dirs...]"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import sys
from zelda.emulator import BizHawk
from zelda.overworld import Navigator
from zelda import secrets

ckpt = sys.argv[1]
methods = tuple(sys.argv[2].split(",")) if len(sys.argv) > 2 else ("bomb", "push", "burn")
dirs = sys.argv[3:]
emu = BizHawk(log_name="find_secret.log", clean_sram=False)
nav = Navigator(emu)
s = emu.load(ckpt); s = emu.wait(4)
for d in dirs:
    s = nav.exit_screen(d)
print("screen", f"{s.room:02X}", s)
print(secrets.sweep(emu, nav, methods=methods))
emu.close()
