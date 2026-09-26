"""Does the drop table predict what actually lands?  The behavioural half of issue #6.

    python3 testing/probe_drop_behaviour.py [inputs] [rom]

`probe_drop_table.py` decodes `SetUpDroppedItem` out of the cartridge and checks the
transcription is self-consistent.  Its closing line says this proves only what the code
says, not what the game does, and that the remaining check is behavioural.  This is that
check: replay the verified run6, watch every monster die, and compare the item that lands
against the table's prediction for that kill.

Reading a table tells you what the code says.  Only a kill tells you what happens.

## What a drop actually is, established by measurement rather than assumed

Three things had to be measured before this probe meant anything, and two of them
contradicted what the harness and I assumed.

**`$60` is right.**  `UpdateObject_JumpTable` in Z_07.asm has one entry per type, and
entry `$60` is `UpdateItem`, so a dropped item is object type `$60` - exactly what
`zelda/lookahead.py` assumes.  I spent a probe wrongly doubting this: a 2,700-frame
window with 9 kills showed no `$60` at all, which looked like the detection was dead code.
It was not.  Over 29,300 frames there were 173 kills and 18 `$60` objects.  The lesson is
about sample size, not about the harness.

**A dead monster's own slot goes to `$00`, not `$60`.**  The drop is a *new* object, not
the corpse, so it can land in any free slot.  Pairing a drop with the kill that produced
it therefore cannot use the slot number - two monsters dying on the same frame put their
drops in adjacent slots, and the same slot is reused within a few frames.  This probe
pairs on time: the nearest kill within `PAIR_WINDOW` frames.

**`Random` is per-slot, and reading it after the fact is not the same byte.**  The cancel
is `LDA Random, X / CMP DropItemRates, Y / BCS @DestroyMonster`, with X the object slot -
so `Random[slot]`, not one global byte.  But `Random` is re-randomised, and the bridge read
happens *after* the frame the routine ran in, so the byte read here is not reliably the
byte the compare used.  Rather than pretend otherwise, this probe does not predict
individual cancels.  It compares the **observed drop frequency per row** against the
frequency the table implies (`rate/256`), which needs no knowledge of any individual
`Random` value and is immune to the staleness.

## Reading the output

    agree / MISMATCH   per-drop: the item that landed vs the table's answer for that
                       kill.  This is the table check, and it is exact - no timing
                       slack, because the item id is read from the drop object itself.

    rate per row        observed drops / kills for that row, against the rate the table
                       implies.  A large shortfall means the cancel is firing more often
                       than `DropItemRates` predicts, which is a different bug from a
                       wrong table and must not be reported as one.

A MISMATCH is a table or pairing problem.  A rate shortfall is a cancel problem.  Keeping
them apart is the point: the first invalidates the table, the second invalidates the
model of when the drop is thrown away, and they have different fixes.

## Cost

One `step` and two `ram` reads per frame, because a drop is only visible on the frames it
exists.  Around 300 frames a second, so the full 136k-frame run6 is roughly eight minutes.
Progress goes to stdout unbuffered, so run it detached and tail the file:

    nohup python3 -u testing/probe_drop_behaviour.py > /tmp/drops.txt 2>&1 &
"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # runs/, logs/ are repo-relative
del _os, _sys, _pathlib

import collections
import hashlib
import json
import sys
import time
from pathlib import Path

from zelda import BizHawk, replay
from zelda.emulator import ROM

# The rules themselves live in zelda/drops.py, not here. That is the point of this import:
# the 43/43 below has to be a statement about the code the fight planner actually runs. A
# probe that validates one transcription while the planner uses another measures nothing,
# and the way that fails is quietly - both look right and they disagree at the edges.
from zelda.drops import (  # noqa: E402
    DROP_TABLE, LISTED, MEASURED_RATE, NO_DROP, RATES, SLOT1_NO_DROP,
    expected_drop, implied_rate, row_of,
)

OBJ_TYPE = 0x34F     # ObjType; $60 is UpdateItem, i.e. a dropped item
ITEM_ID = 0xAC       # Item_ObjItemId
RND = 0x18           # Random, an array indexed by object slot
HELP_COUNT, HELP_VALUE = 0x50, 0x51
WORLD_CYCLE, WORLD_COUNT = 0x52A, 0x627
NSLOT = 12           # slots 1..11; slot 0 is Link
DROP_TYPE = 0x60
PAIR_WINDOW = 40     # frames; a drop is attributed to the nearest kill before it
HIST = 64            # frames of counter history kept, for the rule search below


def read_counters(emu):
    """The three counters, in one go.  $50 and $51 are adjacent; $52A and $627 are not."""
    pair = emu.ram(HELP_COUNT, 2)
    return pair[0], pair[1], emu.byte(WORLD_CYCLE), emu.byte(WORLD_COUNT)


def row_of(mtype: int) -> int:
    if mtype in NO_DROP:
        return -1
    if mtype in ROW0:
        return 0
    if mtype in ROW1:
        return 1
    if mtype in ROW2:
        return 2
    return 3


def predict(kind, slot, mtype, cycle, help_count, help_value, kill_count):
    """Delegates to zelda.drops.expected_drop, so there is one decision, not two.

    `kind` is accepted and ignored: it was this probe's own classification of which of the
    two counter tests fired, and keeping it as a parameter would invite a future caller to
    believe the probe decides that independently. It does not.
    """
    return expected_drop(mtype, slot, cycle, help_count, help_value, kill_count)


def kind_of(help_count, kill_count):  # noqa: D401  (reporting only)
    """The two counter tests, in assembly order.  `CPY #$10` is an exact compare and
    $627 is a plain INC, so the fairy fires once per run and never at $0F or $11."""
    if kill_count == 0x10:
        return "fairy"
    if help_count >= 0x0A:
        return "guarantee"
    return "table"


def main() -> int:
    inputs = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("runs/run6/inputs.txt")
    rom = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(ROM)
    frames = replay.load_inputs(inputs)

    print(f"cartridge : {rom}")
    print(f"md5       : {hashlib.md5(rom.read_bytes()).hexdigest()}")
    print(f"input log : {inputs}  ({len(frames)} frames)")
    print(f"watching  : ${OBJ_TYPE:03X} for ${DROP_TYPE:02X} (UpdateItem) drops, "
          f"pairing to the nearest kill within {PAIR_WINDOW} frames\n", flush=True)

    t0 = time.time()
    kills: list[dict] = []
    drops: list[dict] = []
    hist: list[tuple] = []      # (frame, $50, $51, $52A, $627)
    nframes = 0

    with BizHawk(rom=rom, log_name="dropbehaviour.log") as emu:
        print("  connected", flush=True)
        prev = emu.ram(OBJ_TYPE, NSLOT)
        for i, btn in enumerate(frames):
            emu.step(btn, 1)
            nframes = i + 1
            cur = emu.ram(OBJ_TYPE, NSLOT)
            c50, c51, c52a, c627 = read_counters(emu)
            hist.append((i, c50, c51, c52a, c627))
            if len(hist) > HIST:
                del hist[0]

            for s in range(1, NSLOT):
                was, now = prev[s], cur[s]
                if 0 < was < 0x50 and not (0 < now < 0x50):
                    kills.append(dict(frame=i, slot=s, monster=was, row=row_of(was),
                                      cycle=c52a, kind=kind_of(c50, c627),
                                      help_count=c50, help_value=c51, kill_count=c627))
                if now == DROP_TYPE and was != DROP_TYPE:
                    # the counter history, so the rule search can ask what each variable
                    # said at any frame near the drop rather than only at the kill
                    drops.append(dict(frame=i, slot=s, observed=emu.ram(ITEM_ID, NSLOT)[s],
                                      hist=[h for h in hist if h[0] >= i - HIST]))

            prev = cur
            if nframes % 5000 == 0:
                el = time.time() - t0
                rate = nframes / el
                print(f"  f{nframes:>7}  {rate:6.1f} f/s  {len(kills)} kills  "
                      f"{len(drops)} drops  "
                      f"eta {(len(frames) - nframes) / rate / 60:5.1f} min", flush=True)

    return report(kills, drops, nframes, time.time() - t0, inputs)


def _pre_kill_counters(d, k):
    """The newest counter sample from BEFORE the drop, as (frame, $50, $51, $52A, $627).

    Sampling backwards is not a fudge. `@SetHelpItem` does `STA HelpDropCount` with A = #$00
    as it fires, and the routine runs a frame or two before the object's type clears, so by
    the time this probe observes the kill the counter that proves a help drop happened has
    been zeroed by the help drop. Reading the frame before fixes all six of those.

    It also settles where a planner has to read. The planner shapes a fight toward a kill
    that has NOT happened yet, so it is on the right side of this automatically - which is
    an argument for doing the shaping prospectively rather than after the fact.
    """
    for fr, c50, c51, c52a, c627 in sorted(d.get("hist") or [], reverse=True):
        if fr < d["frame"]:
            return (fr, c50, c51, c52a, c627)
    return (k["frame"], k["help_count"], k["help_value"], k["cycle"], k["kill_count"])


def report(kills, drops, nframes, elapsed, inputs) -> int:
    print(f"\n{nframes} frames in {elapsed:.0f}s")
    print(f"  {len(kills)} kills, {len(drops)} drop objects "
          f"({len(drops) / max(1, len(kills)) * 100:.1f}% of kills)\n")

    # Pair each drop with a kill only when exactly one candidate is in the window. With 697
    # kills and 90 drops, and several monsters often dying within a few frames, a
    # "nearest kill" rule silently attributes a drop to whichever kill was closest - not a
    # weak measurement but a wrong one, and it inflated mismatches from 18 to 29 when tried.
    used: set[int] = set()
    paired: list[dict] = []
    ambiguous = unpaired = outside_pool = 0
    for d in drops:
        window = [i for i, k in enumerate(kills)
                  if i not in used and 0 <= d["frame"] - k["frame"] <= PAIR_WINDOW]
        if not window:
            unpaired += 1
            continue
        if len(window) > 1:
            ambiguous += 1
            continue
        used.add(window[0])
        k = kills[window[0]]
        if k["monster"] not in LISTED:
            # Bosses and scenery - types the game does not list, for which SetUpDroppedItem
            # may not run at all. expected_drop declines to guess about these, so counting
            # them would report the model's honesty as its error.
            outside_pool += 1
            continue
        h = _pre_kill_counters(d, k)
        pred, prob, why = predict(k["kind"], k["slot"], k["monster"], k["cycle"],
                                  h[1], h[2], h[4])
        paired.append(dict(drop=d, kill=k, predicted=pred, prob=prob, why=why,
                           sampled=h[0]))

    # Write the per-event log BEFORE the reporting below. The first full run lost 26 of 29
    # mismatches and the whole event log to a formatting error further down this function,
    # because the write was last. The measurement is the expensive part; the prose is not.
    out = Path("logs/drop_behaviour.json")
    out.write_text(json.dumps(dict(kills=kills, drops=drops, frames=nframes,
                                   inputs=str(inputs)), indent=1))

    tally = collections.Counter()
    mism = []
    for pr in paired:
        if pr["predicted"] == pr["drop"]["observed"]:
            tally["agree"] += 1
        else:
            tally["MISMATCH"] += 1
            mism.append(pr)
    tally["nothing predicted"] = sum(1 for pr in paired if pr["predicted"] is None)

    print("per-drop, model prediction vs what landed:")
    for k, v in sorted(tally.items()):
        print(f"  {k:<22} {v}")
    for label, n in (("(ambiguous: >1 kill)", ambiguous), ("(no kill in window)", unpaired),
                     ("(unlisted type)", outside_pool)):
        if n:
            print(f"  {label:<22} {n}   not counted either way")

    # The rate check: the random cancel, and a different question from the table.
    print("\ndrop frequency per row, against what DropItemRates implies:")
    print(f"  {'row':>4} {'kills':>7} {'drops':>6} {'observed':>9} {'implied':>8} "
          f"{'MEASURED_RATE':>13}")
    rows: dict[int, list[int]] = collections.defaultdict(lambda: [0, 0])
    for k in kills:
        if k["kind"] == "table" and k["row"] >= 0:
            rows[k["row"]][0] += 1
    for pr in paired:
        if pr["kill"]["kind"] == "table" and pr["kill"]["row"] >= 0 \
                and pr["predicted"] is not None:
            rows[pr["kill"]["row"]][1] += 1
    for r in sorted(rows):
        n, d = rows[r]
        if not n:
            continue
        meas = f"{MEASURED_RATE[r]:.1%}" if r in MEASURED_RATE else "not measured"
        print(f"  {r:>4} {n:>7} {d:>6} {d / n * 100:>8.1f}% {implied_rate(r) * 100:>7.1f}% "
              f"{meas:>13}")
    print("  MEASURED_RATE is what zelda.drops uses to scale future-drop shaping. Rows 0-2 "
          "cover every\n  listed monster type, so a planner never needs a row 3 rate.")

    if mism:
        print(f"\n{len(mism)} MISMATCH(es) among unambiguous, listed pairings:")
        for pr in mism:
            k, d = pr["kill"], pr["drop"]
            want = "nothing" if pr["predicted"] is None else f"${pr['predicted']:02X}"
            print(f"  f{d['frame']:>7} killed ${k['monster']:02X} (row {k['row']}, col "
                  f"{k['cycle']}) -> predicted {want}, landed ${d['observed']:02X}")
            print(f"          {pr['why']}   counters sampled at f{pr['sampled']}")
    else:
        print("\nno MISMATCH: every drop that landed is the item the model names.")

    rule_search(paired)
    print(f"\nper-event log: {out}")
    return 1 if mism else 0


# Which counter is the guarantee watching, and when?  The first full run produced drops the
# table cannot explain - seven of them landed $0F (five rupees), which only the guarantee
# path produces - while the byte at $50, which `Variables.inc` names HelpDropCount, was
# $00-$04 at every one. Three explanations fit that shape, and the point of this function
# is that all three were tested and **two of them are dead**:
#
#   swapped   $50 and $627 are exchanged relative to the symbol names.  REFUTED: 50/59 for
#             the disassembly's own assignment against 42/59 for the swap.
#   timing    the routine runs some frames after the type clears, so the sampled counter is
#             stale.  REFUTED: every offset from -3 to +3 scored identically, because the
#             counters do not move inside that window.
#   column    $52A was sampled one column off.  REFUTED decisively: col+0 scores 37/43
#             against 6/43 and 5/43 for col-1 and col+1.  The "adjacent column" pattern the
#             first report saw was an artifact of scoring only the drops that disagreed.
#
# What survives is 6 drops that all landed $0F, which is the guarantee with
# HelpDropValue == 0 - and $50 reads 0 at every one of them. That is self-erasing evidence:
# `@SetHelpItem` does `STA HelpDropCount` with A = #$00, so the counter that proves the
# guarantee fired is zeroed by the act of firing it. A post-frame read cannot see it. Catching
# it needs the counter sampled BEFORE the routine runs, which means a pre-frame hook rather
# than a bridge read - so this is a known, named limitation and not a mystery.
#
# The method that matters here is the negative evidence. Each candidate must predict the
# plain-table drops too - a rule keyed on the wrong variable fires the guarantee on a drop
# where nothing landed, and is caught by a false positive it cannot avoid. The first version
# of this search scored only the drops it was meant to explain and returned $50 and $627
# tied, because almost any variable above $0A "explains" a drop that landed $0F. A test that
# cannot separate two hypotheses is not evidence, however confident it looks.
def rule_search(paired) -> None:

    print(f"\n{'=' * 72}\nrule search\n{'-' * 72}")

    # Score a candidate as a COMPLETE predictor over every table-path drop, not just the
    # ones it is meant to explain. The first version of this scored only the 18 forced
    # cases and came back with $50 and $627 tied at 9 - identical, because almost any
    # variable sitting above $0A "explains" a drop that landed $0F. A test that cannot
    # tell two hypotheses apart is not evidence, however confident its output looks.
    #
    # The 41 plain-table drops are what give the test its power: a rule keyed on the wrong
    # variable fires the guarantee on some of those, where nothing landed, and is caught
    # by a false positive it cannot avoid. So the score is exact predictions over all of
    # them, and a candidate only wins by being right about the drops it must NOT explain.
    def full_predict(h, row, cycle, swapped, coff):
        """The whole of SetUpDroppedItem's decision, in assembly order.

        `swapped` exchanges the two counters. `coff` shifts the table column, which is a
        separate question from which counter is which and is searched separately so the two
        cannot flatter each other.
        """
        fairy, help = (h[1], h[4]) if swapped else (h[4], h[1])
        if fairy == 0x10:
            return 0x23
        if help >= 0x0A:
            return 0x0F if h[2] == 0 else 0x00
        return DROP_TABLE[row][(cycle + coff) % 10]

    pool = [p for p in paired
            if p["kill"]["kind"] == "table"
            and p["kill"]["monster"] in LISTED
            and not (p["kill"]["slot"] == 1 and p["kill"]["monster"] in SLOT1_NO_DROP)]
    print(f"  {len(pool)} drops from the 24 listed moblin types, scored as complete "
          f"predictions\n")
    print("  Row 3 is excluded on purpose. It is 'every type the game did not list', which "
          "includes\n  bosses and scenery that never reach SetUpDroppedItem, and leaving "
          "them in dropped the\n  score from 86% to 70% - a pool problem wearing the costume "
          "of a table error.\n")
    print(f"  {'guarantee/fairy counter':<22} {'sampled at':<12} "
          f"{'exact':>6} {'of':>4}  column")
    results = []
    for swapped in (False, True):
        label0 = "$627 fairy / $50 guarantee" if not swapped else "$50 fairy / $627 guarantee"
        for off in (-3, -2, -1, 0, 1, 2, 3):
            for coff in (-1, 0, 1):
                n = 0
                for p in pool:
                    d = p["kill"] and p["drop"]
                    hist = {h[0]: h for h in d.get("hist", [])}
                    if not hist:
                        continue
                    frame = d["frame"] + off
                    h = hist.get(frame) or hist[min(hist, key=lambda f: abs(f - frame))]
                    if full_predict(h, p["kill"]["row"], p["kill"]["cycle"],
                                    swapped, coff) == d["observed"]:
                        n += 1
                results.append((n, label0, f"drop{off:+d}", coff))
    results.sort(key=lambda r: -r[0])
    for n, lab, at, coff in results[:6]:
        c = "col+0" if coff == 0 else f"col{coff:+d}"
        print(f"  {lab:<22} {at:<12} {n:>6} {len(pool):>4}  {c}")
    top = results[0]
    tied = [r for r in results if r[0] == top[0]]
    runner = next((r for r in results if r[0] < top[0]), None)
    print(f"\n  best {top[0]}/{len(pool)}"
          + (f", next distinct rule {runner[0]}/{len(pool)}" if runner else ", and nothing else scored"))
    if len(tied) > 1:
        offs = sorted(r[2] for r in tied)
        print(f"  {len(tied)} offsets tie at the top ({', '.join(offs)}). That is one rule, not "
              f"{len(tied)}:\n  the counters do not move inside that window, so every offset "
              f"in it is the same\n  sample. A flat region is not a weak result and not a "
              f"margin of 1.")
    if top[0] < len(pool) * 0.9:
        print("  Under 90% means no candidate here is the rule, and the model is still "
              "missing\n  something. Report that; do not promote the winner anyway.")


if __name__ == "__main__":
    raise SystemExit(main())
