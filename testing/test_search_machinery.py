"""Does the search's own machinery do what its comments say, with no emulator in the room?

`zelda/search.py` makes a lot of claims that only show up in a four-hour log if you wait for them:
ACCEPT_AFTER stops a solved segment a few attempts after its last improvement, `seed_base` really
rotates the sample, the phase labels the emulator windows draw are the ones the code thinks it is
drawing, and a scout whose emulator dies gets REPLACED rather than being dead for the rest of the
search (FINDINGS section 13). Each of those is a knob whose failure mode is silence - a segment that
polishes for forty attempts, a retry that replays the identical search, four windows that all say
BASELINE because the counter never moved - and none of them can be checked without an emulator except
by faking one.

So: fakes, no display, no socket. `FakeEmu` answers `load`, `state`, `step` and `cmd` from a fixed
`State`, and the policy raises `OverBudget` or succeeds depending on which invocation it is. Eight
checks, and each one prints the number it established:

  1. the cap fires and says why                     5. the cap counts since the last IMPROVEMENT
  2. cap=0 is exactly the old rule                  6. the phase vocabulary, including CAPPED/DONE
  3. the cap cannot fire with nothing to take       7. a dead scout is replaced and the search goes on
  4. seed_base moves the sample, reproducibly       8. with no callback, the old behaviour holds

WHAT IT DOES NOT CLAIM. Everything here is a fake, and the interesting difference is spelled out in
check 7: a fake attempt that returns instantly lets one worker take every attempt index before the
other thread is ever scheduled - the GIL, not a bug - so the fakes `time.sleep(0.001)` to hand it
over. A real attempt spends minutes inside BizHawk with the GIL released, and that is the case that
matters. So this proves the CONTROL FLOW, on a schedule arranged to make it visible; it proves
nothing about how long anything takes, and nothing about the search finding a line.

One assertion here was order-dependent and cost a false alarm once: `calls == [0, 1]`, when the two
worker threads race to their second load and either order is correct. It is `sorted(calls) == [0, 1]`
now. A test that fails one time in ten for no reason is worse than no test, because the answer people
learn is to run it again.

Run:  python3 testing/test_search_machinery.py
"""

import os
import types
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
from zelda import search
from zelda.emulator import BadReply, State
from zelda.search import parallel_search, OverBudget

# CONVERGE is the other early stop and it fires on identical results, which is exactly what these
# fakes produce. Off, so what is being measured here is the cap and nothing else.
search.CONVERGE[0] = False


class FakeEmu:
    def __init__(self, log, tag=None):
        self.cmds = []
        self.tag = tag
        self.log = log
        # hp packs full hearts in the low nibble and containers above it: 3 hearts of 3
        self.state_ = State(room=0x59, level=3, mode=5, hp=0x23, keys=1, bombs=0)

    def load(self, name):
        return self.state_

    def state(self):
        return self.state_

    def step(self, buttons=(), frames=1):
        return self.state_

    def cmd(self, line):
        self.cmds.append(line)
        return "ok"

    def close(self):
        pass

    def note(self, msg):
        self.log.append(msg)


def run(accept_after, succeed_on=(), tries=60, seed_base=1000, scouts=2, length=None, **kw):
    """Each scout succeeds on its own `succeed_on` invocation numbers. `length(invocation)` gives
    that success's frame count: the default is a plateau (every success the same length, so only the
    first can improve), test 5 passes a decreasing one so every success is an improvement."""
    log, emus, draws = [], [], {}
    born = []

    def factory(nav):
        state = {"n": 0}

        def policy(emu, rec, rng, max_frames):
            state["n"] += 1
            i = state["n"]
            draws.setdefault(id(nav), []).append(rng.randint(0, 10 ** 6))
            if i not in succeed_on:
                raise OverBudget()
            for _ in range(length(i) if length else 593):
                rec.step((), 1)
            return "clear"
        return policy

    for k in range(scouts):
        emus.append(FakeEmu(log, tag=k))
    navs = [object() for _ in range(scouts)]
    best = parallel_search(emus, navs, "start", factory, lambda emu, s: True, tries=tries,
                           max_frames=1500, log=log.append, label="test", patience=14,
                           seed_base=seed_base, accept_after=accept_after, **kw)
    # Count invocations, not log lines: a success that does not beat the best is not logged at all,
    # which is itself worth knowing about (a search can be quietly succeeding and improving nothing).
    attempts = sum(len(v) for v in draws.values())
    logged = sum(1 for line in log if line.strip().startswith("attempt "))
    return best, attempts, logged, draws, log, [c for e in emus for c in e.cmds]


