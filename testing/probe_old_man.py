"""The old man in the White Sword cave: is he a wall, and does a full heart bar change what he does?

What the harness believes, and where each belief came from:

1. journal/15: "A room with an old man is a trap for a planner... his text freezes Link for about 140
   frames... the navigator planned a route, took one step, found it blocked - because Link was frozen,
   not because the way was shut - and wrote down 'cannot step up from here' as a permanent fact."
   So every policy now walks Link INTO the room and holds the direction until he moves.

2. The owner's note, 2026-10-01: "if you had full life you would be in revenge mode, but since you are
   not you will flee." A claim about BEHAVIOUR, and the route walks into that cave at 3.5/5.

Neither has been tested, and the reason is a gap in what got saved: both `*_white_sword` checkpoints
are taken AFTER the segment succeeded - Link already has the sword ($657 = 2) and the item slot reads
$BF = FF, nothing lying - so "go back and look" needs a state from BEFORE the pickup, and there is
not one. The nearest thing is `ckpt_*_ws_0a`: the screen the cave is on, in two different runs, with
two different heart bars (gleeok 3.5/5, fullgame 4.5/5). Same screen, same policy, different life -
which is not a controlled experiment but it is the only pair of states that exists, and if the old man
behaves differently between them that is worth knowing before a route depends on it.

Both sides run the real `white_sword` segment policy from the real checkpoint and report what Link
paid, whether the sword changed hands ($657), and where he finished. The object table is dumped the
moment the emulator is inside the cave, because the only note on the old man's identity is journal/14's
"he, his two flanking torches (type 0x40) and the item all live in the same twenty object slots".

NOTE ON WHAT IS NOT BEING CLAIMED: this cannot separate "the old man blocks at 3.5 and moves at 4.5"
from anything else that differs between two runs - the Blue Lynel on this screen hits for two hearts,
so the low-life side can simply be dying to the Lynel on the way in. Read the end room and position
before reading anything into the sword.

Run it:  python3 testing/probe_old_man.py [attempts]
"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, states/ are repo-relative
_os.environ.setdefault("ZELDA_ROUTE", "5")
ATTEMPTS = int(_os.environ.get("PROBE_ATTEMPTS", "3"))
del _os, _sys, _pathlib
import random

import fullgame
from zelda.emulator import BizHawk
from zelda.overworld import Navigator, read_room_item, read_enemies
from zelda.search import Recorder

SIDES = (("gleeok  3.5/5", "ckpt_gleeok_ws_0a"),      # this run's route-5 arrival
         ("fullgame 4.5/5", "ckpt_fullgame_ws_0a"))   # run6's, the one that got through


def cave_report(emu) -> str:
    """What is in the room, once we are actually inside the cave."""
    s = emu.state()
    obj = " ".join(f"{emu.byte(i):02X}" for i in range(0xA0, 0xC0, 2))
    ens = [(hex(e[1]), e[2], e[3]) for e in read_enemies(emu)][:4]
    return (f"room {s.room:02X} mode {s.mode:02X} pos ({s.x},{s.y}) | item {read_room_item(emu)} "
            f"| enemies {ens or 'none'} | $A0-$BF {obj}")


def run(factory, success, ckpt, seeds=ATTEMPTS):
    emu = BizHawk(log_name=f"probe_old_man_{ckpt}.log", clean_sram=False)
    try:
        emu.load(ckpt)
        nav = Navigator(emu)
        s0 = emu.state()
        rows, caves, saved = [], set(), []
        for seed in range(1000, 1000 + seeds):
            root = emu.msave()
            rec = Recorder(emu)
            # Save the state the moment Link is INSIDE the cave and before the sword is taken. That
            # state does not exist anywhere in the tree - every *_white_sword checkpoint is taken
            # after the segment succeeded, so the old man has already been dealt with by the time
            # there is a savestate of the room - and the harness cannot write RAM to invent one (the
            # input log is the artifact; poking $66F would be a run that never happened). Leaving one
            # behind here is what makes the next question answerable: what is he, and what does he do.
            inner = rec.step

            def watched(buttons=(), frames=1, _inner=inner, _first=[True]):
                st = _inner(buttons, frames)
                if _first[0] and (st.mode == 0x0B or st.room != s0.room) and st.sword == s0.sword:
                    _first[0] = False
                    name = f"probe_old_man_{ckpt.split('_')[-1]}_inside"
                    emu.save(f"ckpt_{name}")
                    saved.append(name)
                    caves.add(cave_report(emu))
                return st

            rec.step = watched
            try:
                res = factory(nav)(emu, rec, random.Random(seed), 3000)
            except Exception as e:
                res = f"raised {type(e).__name__}: {str(e)[:36]}"
            s1 = emu.state()
            emu.mload(root)
            emu.mfree(root)
            rows.append((seed, len(rec.inputs), str(res)[:24], f"{s0.hearts:.1f}->{s1.hearts:.1f}",
                         f"{s0.sword}->{s1.sword}", f"({s1.x},{s1.y}) f{s1.frame}", bool(success(emu, s1))))
        return s0, rows, sorted(caves), saved
    finally:
        emu.close()


def main():
    seg = {s[0]: s for s in fullgame.segments()}
    name = "white_sword"
    _n, factory, success, _t = seg[name]
    print(f"probe_old_man: segment {name!r}, {ATTEMPTS} attempts a side, two ws_0a states with "
          f"different heart bars\n", flush=True)
    for tag, ckpt in SIDES:
        s0, rows, caves, saved = run(factory, success, ckpt)
        print(f"--- {tag}  from {ckpt}: hearts {s0.hearts}/{s0.containers}, sword {s0.sword}, "
              f"bombs {s0.bombs}, room {s0.room:02X}", flush=True)
        for seed, frames, res, hearts, sword, pos, ok in rows:
            print(f"    seed {seed}: {frames:5d} frames  hearts {hearts:>9}  sword {sword:<8} "
                  f"{pos:<16} {'PASS' if ok else '----'}  {res}", flush=True)
        got = sum(1 for r in rows if r[6])
        print(f"    passed {got}/{len(rows)}", flush=True)
        for c in caves:
            print(f"    inside the cave: {c}", flush=True)
        for n in saved:
            print(f"    SAVED ckpt_{n} - inside the cave, sword still {s0.sword}. That state did not "
                  f"exist before this probe", flush=True)
        if not caves:
            print("    never got inside: died on the screen, so this side says nothing about the "
                  "old man", flush=True)
        print(flush=True)


if __name__ == "__main__":
    main()