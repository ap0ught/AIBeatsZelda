"""Does the input log already sitting in the checkpoints actually reach the dragon, from power-on?

The question this exists to answer is not "is the checkpoint there". It is that the run named
`gleeok` on route 5 stopped on 2026-10-01 at `RuntimeError: segment l2_sail failed` with 161
segments and 60,589 frames banked, and its whole input prefix lives only inside the per-segment
checkpoint JSONs - `save_checkpoint` stores the entire `inputs` list in every one of them, because
a resume has to restore the log and not just the state. Nothing was written to logs/*.inputs.txt,
because `Run.finish()` is what writes that and this run never finished. The artefact that would
prove the run exists is exactly the thing the run died without producing.

Three questions, and they are separate:

1. WHERE the run got to, in frames. Free: every segment banks its own json carrying the total frame
   count at that moment, and the `segments` list in the last one is the run's own account of what it
   had played. No emulator, and these are the numbers to quote.

2. Whether that log REPRODUCES the run. Replayed from power-on in a fresh emulator - clean
   cartridge, wiped battery save - and compared two ways: the sha1 of work RAM against the sha1 of
   the bookmark `ckpt_<segment>.State` that the run itself saved, and the parsed final state against
   the summary string the run wrote when it banked that segment. The fingerprint is the check
   `Run.finish()` uses; the state string is here so that a mismatch says WHAT differs instead of
   only that something does.

3. Whether the three Gleeok claims are true of the REPLAYED run in RAM rather than of the
   checkpoint's paperwork: the dragon dead (`zelda.boss.gleeok_dead`), the head off the floor of
   room $13 of level 4 (`zelda.head.taken_test`), and the head down in the sword cave on the White
   Sword's x (`zelda.head.delivered_test`). Those are the project's own tests, called as written; a
   second implementation of them here would be an opinion nobody asked for.

Run:  python3 testing/probe_deliver_replay.py [checkpoint] [--no-replay]
The argument is the SEGMENT name, not the file name: the run is `gleeok` and the file is
gleeok_<segment>.json. Default `deliver`, the last one that run banked. `--no-replay` skips question 2
and 3's replay (about seven minutes of wall clock for 60,589 frames on a loaded machine) and asks only
the RAM claims against the bookmarks - which is only meaningful once a full run has printed MATCH.
Needs a display.

WHAT IT DOES NOT CLAIM. One emulator, one cartridge (the launch banner says so if it is not the
verified md5), one run's random search. It says nothing about whether the log is the fastest line
through those rooms - 75 segments in flagged.json were taken under ACCEPT_AFTER and never polished -
and nothing at all about the run past `deliver`, which is where the run actually died: the next
segment in route 5 is `l2_sail`, whose policy is `dock_policy`, and the head delivery leaves Link
INSIDE the cave at mode $0B, so all 60 attempts read "fail: no dock on this screen @ room 0A L0".
That is a route-ordering problem, and it is not measured here.

Also not recovered: the x the White Sword came from. `zelda/head.py` keeps it in a module global
filled in by `remember_spot` at the moment the sword is taken, in whichever process ran that
segment; no process survives, so a fresh one falls back to 120. The replayed log ends at x=120,
which is what the fallback asks for, and it is also what the run's own banked summary says - but
that is two copies of one number agreeing, not independent evidence of where the sword was.
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from zelda import replay
from zelda.emulator import BizHawk
from zelda.runner import CKPT_DIR

RUN = "gleeok"
WANT = ("gleeok", "gleeok_head", "revenge", "deliver")


def banked_frames(seg: str) -> object:
    """The frame count at which `seg` was banked, from that segment's own checkpoint json."""
    p = CKPT_DIR / f"{RUN}_{seg}.json"
    return json.loads(p.read_text())["frames"] if p.exists() else "no checkpoint"


def where(name: str) -> None:
    print(f"--- what the run banked, read out of the checkpoint jsons (no emulator)", flush=True)
    d = json.loads((CKPT_DIR / f"{RUN}_{name}.json").read_text())
    done = d["segments"]
    print(f"  {RUN}_{name}: {len(done)} segments, {d['frames']} frames, hearts {d['hearts']}, "
          f"keys {d['keys']}, bombs {d['bombs']}, list_hash {d['list_hash']}", flush=True)
    for i, seg in enumerate(done):
        if seg in WANT:
            print(f"    segment {i + 1:3d} of {len(done):3d}  {seg:12s} "
                  f"banked at frame {banked_frames(seg)}", flush=True)
    print(f"  first three: {done[:3]}", flush=True)
    print(f"  last three:  {done[-3:]}", flush=True)