# 1. With the cap, a solved segment stops a few attempts after its last improvement, and says why.
best, attempts, _, _, log, _cmds = run(accept_after=4, succeed_on={1, 2})
assert best is not None and best.frames == 593, (best and best.frames, attempts)   # the plateau
assert best.accepted and "4" in best.accepted, best.accepted
assert attempts <= 12, f"cap did not bound the polishing tail: {attempts} attempts"
assert any("accept-after 4" in l for l in log), [l for l in log if "accept" in l]
print(f"cap=4: stopped after {attempts} attempts; accepted={best.accepted!r}")

# 2. cap=0 restores the old rule: the same segment keeps polishing all the way to `tries`.
best0, attempts0, logged0, _, _, _c0 = run(accept_after=0, succeed_on={1, 2}, tries=30)
assert best0 is not None and best0.accepted == "", best0.accepted
assert attempts0 == 30, attempts0
assert logged0 < attempts0, (logged0, attempts0)   # a success that improved nothing is silent
print(f"cap=0: ran all {attempts0} attempts ({logged0} of them logged); accepted={best0.accepted!r}")

# 3. The cap never fires when there is nothing to take: no success anywhere means no best.
none_best, attempts_none, _, _, _, _c = run(accept_after=2, succeed_on=set(), tries=12)
assert none_best is None, none_best
print(f"cap=2, no success anywhere: {attempts_none} attempts, best={none_best}")

# 4. seed_base moves the sample; the default base reproduces itself exactly.
_, _, _, a1, _, _ = run(accept_after=3, succeed_on={1})
_, _, _, a2, _, _ = run(accept_after=3, succeed_on={1})
_, _, _, b1, _, _ = run(accept_after=3, succeed_on={1}, seed_base=2000)
keys = sorted(a1)
assert all(a1[k] == a2[k] for k in keys), "same seed_base must reproduce the same draws"
assert all(a1[k] != b1[k] for k in keys), "seed_base=2000 drew the same randomness as 1000"
print(f"seed rotation: base 1000 -> {a1[keys[0]]}, base 2000 -> {b1[keys[0]]}")

# 5. The cap counts attempts since the last IMPROVEMENT, so a still-improving segment is never cut.
best5, attempts5, _, _, _, _c5 = run(accept_after=3, succeed_on={1, 2, 3, 4, 5, 6, 7, 8}, tries=40,
                                 length=lambda i: 600 - 7 * i,   # every success is an improvement
                                 scouts=1)                        # one scout: a deterministic sequence
# All 8 improving successes ran - the cap never cut one short - and the best is the LAST one.
# The cap does fire at the end, once the improvements stop and 3 failures follow them, which is
# the intended behaviour rather than a bug: "3 without improvement" is the patience, nothing more.
assert best5 is not None and best5.frames == 544, (best5.frames, best5.accepted)
assert attempts5 == 11, attempts5        # 8 improving successes + 3 failures, nothing cut short
assert "3 without improvement" in (best5.accepted or ""), best5.accepted
print(f"cap=3 with every attempt improving: {attempts5} attempts, not cut short")

