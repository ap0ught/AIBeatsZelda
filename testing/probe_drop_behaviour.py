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

# ---- the cartridge's drop rules, cited to the disassembly -------------------------
NO_DROP = [0x5D, 0x14, 0x15, 0x1B, 0x1C, 0x1D, 0x17]
ROW0 = [0x07, 0x08, 0x0E, 0x04, 0x0F, 0x23]
ROW1 = [0x21, 0x22, 0x0D, 0x10, 0x13, 0x28, 0x2A, 0x27, 0x16]
ROW2 = [0x09, 0x0A, 0x03, 0x01, 0x12, 0x06, 0x0B, 0x24, 0x30]
RATES = [0x50, 0x98, 0x68, 0x68]     # a drop is cancelled when Random >= this
# 4 rows x 10 columns: DropItemSetBaseOffsets ($00,$0A,$14,$1E) + WorldKillCycle.
DROP_TABLE = [
    [0x22, 0x18, 0x22, 0x18, 0x23, 0x18, 0x22, 0x22, 0x18, 0x18],
    [0x0F, 0x18, 0x22, 0x18, 0x0F, 0x22, 0x21, 0x18, 0x18, 0x18],
    [0x22, 0x00, 0x18, 0x21, 0x18, 0x22, 0x00, 0x18, 0x00, 0x22],
    [0x22, 0x22, 0x22, 0x23, 0x18, 0x22, 0x23, 0x22, 0x22, 0x18],
]
SLOT1_NO_DROP = (0x2A, 0x30)      # `CPX #$01` - keyed on the SLOT, not the type

OBJ_TYPE = 0x34F     # ObjType; $60 is UpdateItem, i.e. a dropped item
ITEM_ID = 0xAC       # Item_ObjItemId
RND = 0x18           # Random, an array indexed by object slot
HELP_COUNT, HELP_VALUE = 0x50, 0x51
WORLD_CYCLE, WORLD_COUNT = 0x52A, 0x627
NSLOT = 12           # slots 1..11; slot 0 is Link
DROP_TYPE = 0x60
PAIR_WINDOW = 40     # frames; a drop is attributed to the nearest kill before it


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
    """`SetUpDroppedItem` for one kill.  Returns (item or None, why).

    `kind` is 'fairy', 'guarantee' or 'table', decided by the two counter compares in the
    order the assembly tests them.  Deliberately does NOT model the random cancel - see
    the docstring on why a stale `Random` read would make that prediction a lie.
    """
    if kind == "fairy":
        return 0x23, f"fairy: WorldKillCount ${kill_count:02X} == $10 exactly"
    if kind == "guarantee":
        return (0x0F if help_value == 0 else 0x00), (
            f"guarantee: HelpDropCount ${help_count:02X} >= $0A, "
            f"HelpDropValue ${help_value:02X}")
    if mtype in NO_DROP:
        return None, f"no-drop type ${mtype:02X}"
    if slot == 1 and mtype in SLOT1_NO_DROP:
        return None, f"slot-1 ${mtype:02X} may already carry a room item"
    return DROP_TABLE[row_of(mtype)][cycle], (
        f"table row {row_of(mtype)} column {cycle}")


def kind_of(help_count, kill_count):
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
    nframes = 0

    with BizHawk(rom=rom, log_name="dropbehaviour.log") as emu:
        print("  connected", flush=True)
        prev = emu.ram(OBJ_TYPE, NSLOT)
        for i, btn in enumerate(frames):
            emu.step(btn, 1)
            nframes = i + 1
            cur = emu.ram(OBJ_TYPE, NSLOT)

            for s in range(1, NSLOT):
                was, now = prev[s], cur[s]
                if 0 < was < 0x50 and not (0 < now < 0x50):
                    help_count = emu.byte(HELP_COUNT)
                    help_value = emu.byte(HELP_VALUE)
                    kill_count = emu.byte(WORLD_COUNT)
                    kills.append(dict(frame=i, slot=s, monster=was,
                                      row=row_of(was), cycle=emu.byte(WORLD_CYCLE),
                                      kind=kind_of(help_count, kill_count),
                                      help_count=help_count, help_value=help_value,
                                      kill_count=kill_count))
                if now == DROP_TYPE and was != DROP_TYPE:
                    drops.append(dict(frame=i, slot=s, observed=emu.ram(ITEM_ID, NSLOT)[s]))

            prev = cur
            if nframes % 5000 == 0:
                el = time.time() - t0
                rate = nframes / el
                print(f"  f{nframes:>7}  {rate:6.1f} f/s  {len(kills)} kills  "
                      f"{len(drops)} drops  "
                      f"eta {(len(frames) - nframes) / rate / 60:5.1f} min", flush=True)

    return report(kills, drops, nframes, time.time() - t0, inputs)


