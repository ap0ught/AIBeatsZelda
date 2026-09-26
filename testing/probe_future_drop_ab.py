"""Does the future-drop term change the fight planner's mind, and in the right direction?

    python3 testing/probe_future_drop_ab.py [savestate]

Issue #6's Change 1 acceptance criterion is behavioural: "plan_fight ends a fight nearer the
exit when the last kill drops a key [bomb], and measurably earlier in a segment that farms
keys". A score that changed would not demonstrate that. This runs the same real fight twice
from the same savestate - once with the term live, once with it disabled - and reports what
each run's first decision was and how far the chosen ending sits from where the drop
actually landed.

The A/B is exact rather than statistical. `plan_fight` is deterministic given a savestate and
an RNG seed, and the two runs differ in exactly one thing: whether `expected_drop` returns a
drop. So any difference in the decision is caused by the term and nothing else - no need to
average over routes or argue about variance.

What this does NOT do, and the distinction is the whole point of the ticket:

- It runs from a savestate that exists in `states/`, not from the rooms the ticket names
  (L3R89, L5R38). Those need states captured in them first.
- It reports the first decision only. Whether the fight then *ends* nearer the exit is a
  claim about a whole fight, and one decision is evidence that the term is wired up and
  influential, not evidence that runs got faster.
- It cannot tell you the term is correctly *calibrated*. It shows the term moves decisions.
  Whether it moves them the right amount is a run-time question, and the honest way to
  answer that is a full run compared against the 37m02s baseline.

## Reading the output

    term ON / term OFF    the first move each run chose, and its score
    shifted                whether the two runs chose differently
    drop at                where the drop actually landed, from the OFF run's frame
    distance               how far each run's chosen ending is from it, in pixels

A `distance` that is smaller with the term on is the direction the ticket wants. Equal
distances with a non-empty `shifted` means the term changed the move but not the ending
position, which is worth knowing and is not the same result.
"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # states/, logs/ are repo-relative
del _os, _sys, _pathlib

import json
import random
import sys
from pathlib import Path

import zelda.lookahead as L
from zelda import BizHawk
from zelda.emulator import ROM
from zelda.search import Recorder

# emu.load() takes a BARE name and builds states/<name>.State itself, so passing a path
# gets you states/states/....State.State - which fails, correctly.
STATE = Path(sys.argv[1]).stem if len(sys.argv) > 1 else Path("m3_59_fight_start")
SEED = 12345


def first_decision(emu, *, term_on: bool):
    """Run the fight from the current state and return its first decision.

    `term_on=False` swaps `expected_drop` for a stub that never predicts anything, which is
    exactly what the planner did before Change 1. Patching the function the planner calls -
    rather than adding a flag to the planner - keeps the "before" arm free of the change
    under test, so there is no second code path that could itself be wrong.
    """
    real = L.expected_drop
    if not term_on:
        L.expected_drop = lambda *a, **k: (None, 0.0, "future-drop shaping disabled for the A/B")
    log: "list[dict]" = []
    L.DECISION_LOG[0] = log
    try:
        rec = Recorder(emu)
        L.plan_fight(emu, rec, rng=random.Random(SEED))
    finally:
        L.DECISION_LOG[0] = None
        L.expected_drop = real
    return log, rec


def where_the_drop_lands(emu):
    """Any $60 drop object in a slot, as (x, y, item). None if the floor is clear."""
    types = emu.ram(0x34F, 12)
    for s in range(1, 12):
        if types[s] == 0x60:
            # x is $70+s and y is $84+s, each its own 12-byte array. Reading y out of the x
            # buffer is an IndexError, which is what happened the first time.
            return emu.ram(0x70, 12)[s], emu.ram(0x84, 12)[s], emu.ram(0xAC, 12)[s]
    return None


def main() -> int:
    if not (Path("states") / f"{STATE}.State").exists():
        print(f"no savestate at states/{STATE}.State")
        return 1
    print(f"state     : states/{STATE}.State")
    print(f"cartridge : {ROM}")
    print(f"seed      : {SEED}\n")

    results = {}
    with BizHawk(rom=ROM, log_name="futuredrop_ab.log") as emu:
        for arm in (False, True):
            emu.load(STATE)
            log, rec = first_decision(emu, term_on=arm)
            label = "term ON " if arm else "term OFF"
            if not log:
                print(f"{label}: no decisions logged - not a fight")
                continue
            n_enemies = len(log[0].get("enemies") or [])
            print(f"{label}: {len(log)} decisions, {n_enemies} enemies in view, "
                  f"fight ran {len(rec.inputs)} frames")
            results[arm] = dict(log=log, frames=len(rec.inputs), enemies=n_enemies,
                                landed=where_the_drop_lands(emu))

        # The FIRST decision is the wrong thing to compare. It is very often a `hold` or an
        # approach step, which kills nothing, so n1 < n0 is false and the term is correctly
        # zero - the two arms then agree exactly and the comparison says nothing at all. That
        # is what the first version of this probe measured, and it reported "no effect" for a
        # term that is working. The whole sequence is the comparison; the interesting entries
        # are the ones where a branch actually killed something.
        if len(results) == 2:
            off, on = results[False]["log"], results[True]["log"]
            n = min(len(off), len(on))
            differing = [i for i in range(n) if off[i]["choice"] != on[i]["choice"]]
            print(f"\n{'=' * 68}")
            print(f"decisions compared: {n}   differing: {len(differing)}")
            if not differing:
                print("  the term changed nothing. Either no branch ever killed anything, or")
                print("  the room's monsters are types expected_drop declines to predict.")
            for i in differing[:5]:
                o, nn = off[i], on[i]
                ob = max(o["choice"] and [b["score"] for b in o["branches"]] or [0])
                nb = max([b["score"] for b in nn["branches"]] or [0])
                print(f"  decision {i}: OFF {o['choice']} ({ob:.1f})  ->  "
                      f"ON {nn['choice']} ({nb:.1f})   delta {nb - ob:+.1f}")
            print(f"\n  fight length: OFF {results[False]['frames']} frames, "
                  f"ON {results[True]['frames']} frames")
            if results[False]["landed"] or results[True]["landed"]:
                print(f"  drop on the floor afterwards: OFF {results[False]['landed']}, "
                      f"ON {results[True]['landed']}")

    Path("logs/future_drop_ab.json").write_text(json.dumps(
        {("term_on" if k else "term_off"):
            dict(frames=v["frames"], enemies=v["enemies"], landed=v["landed"],
                 choices=[d["choice"] for d in v["log"]][:400])
         for k, v in results.items()}, indent=1, default=str))
    print("\nWhat this does not show: that fights get faster, or that the term is correctly")
    print("calibrated. It shows the term is wired up and whether it moves the planner. The")
    print("ticket's named rooms (L3R89, L5R38) need savestates captured in them; this runs")
    print("from whatever state it is given.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