# 6. The phase vocabulary: numbered while searching, and the stop reason named at the moment it stops.
_, _, _, _, _, cmds = run(accept_after=3, succeed_on={1, 2, 3}, tries=8)
phases = [c.split(" ", 1)[1] for c in cmds if c.startswith("phase ")]
assert "BASELINE #1" in phases, phases[:6]
assert any(p.startswith("POLISH #") for p in phases), phases
# CAPPED is announced the moment the search decides (while windows are still stepping, so it can be
# seen) and DONE after the threads join (correct in the bridge, invisible on a parked window).
assert "CAPPED" in phases and phases.index("CAPPED") < len(phases) - 1, phases[-4:]
assert phases[-1] == "DONE", phases[-3:]
assert all(len(p) <= 14 for p in phases), phases        # the HUD draws 14 cells
_, _, _, _, _, cmds2 = run(accept_after=3, succeed_on=set(), tries=8)
# With no success anywhere there is nothing to polish, so every attempt says BASELINE with its own
# number - the numbering is what tells four windows apart when they are all in the same phase.
ph2 = [c.split(" ", 1)[1] for c in cmds2 if c.startswith("phase ")]
numbered = [p for p in ph2 if "#" in p]          # one per attempt; DONE is sent per scout after the join
assert numbered == [f"BASELINE #{i}" for i in range(1, len(numbered) + 1)], numbered
assert ph2[-1] == "DONE" and ph2[-2] == "DONE", ph2[-2:]   # once per scout, both at the end
_, _, _, _, _, cmds3 = run(accept_after=3, succeed_on={1, 2, 3}, tries=8, phase_prefix="S2/5 ")
staged = [c.split(" ", 1)[1] for c in cmds3 if c.startswith("phase ")]
assert staged[0] == "S2/5 BASELINE #1", staged[:4]
print("phases:", phases[:3], "...", phases[-1], "| staged:", staged[0])

# 7. A scout whose emulator dies is REPLACED and keeps working, instead of being dead for the rest
#    of the search. FakeBizHawk raises RuntimeError("bridge connection lost") on its 2nd attempt.
class Dying(FakeEmu):
    def __init__(self, log, tag=None, die_on=2):
        super().__init__(log, tag)
        self.attempts = 0
        self.die_on = die_on

    def load(self, name):
        self.attempts += 1
        if self.attempts == self.die_on:
            raise RuntimeError("bridge connection lost at 12:00:00: EmuHawk exit code 0")
        return self.state_


log = []
scouts_ = [Dying(log, tag=k) for k in range(2)]
calls = []


def respawn(k):
    calls.append(k)
    fresh = FakeEmu(log, tag=f"fresh{k}")
    scouts_[k] = fresh
    return True


def factory(nav):
    seen = {"n": 0}

    def policy(emu, rec, rng, max_frames):
        # sleep(0) hands the GIL over. Without it a fake attempt finishes instantly, one worker takes
        # every attempt index before the other thread is ever scheduled, and the test measures the
        # scheduler instead of the respawn. A real attempt spends minutes inside the emulator with the
        # GIL released, which is the case that matters.
        time.sleep(0.001)
        seen["n"] += 1
        if seen["n"] > 6:                    # everything after the deaths succeeds
            for _ in range(520 + seen["n"]):
                rec.step((), 1)
            return "clear"
        raise search.OverBudget()
    return policy


# tries must cover "6 failures then success" for BOTH scouts, and a respawn rebuilds the policy with
# its own counter, so both need 7 of their own attempts: 14 is the floor and 30 leaves room to spare.
best = search.parallel_search(scouts_, [object(), object()], "start", factory, lambda e, s: True,
                              tries=30, max_frames=1500, log=log.append, label="respawn",
                              patience=6, respawn=respawn)
# sorted(), because the two workers race to their second load and either order is right:
# assert calls == [0, 1] failed once in six runs and was the test's fault, not the code's.
assert sorted(calls) == [0, 1], calls
assert any("replaced with a fresh emulator" in l for l in log), [l for l in log if "replac" in l]
assert best is not None and best.success, best        # and the search still produced a winner
assert any("scout emulator(s) died mid-search, 2 replaced" in l for l in log), [l for l in log if "died" in l]
print(f"respawn: {calls}, best {best.frames} frames from a search that lost both emulators first")

# 8. Without a respawn callback the old behaviour holds: the worker stops.
log2 = []
scouts2 = [Dying(log2, tag=k) for k in range(2)]
best2 = search.parallel_search(scouts2, [object(), object()], "start", factory, lambda e, s: True,
                               tries=30, max_frames=1500, log=log2.append, label="norespawn", patience=6)
assert best2 is None, best2
assert sum(1 for l in log2 if "is not coming back this search" in l) == 2, log2
print("no callback: both workers stopped, as before")