def report(kills, drops, nframes, elapsed, inputs) -> int:
    print(f"\n{nframes} frames in {elapsed:.0f}s")
    print(f"  {len(kills)} kills, {len(drops)} drop objects "
          f"({len(drops) / max(1, len(kills)) * 100:.1f}% of kills)\n")

    # pair each drop with the nearest preceding kill
    used = set()
    paired, unpaired = [], []
    for d in drops:
        best = None
        for idx, k in enumerate(kills):
            if idx in used or k["frame"] > d["frame"] or d["frame"] - k["frame"] > PAIR_WINDOW:
                continue
            if best is None or k["frame"] > kills[best]["frame"]:
                best = idx
        if best is None:
            unpaired.append(d)
        else:
            used.add(best)
            k = kills[best]
            pred, why = predict(k["kind"], k["slot"], k["monster"], k["cycle"],
                                k["help_count"], k["help_value"], k["kill_count"])
            paired.append(dict(drop=d, kill=k, predicted=pred, why=why))

    tally = collections.Counter()
    mism = []
    for p in paired:
        if p["predicted"] == p["drop"]["observed"]:
            tally["agree"] += 1
        else:
            tally["MISMATCH"] += 1
            mism.append(p)
    tally["no drop predicted"] = sum(1 for p in paired if p["predicted"] is None)

    print("per-drop, table prediction vs what landed:")
    for k, v in sorted(tally.items()):
        print(f"  {k:<22} {v}")
    if unpaired:
        print(f"  {'(no kill within window)':<22} {len(unpaired)}")

    # The rate check: this is the cancel, and it is a separate question from the table.
    print("\ndrop frequency per row, against what DropItemRates implies:")
    print(f"  {'row':>4} {'kills':>7} {'drops':>6} {'observed':>9} {'implied':>8}  verdict")
    rows = collections.defaultdict(lambda: [0, 0])
    for k in kills:
        if k["row"] >= 0 and k["kind"] == "table":
            rows[k["row"]][0] += 1
    for p in paired:
        if p["kill"]["row"] >= 0 and p["kill"]["kind"] == "table" and p["predicted"] is not None:
            rows[p["kill"]["row"]][1] += 1
    shortfalls = 0
    for r in sorted(rows):
        n, d = rows[r]
        if not n:
            continue
        obs, imp = d / n, RATES[r] / 256
        short = obs < imp * 0.6
        shortfalls += short
        print(f"  {r:>4} {n:>7} {d:>6} {obs * 100:>8.1f}% {imp * 100:>7.1f}%"
              + ("   shortfall - cancel fires more often than the table says"
                 if short else "   consistent"))

    if mism:
        print(f"\n{len(mism)} MISMATCH(es) - the table itself, not the cancel:")
        for p in mism:
            k, d = p["kill"], p["drop"]
            print(f"  f{d['frame']:>7} killed ${k['monster']:02X} (row {k['row']}, col "
                  f"{k['cycle']}, {k['kind']}) -> predicted ${p['predicted']:02X}, "
                  f"landed ${d['observed']:02X}")
            print(f"          {p['why']}  kill at f{k['frame']} slot {k['slot']}, "
                  f"drop in slot {d['slot']}")
    else:
        print("\nno MISMATCH: every drop that landed is the item the table names.")

    if shortfalls:
        print(f"\n{shortfalls} row(s) show a drop-rate shortfall. That is the random cancel, "
              f"not the table -\nsee the docstring; do not read it as a wrong table.")

    out = Path("logs/drop_behaviour.json")
    out.write_text(json.dumps(dict(kills=kills, drops=drops, frames=nframes,
                                   inputs=str(inputs)), indent=1))
    print(f"\nper-event log: {out}")
    return 1 if mism else 0


if __name__ == "__main__":
    raise SystemExit(main())
