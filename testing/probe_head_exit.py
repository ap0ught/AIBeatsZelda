"""Can Link get from the sword cave, after leaving the head in it, to Level 1's door - and by which road?

Route 5 died on 2026-10-01 at `RuntimeError: segment l2_sail failed`, sixty attempts of
"fail: no dock on this screen @ room 0A L0". The cause is in the shape of the route rather than in
the segment: `head.deliver_policy` walks INTO the cave (mode $0B) to put the head down on the item
row, and the very next segment in route5.py is `l2_sail`, whose policy is `dock_policy`. There is no
dock inside a cave. So the segment had nothing to do from the state the previous one handed it, and
failing sixty times was the correct behaviour of a correct policy.

The second half of the same problem is one segment further on. route5.py's "NEW LEG 2" plans the walk
to Level 1's door from 0x45, the island bank: `l2_sail` rides the raft to 0x55 and five lanes take
0x55 -> 0x56 -> 0x46 -> 0x47 -> 0x48 -> 0x38 -> 0x37. But route 5 is not on the island when `deliver`
finishes - it is inside a cave on 0x0A - and 0x45 is only reachable by the raft, which is only
reachable from 0x55. Measured: the router cannot get from 0x0A to 0x55 or to 0x45 at all in the
direction that leg needs. So the whole raft leg is the wrong shape for where this route actually is,
not just one missing lane.

This probe asks the router, then walks the road it names with the real policies, from the real
bookmark the run left behind (`states/ckpt_gleeok_deliver.State`, Link inside the cave at 120,141 on
6.0 of 7 hearts). Four things:

1. THE ROAD. `owroute.dijkstra` from the spot `revenge` ended on, 0x0A at (192,141), collapsed to one
   lane per screen transition the way route5.py's own comments are written. Every seam's two ends are
   then asked directly whether `owroute.free()` calls them walkable, because a wrong coordinate does
   not fail - `_lane()` falls back to "leave wherever you can" and the symptom is a mysteriously slow
   search rather than an error.

2. GETTING OUT OF THE CAVE. Two ways, both measured from the same bookmark: the implicit one
   (`Navigator.exit_screen` has a mode-$0B branch that holds Down until the overworld comes back) and
   the explicit one (`bot.exit_cave_down`, whose corridor x is hardcoded to 112 for the candle cave -
   the sword cave's is not 112). Which one lands where, and how many frames each costs.

3. THE WALK. All of it, chained, with `make_cross_at_policy` exactly as route5.py's `lane()` builds
   it: out of the cave, then each lane in order, from the bookmark. Frames per leg and the state at
   each seam, because "the router says there is a path" and "Link walked it" are different claims.

4. THE NEW SEAM. Seven of the eight crossings below are the REVERSE of legs the run walked on its way
   home (rv_leg_47..50 and rv_leg_43..46), so they are known-good in one direction. 0x38 -> 0x37 is
   not: it is the only crossing here with no measured counterpart, and it is the one that decides
   whether this road works.

WHAT IT DOES NOT CLAIM. One walk, one seed, one bookmark, from a state the run reached by its own
search rather than from power-on. It does not claim the frames are good - they are one attempt with
jitter on, and a search will beat them - and it does not claim the road is the fastest one. It does
not touch the search, the ranking or the ranking's cutoff, and a lane that passes here can still lose
sixty attempts inside the search if an enemy is in the way. What it establishes is narrower and is
the thing that was missing: the route has a walkable, connected road from where `deliver` leaves Link
to where Level 1's door is, and it does not need the raft.

Run:  python3 testing/probe_head_exit.py
Needs a display.
"""
import os
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from zelda import bot, owroute
from zelda.emulator import BizHawk
from zelda.overworld import Navigator
from zelda.search import Recorder
from zelda.segments import make_cross_at_policy

CKPT = "ckpt_gleeok_deliver"

# The road the router names, and the pinned column/row each lane leaves from. `at` is x for Up/Down
# and y for Left/Right - Navigator.exit_screen's convention, not the router's arrival tuple.
LANES = [
    ("hd_0a_1a", "Down", 0x1A, 208),
    ("hd_1a_19", "Left", 0x19, 141),
    ("hd_19_18", "Left", 0x18, 141),
    ("hd_18_17", "Left", 0x17, 141),
    ("hd_17_27", "Down", 0x27, 160),
    ("hd_27_28", "Right", 0x28, 141),
    ("hd_28_38", "Down", 0x38, 112),
    ("hd_38_37", "Left", 0x37, 141),
]


