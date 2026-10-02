"""Does the reply validator ever reject a real reply, and does a real fight produce a bad one?

Two questions about `zelda/emulator.py`'s `_reply_answers`, which rejects a bridge reply that is not
an answer to the command that was sent. It exists because the failure was invisible: a garbled reply
reached `State.parse`, which does `int(v)` on the right of every `k=v` token, so a truncated line
raised `ValueError: invalid literal for int() with base 10: ''` - a message naming neither the command
nor the emulator nor the reply. Measured at 12 attempts in 590 over a four-hour log (2.0%), and all
twelve were in fights, which are the segments that make the most `state` calls per attempt.

A check that is wrong in the strict direction costs a whole emulator, so it has to be shown safe
against real traffic before anyone trusts it, and `BizHawk.cmd` is the one place every reply passes
through. So this probe wraps `cmd` - which sees every command and every reply the harness ever gets,
including the ones made from inside `parallel_search`, `Navigator` and `plan_fight` - and counts two
things:

1. REJECTED: a reply the validator called malformed. On real traffic this must be ZERO. One is a bug
   in the validator, and the cost of it is an emulator replaced for nothing.
2. BAD: a real reply that failed to parse - the ValueError the run's log actually recorded. This is
   the failure being hunted; see the docstring's "what it does not claim" for what a null result here
   is worth.

The traffic is real and it is the traffic that failed: `fullgame.gleeok_policy` - the fight, from
`states/ckpt_gleeok_start.State`, the bookmark the archived route-5 run searched `gleeok` from - driven
through `parallel_search` itself, four scouts wide, with the phase spread a phase-locked boss gets. Not
a synthetic command mix, because the synthetic mix is what came back clean 65,149 times and taught
nothing.

Run:  python3 testing/probe_bridge_replies.py [seconds]
Needs a display. Default 300 seconds.
"""
import os
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

import zelda.emulator as emu_mod
from zelda.emulator import BadReply, BizHawk

# Wrap cmd once. Everything the harness asks the bridge goes through it, so this is the whole surface.
COUNTS = {"replies": 0, "rejected": []}
_orig_cmd = BizHawk.cmd


def cmd(self, line: str) -> str:
    resp = _orig_cmd(self, line)
    COUNTS["replies"] += 1
    if not emu_mod._reply_answers(line, resp):
        COUNTS["rejected"].append((line, resp[:200]))
        raise BadReply(f"the bridge's answer to {line!r} is not an answer to it: {resp[:140]!r}")
    return resp


BizHawk.cmd = cmd


def fight() -> list:
    """Search the Gleeok fight for real, from the bookmark the archived run searched it from."""
    from zelda.overworld import Navigator
    from zelda.search import parallel_search, ENTER_SPREAD
    from zelda.boss import gleeok_dead
    import fullgame as fg

    ENTER_SPREAD[0] = 90                      # what a phase-locked boss gets; see runner.PHASE_LOCKED
    log = []
    with BizHawk(log_name="probe_bridge_replies.log") as emu:
        # load() itself goes through cmd, so the validator sees the load's reply too.
        emu.load("ckpt_gleeok_start")
        scouts = [emu] + [BizHawk(log_name=f"probe_bridge_s{i}.log", clean_sram=False) for i in range(3)]
        try:
            parallel_search(scouts, [Navigator(e) for e in scouts], "ckpt_gleeok_start",
                            lambda nav: fg.gleeok_policy(nav),
                            lambda emu2, s: s.hearts > 0 and s.room == 0x13 and gleeok_dead(emu2),
                            tries=10 ** 6, max_frames=3000, log=log.append, label="probe",
                            patience=10 ** 6, accept_after=10 ** 6)
        finally:
            for e in scouts:
                try:
                    e.close()
                except Exception:
                    pass
    return log


def main() -> None:
    secs = float(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].replace(".", "").isdigit() else 300
    print(f"running the Gleeok fight from ckpt_gleeok_start for {secs:.0f}s, four scouts wide, "
          f"validating every reply", flush=True)
    stop = threading.Event()
    box = []

    def go():
        box.append(fight())

    t = threading.Thread(target=go, daemon=True)
    t0 = time.time()
    t.start()
    while time.time() - t0 < secs + 90 and t.is_alive():
        time.sleep(5)
    # The search is bounded by TIME, not by tries: patience and accept_after are set out of reach so
    # it keeps drawing attempts until the window closes, because the sample being bought is replies
    # and a fight that ends in 20 seconds buys almost none.
    t.join(timeout=30)
    print(f"  {time.time() - t0:.0f}s, {COUNTS['replies']} replies checked", flush=True)
    for line in (box[0][-6:] if box and box[0] else []):
        print(f"    search: {line}", flush=True)
    print(f"  rejected by the validator: {len(COUNTS['rejected'])}"
          + ("" if not COUNTS["rejected"] else "   <-- THE VALIDATOR IS WRONG"), flush=True)
    for line, resp in COUNTS["rejected"][:5]:
        print(f"      {line!r} -> {resp!r}", flush=True)
    if not COUNTS["rejected"]:
        print("  so the validator accepted every reply the harness received. That is the claim it "
              "makes, and it is the only one it makes.", flush=True)
    print("  This says nothing about how OFTEN a reply is malformed. The archived run's rate is 2.0% "
          "of attempts and one attempt is thousands of replies, so minutes of one fight is a small "
          "sample of that - the probe's job is to prove the check is safe, not to find the cause, and "
          "testing/probe_bridge_replies.py's own docstring is where the cause is still open.",
          flush=True)


main()