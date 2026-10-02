"""Does the not-sitting-still machinery do what it says: the ledger, the flag list, and the rewind?

`zelda/runner.py` keeps two pieces of per-run state beside the checkpoints and one mechanism for
getting unstuck, and all three are advisory - which is exactly why they are easy to get quietly
wrong:

  * `logs/stuck.json` - the failure ledger. A segment that fails gets `fails`, its retry draws a
    DIFFERENT band of attempt seeds (`seed_base = 1000 + 1000*fails`), and after `BACKPROP_AFTER`
    failures the runner rewinds one segment and re-searches the decision that led there. A ledger
    that does not round-trip, or a `_note_stuck` that clobbers instead of merging, either re-runs the
    identical search forever or forgets that a segment is in trouble.
  * `logs/flagged.json` - what ACCEPT_AFTER left on the table. Taking what the search has is only a
    decision if the thing not taken is written down; without this the cost of the cap is invisible.
  * `runner.NeedsBackprop` - deliberately NOT the plain `RuntimeError: segment X failed`, because
    `run_until.sh` stops the run on that exact message. An escaping NeedsBackprop would print as
    `NeedsBackprop: ...`, which must not match, or a rewindable failure would be treated as a crash
    and retried forever.

No emulator, no display: the paths are pointed at a temporary directory, `Run` is constructed without
`open()`, and only `main.inputs` is touched. Run:  python3 testing/test_runner_stuck.py
"""
import json
import os
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from zelda import runner as r
from zelda.search import Attempt

tmp = Path("/tmp/opencode/stucktest")
tmp.mkdir(exist_ok=True)
r.STUCK_PATH = tmp / "stuck.json"
r.FLAGS_PATH = tmp / "flagged.json"

# -- the ledger round-trips, and a corrupt file is treated as "nothing recorded"
run = r.Run("testrun")
run.main = types.SimpleNamespace(inputs=[("A",)] * 10)      # only .inputs is touched
run.log = lambda *a: None
assert run.stuck_entry("nope") == {}
run._note_stuck("59_fight", fails=1, tries=60)
assert run.stuck_entry("59_fight")["fails"] == 1
r.STUCK_PATH.write_text("{ this is not json")
assert run.stuck_entry("59_fight") == {}, "a corrupt ledger must not raise"
run._note_stuck("59_fight", fails=2, tries=60)
assert run.stuck_entry("59_fight")["fails"] == 2
run._note_stuck("59_fight", fails=2, tries=60, backprops=1)    # _note_stuck merges, does not clobber
assert run.stuck_entry("59_fight")["backprops"] == 1
run._clear_stuck("59_fight")
assert run.stuck_entry("59_fight") == {}, "a segment that finally passed must not stay on the list"

# -- the flag list records what was left on the table
best = Attempt(seed=1002, frames=503, hearts=3.0)
best.accepted = "took the 503-frame line after 11 attempts (8 without improvement)"
run._flag_for_improvement("59_fight", best, best.accepted)
flag = json.loads(r.FLAGS_PATH.read_text())["59_fight"]
assert flag["frames"] == 503 and flag["hearts"] == 3.0 and flag["run"] == "testrun", flag
assert "8 without improvement" in flag["reason"], flag
assert flag["total_frames"] == 10

# -- backprop rewinds one segment, and leaves that segment unfinished
run.done = ["a", "b", "c"]
seen = []


def fake_resume(name):
    seen.append(name)
    run.done = list(run.done)          # resume() reloads done from the checkpoint
    return "state"


run.resume = fake_resume
run._note_stuck("d", fails=2, tries=60)
prev = run.backprop("d")
assert prev == "c" and seen == ["c"], (prev, seen)
assert run.done == ["a", "b"], run.done
assert r.Run.stuck_entry(run, "d")["backprops"] == 1

# -- and it declines, rather than inventing a rewind, at the start of a run
empty = r.Run("testrun2")
empty.log = lambda *a: None
assert empty.backprop("first") is None

# -- NeedsBackprop is not the message run_until.sh stops on
bp = r.NeedsBackprop("59_fight", 2, 0)
# run_until.sh stops the run on "RuntimeError: segment" in the log tail. A NeedsBackprop that
# escaped would print as "NeedsBackprop: ...", which must NOT match, or the wrapper would call a
# rewindable failure a crash and retry it forever. main() converts the un-rewindable case into the
# plain RuntimeError, and that is the message the wrapper does stop on.
escaped = f"{type(bp).__name__}: {bp}"
assert "RuntimeError: segment" not in escaped, escaped
assert escaped.startswith("NeedsBackprop: segment 59_fight failed 2 times"), escaped
plain = f"{type(RuntimeError('segment 59_fight failed')).__name__}: segment 59_fight failed"
assert "RuntimeError: segment" in plain, plain

print("ledger round-trips and survives a corrupt file; the flag list records the reason; "
      "backprop rewinds exactly one segment and un-finishes it; NeedsBackprop is not the message "
      "the wrapper stops on. all checks passed")