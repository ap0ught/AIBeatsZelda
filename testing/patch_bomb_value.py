"""Bombs are worth frames. The search ranked attempts by hearts and frames only, so of sixty attempts at a room
the one that happened to pick up four bombs had no edge over the one that did not - and the fourth run reached
Level 7 with none. Each bomb in hand (up to BOMB_CAP) now counts BOMB_VALUE frames in the ranking, and the
lossless OverBudget cut allows for the bombs an attempt might still collect."""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import pathlib

p = pathlib.Path("zelda/search.py")
t = p.read_text(encoding="utf-8")

old = """    hearts: float = 0.0
    note: str = ""
"""
new = """    hearts: float = 0.0
    note: str = ""
    bombs: int = 0
"""
assert t.count(old) == 1
t = t.replace(old, new)

old = """def value_of(a, containers: float) -> float:"""
new = """BOMB_VALUE = [220]             # frames one more bomb in hand is worth to the ranking (a wall bombed saves 500+)
BOMB_CAP = [8]                 # ...up to this many


def _bomb_worth(a) -> float:
    return BOMB_VALUE[0] * min(getattr(a, "bombs", 0) or 0, BOMB_CAP[0])


def value_of(a, containers: float) -> float:"""
assert t.count(old) == 1
t = t.replace(old, new)

old = """    if HEARTS_FREE[0]:
        return -a.frames + (200 if h >= 2 else 0)
    v = 600 * min(h, 4) + 300 * max(0.0, min(h, 7) - 4) + 120 * max(0.0, h - 7)
    cliff = min(4.0, max(1.5, 0.5 * containers))
    if h < cliff:
        v -= (cliff - h) * 4000
    return v - a.frames
"""
new = """    if HEARTS_FREE[0]:
        return -a.frames + (200 if h >= 2 else 0) + _bomb_worth(a)
    v = 600 * min(h, 4) + 300 * max(0.0, min(h, 7) - 4) + 120 * max(0.0, h - 7)
    cliff = min(4.0, max(1.5, 0.5 * containers))
    if h < cliff:
        v -= (cliff - h) * 4000
    return v - a.frames + _bomb_worth(a)
"""
assert t.count(old) == 1
t = t.replace(old, new)

old = """        c = st["containers"]
        _Full.hearts = c
        return int(value_of(_Full, c) - value_of(b, c))
"""
new = """        c = st["containers"]
        _Full.hearts = c
        _Full.bombs = min(BOMB_CAP[0], st.get("b0", 0) + 4)     # ...and one drop of bombs it might still pick up
        return int(value_of(_Full, c) - value_of(b, c))
"""
assert t.count(old) == 1
t = t.replace(old, new)

old = """            a = Attempt(1000 + i, rec.inputs, len(rec.inputs), ok, s.hearts, outcome)
            with lock:"""
new = """            a = Attempt(1000 + i, rec.inputs, len(rec.inputs), ok, s.hearts, outcome, s.bombs)
            with lock:"""
assert t.count(old) == 1
t = t.replace(old, new)

old = """        a = Attempt(seed, rec.inputs, len(rec.inputs), ok, s.hearts, outcome)"""
new = """        a = Attempt(seed, rec.inputs, len(rec.inputs), ok, s.hearts, outcome, s.bombs)"""
assert t.count(old) == 1
t = t.replace(old, new)
old = """            s_start = emu.load(state_name)
            rec = Recorder(emu)
            rec.step((), 2)
            if setup:
                setup(rec, nav)
            rec.cap = cutoff"""
new = """            s_start = emu.load(state_name)
            st.setdefault("b0", s_start.bombs)
            rec = Recorder(emu)
            rec.step((), 2)
            if setup:
                setup(rec, nav)
            rec.cap = cutoff"""
assert t.count(old) == 1
t = t.replace(old, new)
p.write_text(t, encoding="utf-8")
print("patched search: bombs count in the ranking")
