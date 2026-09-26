import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import ast, pathlib
p = pathlib.Path("fullgame.py"); raw = p.read_bytes(); crlf = b"\r\n" in raw
t = raw.decode("utf-8").replace("\r\n", "\n")
def sub(old, new, what):
    global t
    assert t.count(old) == 1, (what, t.count(old)); t = t.replace(old, new); print("  applied:", what)
sub('''    S.append(("l5_47_key",  lambda nav: make_clear_grab_policy(nav, "Up"), ok(0x37), 60))''',
    '''    S.append(("l5_47_key",  lambda nav: make_clear_grab_policy(nav, "Up"), ok_gain(0x37, keys=1), 60))''', "l5_47_key insists on the key")
sub('''    S.append(("l5_27_key",  lambda nav: make_grab_policy(nav, "Left"),     ok(0x26), 50))''',
    '''    S.append(("l5_27_key",  lambda nav: make_grab_policy(nav, "Left"),
              lambda emu, s: s.room == 0x26 and s.mode == 5 and s.hearts > 0 and s.keys >= started().keys, 50))''', "l5_27_key nets a key")
sub('''    S.append(("l5_26_key",  lambda nav: make_clear_grab_policy(nav, "Left"), ok(0x25), 60))''',
    '''    S.append(("l5_26_key",  lambda nav: make_clear_grab_policy(nav, "Left"), ok_gain(0x25, keys=1), 60))''', "l5_26_key insists on the key")
import re
m = re.search(r'    S\.append\(\("l7_1c",[^\n]*\n(?:              [^\n]*\n)?', t)
print(repr(m.group(0)))
p.write_bytes((t.replace("\n", "\r\n") if crlf else t).encode("utf-8"))