def road() -> None:
    print("--- 1. the road, asked of the router (no emulator)", flush=True)
    start = (0x0A, 192, 141)            # where `revenge` banked: ckpt_gleeok_revenge, pos=(192,141)
    for goal, what in ((0x55, "the dock route 5 planned"), (0x37, "Level 1's door")):
        d, end, rooms = owroute.leg(start, goal, False, None)
        if d is None:
            print(f"  0x0A (192,141) -> {goal:#04x} ({what}): NO PATH", flush=True)
        else:
            print(f"  0x0A (192,141) -> {goal:#04x} ({what}): {d:.0f} frames, "
                  f"{len(rooms) - 1} crossings  " + " ".join(f"{r:02X}" for r in rooms), flush=True)
    d, end, prev = owroute.dijkstra(start, False, lambda n: n[0] == 0x37)
    assert end is not None, "the router found no road from 0x0A to 0x37; the LANES list below is stale"
    path = [end]
    while path[-1] in prev:
        path.append(prev[path[-1]])
    path.reverse()
    legs = [(a[0], b[0], b) for a, b in zip(path, path[1:]) if a[0] != b[0]]
    print("  collapsed to one lane per crossing, with each seam's pinned coordinate:", flush=True)
    for a, b, node in legs:
        delta = b - a
        d_name = ("Left" if delta == -1 else "Right" if delta == 1
                  else "Up" if delta == -16 else "Down")
        at = node[1] if d_name in ("Up", "Down") else node[2]
        print(f"    {a:02X} {d_name:5s} {b:02X} at {at}", flush=True)
    print("  each seam's two ends, asked of owroute.free() directly:", flush=True)
    for a, b, node in legs:
        delta = b - a
        d_name = ("Left" if delta == -1 else "Right" if delta == 1
                  else "Up" if delta == -16 else "Down")
        at = node[1] if d_name in ("Up", "Down") else node[2]
        if d_name in ("Up", "Down"):
            dep = (at, 221 if d_name == "Down" else 61)
            arr = (at, 61 if d_name == "Down" else 221)
        else:
            dep = (0 if d_name == "Left" else 240, at)
            arr = (240 if d_name == "Left" else 0, at)
        ok = dep in owroute.free(a, False) and arr in owroute.free(b, False)
        print(f"    {a:02X} {d_name:5s} {b:02X} at {at}: leaves {dep} and lands {arr} -> "
              f"{'both walkable' if ok else 'NOT WALKABLE'}", flush=True)
    mine = [f"{a:02X}->{b:02X}" for a, b, _ in legs]
    want = []
    prevr = 0x0A
    for _, _, b, _ in LANES:
        want.append(f"{prevr:02X}->{b:02X}")
        prevr = b
    print(f"  router's seams == the LANES list in this probe: {mine == want}"
          + ("" if mine == want else f"\n    router {mine}\n    probe  {want}"), flush=True)


def out_of_cave(emu, nav, rec, how: str) -> str:
    """Two ways out of the sword cave, measured from the same bookmark."""
    s = emu.state()
    print(f"  [{how}] starting at {s}", flush=True)
    if how == "implicit (Navigator.exit_screen's mode $0B branch)":
        try:
            s = nav.exit_screen("Down", at=208)
        except Exception as e:
            print(f"    raised {type(e).__name__}: {str(e)[:60]}", flush=True)
            return "raised"
    elif how == "explicit (bot.exit_cave_down, corridor x=112)":
        try:
            s = bot.exit_cave_down(emu, log=lambda *a: None)
        except Exception as e:
            print(f"    raised {type(e).__name__}: {str(e)[:60]}", flush=True)
            return "raised"
    else:                                              # hold Down until the overworld comes back
        s = emu.wait_until(lambda q: q.mode == 5 and not q.level, 600, buttons=("Down",))
        s = emu.wait(2)
    print(f"    -> {s}   ({len(rec.inputs)} frames so far)", flush=True)
    return str(s)


def walk(emu, nav, rng) -> None:
    print("\n--- 3. the whole walk, from the run's own bookmark, with the real policies", flush=True)
    emu.load(CKPT)
    rec = Recorder(emu)
    orig = emu.step
    emu.step = rec.step
    print(f"  loaded {CKPT}: {emu.state()}  ({len(rec.inputs)} frames)", flush=True)
    total = 0

    def leg(name, pol, want_room):
        nonlocal total
        nav.jitter = (rng, rng.choice([0.0, 0.05, 0.1]))
        n0 = len(rec.inputs)
        try:
            out = pol(emu, rec, rng, 3000)
        except Exception as e:
            out = f"raised {type(e).__name__}: {str(e)[:60]}"
        finally:
            nav.jitter = None
        q = emu.state()
        total += len(rec.inputs) - n0
        good = q.room == want_room and q.mode == 5 and q.level == 0 and q.hearts > 0
        print(f"    {name:10s} {len(rec.inputs) - n0:5d} frames  {out:22s} -> {q}  "
              f"{'OK' if good else 'WRONG SCREEN'}", flush=True)
        return good

    nav.jitter = (rng, 0.0)
    try:
        out_of_cave(emu, nav, rec, "implicit (Navigator.exit_screen's mode $0B branch)")
    finally:
        nav.jitter = None
    q = emu.state()
    if not (q.mode == 5 and not q.level and q.room == 0x0A):
        print(f"    implicit exit did not land on 0x0A in the overworld ({q}); reloading and "
              f"using the explicit one", flush=True)
        emu.load(CKPT)
        emu.step = rec.step
        nav.jitter = (rng, 0.0)
        try:
            out_of_cave(emu, nav, rec, "explicit (bot.exit_cave_down, corridor x=112)")
        finally:
            nav.jitter = None
        q = emu.state()
        print(f"    explicit exit -> {q}", flush=True)
    ok = True
    for name, d, room, at in LANES:
        pol = make_cross_at_policy(nav, d, at=at)
        ok = leg(name, pol, room) and ok
    print(f"  total {total} frames ({total / 60.0988:.0f}s of game time) from the head down in the "
          f"cave to Level 1's door: {'every lane landed where it was asked to' if ok else 'SOME LANE DID NOT'}",
          flush=True)
    emu.step = orig
    nav.jitter = None


def main() -> None:
    road()
    rng = random.Random(1000)
    with BizHawk(log_name="probe_head_exit.log") as emu:
        nav = Navigator(emu)
        print("\n--- 2. out of the cave, two ways, each from its own load of the bookmark",
              flush=True)
        for how in ("implicit (Navigator.exit_screen's mode $0B branch)",
                    "explicit (bot.exit_cave_down, corridor x=112)",
                    "plain hold Down until mode 05"):
            emu.load(CKPT)
            rec = Recorder(emu)
            orig = emu.step
            emu.step = rec.step
            try:
                out_of_cave(emu, nav, rec, how)
            finally:
                emu.step = orig
                nav.jitter = None
        walk(emu, nav, rng)


main()