def main() -> None:
    name = next((a for a in sys.argv[1:] if not a.startswith("-")), "deliver")   # gleeok_<name>.json
    meta = CKPT_DIR / f"{RUN}_{name}.json"
    if not meta.exists():
        raise SystemExit(f"no checkpoint json at {meta}")
    d = json.loads(meta.read_text())
    # An idle frame is banked as the empty string, and ",".join(()) is "" - so the split yields [""]
    # and has to be filtered or the run opens on "unknown button ''".
    frames = [tuple(b for b in l.split(",") if b) for l in d["inputs"]]
    print(f"{RUN}_{name}: {len(frames)} frames of input in the json, "
          f"its own counter says {d['frames']}, summary {d['summary']}", flush=True)
    where(name)

    with BizHawk(log_name="probe_deliver_replay.log") as emu:
        try:
            emu.cmd("phase verify")
        except Exception:
            pass
        if "--no-replay" in sys.argv:
            print("--- --no-replay: skipping the 60,000-frame replay, claims only", flush=True)
        else:
            print(f"--- replaying {len(frames)} frames from power-on, one window stepped every frame",
                  flush=True)
            s_end = replay.run_inputs(emu, frames)
            fp_end = replay.fingerprint(emu)
            print(f"  replay          -> {s_end}\n    work-RAM sha1 {fp_end}", flush=True)
            ck = emu.load(f"ckpt_{RUN}_{name}")
            fp_ck = replay.fingerprint(emu)
            print(f"  ckpt_{RUN}_{name} -> {ck}\n    work-RAM sha1 {fp_ck}", flush=True)
            print(f"\n  fingerprint {'MATCH' if fp_end == fp_ck else 'MISMATCH'}", flush=True)
            print(f"  state       {'MATCH' if str(s_end) == str(ck) else 'MISMATCH'}"
                  + ("" if str(s_end) == str(ck) else f"   (the bookmark says {ck})"), flush=True)
        claims(emu)
    print("\nIf the fingerprint says MATCH then the log inside the checkpoints is a run from power-on "
          "that reaches the dragon and the head. It is not yet logs/*.inputs.txt, and it is not the "
          "whole game: the route's next segment failed.", flush=True)


def claims(emu) -> None:
    # The three claims, in RAM, through the project's own tests. Asked of the BOOKMARKS rather than
    # of a second replay: the fingerprint equality is what licenses that, and it is a license with a
    # number on it rather than an assumption.
    #
    # And each claim has to be asked where it is a question at all. $034D - the flag gleeok_dead
    # reads first - is set per ROOM when that room is finished, so asking it at the end of this run
    # asks about the sword cave, where the answer is a confident False about two cave objects. The
    # first version of this probe did exactly that and printed "Gleeok dead False" under a heading
    # that said "at the end of the replayed run". The dragon's death is a fact about room $13 of
    # level 4 and has to be asked there.
    name = next((a for a in sys.argv[1:] if not a.startswith("-")), "deliver")
    from zelda import head
    from zelda.boss import gleeok_dead
    from zelda.overworld import read_enemies
    print("\n--- the three claims, in RAM, each asked where it is a question at all", flush=True)
    t = emu.load(f"ckpt_{RUN}_gleeok")
    print(f"  Gleeok dead      {gleeok_dead(emu)}   (asked in {t}; $034D={emu.byte(0x34D):#04x}, "
          f"{len(read_enemies(emu))} objects, banked at frame {banked_frames('gleeok')})", flush=True)
    print(f"  head taken       {head.taken_test(emu, t)}   (asked in the same bookmark; floor "
          f"spot {head.floor_spot(emu)}, Link at ({t.x},{t.y}))", flush=True)
    t = emu.load(f"ckpt_{RUN}_gleeok_head")
    print(f"     ...and again   {head.taken_test(emu, t)}   (asked in ckpt_{RUN}_gleeok_head, "
          f"Link at ({t.x},{t.y}) mode={t.mode:#04x} L{t.level} room={t.room:#04x}, banked at "
          f"frame {banked_frames('gleeok_head')})", flush=True)
    q = emu.load(f"ckpt_{RUN}_{name}")
    print(f"  head delivered   {head.delivered_test(emu, q)}   (asked in ckpt_{RUN}_{name}: "
          f"x={q.x}, mode={q.mode:#04x}, sub={q.sub}, level={q.level}, room={q.room:#04x}); "
          f"the White Sword's x as this process knows it: {head.spot()} (None = the fallback 120, "
          f"because remember_spot ran in a process that is gone)", flush=True)
    print(f"  ...and NOT here  gleeok_dead={gleeok_dead(emu)} $034D={emu.byte(0x34D):#04x} - "
          f"the cave has no dragon and $034D is a per-room flag", flush=True)


main()