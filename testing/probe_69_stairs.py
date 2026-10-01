"""Does the dash planner know a Darknut's shield - and should this leg even offer the sword?

The question, from watching 69_stairs run: all four scouts walk into a knight and swing at its face.
The route's own caption for the room says the opposite plan - "None of these eight Darknuts needs to
die. Dash through them to the staircase on the east side" - so the planner is not failing to find a
line, it is choosing to fight a fight that cannot be won with a frontal sword.

Where the knowledge was missing: combat.py has had `shield_side` since the Darknut hunter was written
(a swing along the axis a knight faces is stopped by its shield; only side and back land), and
lookahead.py's killable() says a Darknut is killable - correctly, from the monster's side. Nothing
between the two ever asked whether THIS swing would land, so plan_reach offered a swing in all four
directions whenever anything killable was within 36 px, and scored the result by what happened next.
A swing into a shield scores no kill, so it should have lost on the score - except that it also moved
Link, and "moved Link" is most of what the score is made of.

THREE configurations, same room, same seeds, because there are two separate claims here and one run
cannot separate them:

  blind   transit=False, ZELDA_SHIELD_AWARE=0   what the route ran before either change
  aware   transit=False, ZELDA_SHIELD_AWARE=1   the shield-aware swing filter, sword still priced
  dash    transit=True                          no sword offered at all, damage not priced

WHAT IT FOUND, 2026-10-01, room $69 from ckpt_gleeok_59_fight, four attempts a side, same seeds:

| | passes | deaths | sword frames | frames of the passes |
|---|---|---|---|---|
| blind | 3/4 | 1 | 46, 26, 36, 18 | 818, 639, 394 |
| aware | 2/4 | **0** | 0, 2, 0, 0 | 505, 559 |
| dash (transit) | 1/4 | 2 | 0, 0, 0, 0 | 355 |

1. "It swings at knights head-on." TRUE of the old planner and it is most of what it was doing: 18-46
   frames of sword per attempt, all of it into shields. With `swing_connects` those swings are not
   offered at all and the sword drops to 0-2 frames. The room needs no fighting.

2. `transit=True` is NOT the answer, and the caption that says "none of these eight Darknuts needs to
   die" is not a reason to believe it. transit deletes the damage price along with the sword, so the
   planner walks into eight knights: 1 pass and 2 deaths, dead at 176 and 323 frames - the worst of the
   three. Not fighting and not being hurt are different things, and this room has eight of the second
   in it. The route does not ask for transit on either Darknut leg.

3. Deaths went to zero with the shield-aware planner, and the passes cost about the same (394-818
   blind, 505-559 aware). Two of the aware attempts still failed WITHOUT dying, ending in mode $10
   and mode $07 rather than the cellar in mode $09 - a stairwell transition that did not finish, which
   is the next thing to look at and is not a shield problem. Four seeds is too few to rank the pass
   counts (2/4 against 3/4 is noise); it is enough to rank the deaths and the sword.

The frame means are not quoted for the same reason probe_walls does not quote them: they move between
runs while the behaviour underneath them stays put.

The numbers printed are the ones the change is meant to move: attempts that end in death, hearts lost
getting past a knight, sword frames spent, whether the stairs actually fired, and the frames the leg
took. The end room matters: "reached" from plan_reach can mean "arrived" or "left the room", and a
segment whose success test wants the cellar has to tell those apart.

Run it:  python3 testing/probe_69_stairs.py [attempts]
"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, states/ are repo-relative
ATTEMPTS = int(_os.environ.get("PROBE_ATTEMPTS", "4"))
del _os, _sys, _pathlib
import random

from zelda import lookahead
from zelda.emulator import BizHawk
from zelda.overworld import Navigator
from zelda.search import Recorder
from zelda.segments import make_lareach_policy

CKPT = "gleeok_59_fight"        # the state 69_stairs starts from: Level 3 room $69, eight Darknuts
GOAL = (208, 141)               # the east staircase; the route's Goal(208, 141, 6)


class Goal:
    def __init__(self, t, r=6):
        self.target, self.radius = t, r

    def __call__(self, x, y):
        return abs(x - self.target[0]) <= self.radius and abs(y - self.target[1]) <= self.radius


def knights(emu):
    """(type, x, y, facing) for every Darknut in the room, from the enemy's own direction byte."""
    from zelda.overworld import read_enemies
    return [(e[1], e[2], e[3], lookahead.facing_of(emu, e[0]))
            for e in read_enemies(emu) if e[1] in lookahead.DARKNUT_TYPES]


def run(tag, *, transit, shield_aware):
    lookahead.SHIELD_AWARE[0] = shield_aware
    emu = BizHawk(log_name=f"probe_69_{tag}.log", clean_sram=False)
    try:
        emu.load(f"ckpt_{CKPT}")
        nav = Navigator(emu)
        policy = make_lareach_policy(nav, Goal(GOAL), exit_ok=True, transit=transit)
        out = []
        for seed in range(1000, 1000 + ATTEMPTS):
            root = emu.msave()
            rec = Recorder(emu)
            s0 = emu.state()
            try:
                res = policy(emu, rec, random.Random(seed), 3000)
            except Exception as e:
                res = f"raised {type(e).__name__}: {str(e)[:40]}"
            s1 = emu.state()
            emu.mload(root)
            emu.mfree(root)
            sword = sum(1 for b in rec.inputs if "A" in b)
            passed = s1.mode == 9 and s1.room == 0x0F and s1.hearts > 0
            out.append({"seed": seed, "frames": len(rec.inputs), "res": str(res)[:22],
                        "hearts": f"{s0.hearts:.1f}->{s1.hearts:.1f}", "sword": sword,
                        "end": f"room {s1.room:02X} mode {s1.mode:02X}", "ok": passed})
        return out, knights(emu)
    finally:
        emu.close()


CONFIGS = (("blind", dict(transit=False, shield_aware=False)),
           ("aware", dict(transit=False, shield_aware=True)),
           ("dash ", dict(transit=True, shield_aware=True)))


def main():
    print(f"probe_69_stairs: room $69 from ckpt_{CKPT}, {ATTEMPTS} attempts a side, same seeds\n",
          flush=True)
    for tag, kw in CONFIGS:
        rows, kn = run(tag.strip(), **kw)
        print(f"--- {tag}  transit={kw['transit']!s:5} shield_aware={kw['shield_aware']!s:5} "
              f"| {len(kn)} Darknuts: "
              + ", ".join(f"${t:02X}@({x},{y}) f{f}" for t, x, y, f in kn[:3]), flush=True)
        for r in rows:
            mark = "PASS" if r["ok"] else ("died" if r["res"].startswith("died") else "----")
            print(f"    seed {r['seed']}: {r['frames']:5d} frames  sword {r['sword']:3d}  "
                  f"hearts {r['hearts']:>9}  {r['end']}  {mark:4}  {r['res']}", flush=True)
        ok = [r for r in rows if r["ok"]]
        print(f"    passed {len(ok)}/{len(rows)}   died {sum(1 for r in rows if r['res'].startswith('died'))}"
              f"   lost health {sum(1 for r in rows if r['hearts'].endswith(tuple('0123456789')) and r['hearts'].split('->')[0] != r['hearts'].split('->')[1])}"
              f"   frames of passes {[r['frames'] for r in ok] or '-'}", flush=True)
        print(flush=True)


if __name__ == "__main__":
    main()