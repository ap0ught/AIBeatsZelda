"""Stop an attempt the moment it can no longer beat the best one.

An attempt's value is (what its hearts are worth) - frames, and hearts are capped by the containers, so once
an attempt has run   frames >= value(full health) - value(best)   it has lost whatever happens next. Level 8's
Gleeok was the case that hurt: a 1,985-frame win on the board and every other scout still grinding its
6,000-frame budget, ten minutes an attempt. The cut is lossless - it never removes an attempt that could
have won - and it is evaluated live, so a better best tightens every attempt already running."""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import pathlib

p = pathlib.Path("zelda/search.py")
t = p.read_text(encoding="utf-8")

old = '''class Recorder:
    """Wraps an emulator so a policy's steps are captured as an input list."""

    def __init__(self, emu: BizHawk):
        self.emu = emu
        self._raw_step = emu.step          # bound now, so patching emu.step later can't recurse
        self.inputs: list = []

    def step(self, buttons=(), frames: int = 1) -> State:
        if isinstance(buttons, str):
            buttons = tuple(b for b in buttons.split(",") if b)
        self.inputs.extend([tuple(buttons)] * frames)
        return self._raw_step(buttons, frames)
'''
new = '''class OverBudget(BaseException):
    """This attempt cannot beat the best any more. BaseException on purpose: no policy's `except Exception`
    may swallow it, while every `finally` (the emu.step restores) still runs."""


class Recorder:
    """Wraps an emulator so a policy's steps are captured as an input list."""

    def __init__(self, emu: BizHawk):
        self.emu = emu
        self._raw_step = emu.step          # bound now, so patching emu.step later can't recurse
        self.inputs: list = []
        self.cap = None                    # callable -> frame count past which this attempt has already lost

    def step(self, buttons=(), frames: int = 1) -> State:
        if isinstance(buttons, str):
            buttons = tuple(b for b in buttons.split(",") if b)
        if self.cap is not None:
            limit = self.cap()
            if limit is not None and len(self.inputs) + frames > limit:
                raise OverBudget()
        self.inputs.extend([tuple(buttons)] * frames)
        return self._raw_step(buttons, frames)
'''
assert t.count(old) == 1
t = t.replace(old, new)

old2 = '''            rng = random.Random(1000 + i)
            s_start = emu.load(state_name)
            rec = Recorder(emu)
            rec.step((), 2)
            if setup:
                setup(rec, nav)
            try:
                outcome = policy(emu, rec, rng, max_frames)
            except LinkDied:
                outcome = "died"
'''
new2 = '''            rng = random.Random(1000 + i)
            s_start = emu.load(state_name)
            rec = Recorder(emu)
            rec.step((), 2)
            if setup:
                setup(rec, nav)
            rec.cap = cutoff
            step0 = emu.step
            try:
                outcome = policy(emu, rec, rng, max_frames)
            except OverBudget:
                outcome = "over budget"
                emu.step = step0               # belt and braces: a policy without a finally
            except LinkDied:
                outcome = "died"
'''
assert t.count(old2) == 1
t = t.replace(old2, new2)

old3 = '''    def work(k):
        emu, nav = scouts[k], navs[k]
        policy = factory(nav)
'''
new3 = '''    class _Full:                       # the best any attempt could still do: full health, no frames
        frames = 0

    def cutoff():
        b = st["best"]
        if b is None:
            return None
        c = st["containers"]
        _Full.hearts = c
        return int(value_of(_Full, c) - value_of(b, c))

    def work(k):
        emu, nav = scouts[k], navs[k]
        policy = factory(nav)
'''
assert t.count(old3) == 1
t = t.replace(old3, new3)

old4 = '''            a = Attempt(1000 + i, rec.inputs, len(rec.inputs), ok, s.hearts, outcome)
            with lock:'''
new4 = '''            if outcome == "over budget":
                ok = False
            a = Attempt(1000 + i, rec.inputs, len(rec.inputs), ok, s.hearts, outcome)
            with lock:'''
assert t.count(old4) == 1
t = t.replace(old4, new4)
p.write_text(t, encoding="utf-8")
print("patched search.py")
