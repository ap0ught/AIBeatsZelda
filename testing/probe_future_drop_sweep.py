"""Does future-drop shaping help?  Measured across every fight state in states/, not one room.

    python3 testing/probe_future_drop_sweep.py            # all three arms, every fight state
    python3 testing/probe_future_drop_sweep.py --quick    # one state, to check the harness

One room said the term made a fight 49% longer, and one room is one sample. This runs the
same A/B over every savestate in `states/` that has live enemies, in three arms:

    stub      `expected_drop` patched to predict nothing - the planner as it was before
              Change 1. Patching the function the planner calls, rather than adding a flag to
              the planner, keeps this arm free of the code under test.
    all       the term on, for every kill.
    last      the term on only when the branch kills the LAST enemy (`n1 == 0`).

The `last` arm exists because the one-room result had a likely explanation: the term shapes
toward where the dead monster was, which is a corpse, and a fight that loiters near a corpse
is not a fight that ends. A mid-fight body is worth nothing; only the last kill's position
persists into the decision about where the room ends. If that is the explanation, `last`
should beat `stub` where `all` loses to it.

## What the numbers mean, and what they do not

`frames` is how long `plan_fight` took to clear the room. Lower is better, and `vs stub` is
the only column that says anything: `all` winning on some rooms and losing on others is a
variance problem, while `last` losing everywhere is a sign problem, and those need different
responses.

This measures **rooms in isolation**, from a savestate, with the fight's outcome decided by
the planner alone. It is not a run. A real run compounds every room, so a term that is
neutral per-room can still be net-negative over a route by pushing Link into worse positions
on the way out - and none of that shows up here. A sweep that comes out positive is
permission to try a run, not evidence that the run improves.

Every fight here starts from a state captured mid-route, so Link's health, bombs and sword
are whatever they happened to be. That is another reason to read the total rather than any
one row.

## Cost

Three `plan_fight` runs per state over eight states, each up to 3000 frames of planning.
That is tens of minutes, not seconds. Run it detached:

    nohup python3 -u testing/probe_future_drop_sweep.py > /tmp/sweep.txt 2>&1 &
"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # states/, logs/ are repo-relative
del _os, _sys, _pathlib

import json
import random
import sys
import time
from pathlib import Path

import zelda.lookahead as L
from zelda import BizHawk
from zelda.emulator import ROM
from zelda.overworld import read_enemies
from zelda.search import Recorder

SEED = 12345
ARMS = ("stub", "all", "last")


def run_arm(emu, state: str, arm: str):
    """Clear the room from `state` under one arm. Returns (frames, decisions, drop)."""
    emu.load(state)
    if not read_enemies(emu):
        return None
    L.FUTURE_DROP[0] = arm in ("all", "last")
    L.FUTURE_DROP_LASTKILL_ONLY[0] = arm == "last"
    real = L.expected_drop
    if arm == "stub":
        L.expected_drop = lambda *a, **k: (None, 0.0, "disabled for the A/B")
    log: "list[dict]" = []
    L.DECISION_LOG[0] = log
    try:
        rec = Recorder(emu)
        L.plan_fight(emu, rec, rng=random.Random(SEED))
        frames, choices = len(rec.inputs), [d["choice"] for d in log]
    finally:
        L.DECISION_LOG[0] = None
        L.expected_drop = real
        L.FUTURE_DROP[0] = False
        L.FUTURE_DROP_LASTKILL_ONLY[0] = False
    return frames, choices, where_the_drop_lands(emu)


def where_the_drop_lands(emu):
    """Any $60 drop object on the floor, as (x, y, item). None if the floor is clear."""
    types = emu.ram(0x34F, 12)
    for s in range(1, 12):
        if types[s] == 0x60:
            # x is $70+s, y is $84+s, each its own 12-byte array.
            return emu.ram(0x70, 12)[s], emu.ram(0x84, 12)[s], emu.ram(0xAC, 12)[s]
    return None


def main() -> int:
    quick = "--quick" in sys.argv
    states = sorted(p.stem for p in Path("states").glob("*.State"))
    rows: list[dict] = []
    t0 = time.time()

    with BizHawk(rom=ROM, log_name="futuredrop_sweep.log") as emu:
        # which of these are actually fights? Loading each is cheap; a room with no enemies
        # has nothing to shape toward and would report "no effect" for every arm.
        fights: list[tuple[str, str, int]] = []          # stem, "L{level}R{room}", enemies
        for st in states:
            try:
                emu.load(st)
            except RuntimeError:
                continue
            ens = read_enemies(emu)
            if ens:
                s = emu.state()
                fights.append((st, f"L{s.level}R{s.room}", len(ens)))
        if not fights:
            print("no savestate in states/ has live enemies")
            return 1
        print(f"{len(states)} savestates, {len(fights)} of them are fights:", flush=True)
        for st, room, n in fights:
            print(f"  {st:24} {room:>8}  {n:2} enemies", flush=True)
        if quick:
            fights = fights[:1]

        for st, room, n in fights:
            got = {}
            for arm in ARMS:
                got[arm] = run_arm(emu, st, arm)
            if got["stub"] is None:
                continue
            base = got["stub"][0]
            differing = sum(1 for a, b in zip(got["stub"][1], got["all"][1]) if a != b)
            rows.append(dict(state=st, room=room, enemies=n,
                             stub=base, all_=got["all"][0], last=got["last"][0],
                             differing=differing,
                             stub_drop=got["stub"][2], all_drop=got["all"][2],
                             last_drop=got["last"][2]))
            print(f"\n{st} ({room}, {n} enemies)  [{time.time() - t0:.0f}s]", flush=True)
            for arm in ARMS:
                v = got[arm][0]
                print(f"  {arm:5} {v:>5} frames  ({v - base:+d} vs stub)  "
                      f"drop: {got[arm][2] if got[arm][2] else 'none'}", flush=True)
            print(f"  decisions differing, stub vs all: {differing}", flush=True)

    return report(rows, time.time() - t0)


def report(rows, elapsed) -> int:
    print(f"\n{'=' * 74}\nsweep over {len(rows)} fights, {elapsed:.0f}s\n")
    print(f"  {'room':>8} {'enemies':>8} {'stub':>7} {'all':>7} {'all vs':>8} "
          f"{'last':>7} {'last vs':>8} {'shifted':>8}")
    tot = {"stub": 0, "all": 0, "last": 0}
    for r in rows:
        tot["stub"] += r["stub"]
        tot["all"] += r["all_"]
        tot["last"] += r["last"]
        print(f"  {r['room']:>8} {r['enemies']:>8} {r['stub']:>7} {r['all_']:>7} "
              f"{r['all_'] - r['stub']:>+8} {r['last']:>7} "
              f"{r['last'] - r['stub']:>+8} {r['differing']:>8}")
    print(f"  {'TOTAL':>8} {'':>8} {tot['stub']:>7} {tot['all']:>7} "
          f"{tot['all'] - tot['stub']:>+8} {tot['last']:>7} "
          f"{tot['last'] - tot['stub']:>+8}")

    wins_all = sum(1 for r in rows if r["all_"] < r["stub"])
    wins_last = sum(1 for r in rows if r["last"] < r["stub"])
    losses_all = sum(1 for r in rows if r["all_"] > r["stub"])
    losses_last = sum(1 for r in rows if r["last"] > r["stub"])
    print(f"\n  all:  {wins_all} faster, {losses_all} slower, "
          f"{len(rows) - wins_all - losses_all} unchanged")
    print(f"  last: {wins_last} faster, {losses_last} slower, "
          f"{len(rows) - wins_last - losses_last} unchanged")
    print("\n  Reading it: winning some rooms and losing others is variance, and the fix is")
    print("  more rooms. Losing everywhere is the sign, and no amount of rooms will fix it.")
    print("  A positive total is permission to try a full run - not evidence one improves,")
    print("  because this measures rooms in isolation and a route compounds every one of them.")

    out = Path("logs/future_drop_sweep.json")
    out.write_text(json.dumps(rows, indent=1, default=str))
    print(f"\nper-room log: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