# 9. A DEAD CHANNEL and an UNREADABLE REPLY are different things and must be handled differently.
#    Check 7 covers the first from the other side (the emulator raising RuntimeError mid-attempt);
#    this covers both at the post-attempt state read, which is where the distinction was got wrong.
#    A scout whose socket has timed out must be REPLACED, because Python will never read that socket
#    again; a scout whose reply merely cannot be parsed must be KEPT. Getting that backwards kept a
#    finished scout in the search and let it answer every remaining attempt instantly.
class Dead(FakeEmu):
    """Raises where a timed-out socket raises: from state(), after the policy has run."""

    def __init__(self, log, tag=None, exc=None):
        super().__init__(log, tag)
        self.exc = exc

    def state(self):
        raise self.exc


def one(exc):
    log = []
    emus = [Dead(log, tag=0, exc=exc)]
    calls = []

    def respawn(k):
        calls.append(k)
        emus[k] = FakeEmu(log, tag=f"fresh{k}")
        return True

    search.parallel_search(emus, [object()], "start", factory, lambda e, s: True, tries=4,
                           max_frames=1500, log=log.append, label="distinguish", patience=3,
                           respawn=respawn)
    return calls, log


calls, log = one(OSError("cannot read from timed out object"))
assert calls == [0], f"a timed-out socket is a dead channel and must be replaced: {calls}"
assert any("lost its emulator" in l for l in log), [l for l in log if "lost" in l]
print(f"dead channel: replaced {calls}, which is the only thing that can help")

calls, log = one(BadReply("the bridge's answer to 'state' is not an answer to it: 'frame=1 mode='"))
assert calls == [], f"an unreadable reply is one attempt of bad luck, not a dead scout: {calls}"
assert any("unreadable bridge reply" in l for l in log), [l for l in log if "unreadable" in l]
assert any("attempt(s) lost to a bridge reply that could not be read" in l for l in log), log
print("unreadable reply: scout kept, attempt lost, and the search's summary says so")

# 10. A BadReply names the replies that came before it, and a good reply is appended to the record.
#     Checked against the REAL BizHawk.cmd - only the socket underneath is fake - because the thing
#     being tested is what that function puts in the message, and a test of a copy of it proves
#     nothing. A garbled reply on its own says the stream slipped; the replies before it say where,
#     and "'ok' as the answer to `step`" is only interpretable if the log carries what preceded it.
import io as _io
from collections import deque as _deque

from zelda.emulator import BizHawk


def wire(lines):
    """A BizHawk with no emulator: a socket that swallows writes and a reader that hands back
    `lines` one at a time, exactly as a bridge would."""
    emu = object.__new__(BizHawk)
    emu.conn = types.SimpleNamespace(sendall=lambda b: None, settimeout=lambda t: None)
    emu._rf = _io.BytesIO("".join(l + "\n" for l in lines).encode())
    emu._recent = _deque(maxlen=8)
    return emu


emu = wire(["frame=1 mode=05 sub=00", "frame=1 mode=05 sub=00", "0a0b0c", "ok"])
assert BizHawk.cmd(emu, "state") == "frame=1 mode=05 sub=00"
assert BizHawk.cmd(emu, "state") == "frame=1 mode=05 sub=00"
assert BizHawk.cmd(emu, "ram 485 3") == "0a0b0c"
try:
    BizHawk.cmd(emu, "ram 847 12")
except BadReply as e:
    msg = str(e)
    assert "ram 847 12" in msg and "'ok'" in msg, msg
    # the three replies before it, in order: the point of the ring buffer
    assert msg.count("->") == 3, msg
    assert "'state'->'frame=1 mode=05 sub=00" in msg, msg
    assert "'ram 485 3'->'0a0b0c'" in msg, msg
    print("BadReply names the command, the reply it got, and the three replies before it")
else:
    raise AssertionError("a reply that cannot be right did not raise")

# and the ring is cleared by the raise, so the NEXT failure does not quote a stale history
emu2 = wire(["ok"])
try:
    BizHawk.cmd(emu2, "state")
except BadReply as e:
    assert "before:" not in str(e), str(e)
else:
    raise AssertionError("a reply that cannot be right did not raise")

print("all checks passed")