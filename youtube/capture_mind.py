"""Mind's-eye footage: re-run the planner on the KEPT take of a fight from run 6 (same bookmark, same seed, so the
emulator reproduces the exact frames of the verified run) with the decision log switched on, and film every frame.
Output: youtube/capture/mind/<segment>/NNNN.png + decisions.json (per decision: Link, enemies with facing and hp, the
walking-distance field to the strike spots, all candidate futures with their scores, and the choice).

usage: python youtube/capture_mind.py <segment> <seed>      (seed = 1000 + winning attempt - 1)"""
import json, os, pathlib, random, shutil, sys
sys.path.insert(0, ".")
os.environ["ZELDA_ROUTE"] = "4"
import fullgame as fg
from zelda import runner, lookahead, search
from zelda.emulator import BizHawk
from zelda.overworld import Navigator
from zelda.search import Recorder
seg, seed = sys.argv[1], int(sys.argv[2])
segs = fg.segments(); names = [s[0] for s in segs]; i = names.index(seg)
ARCH = pathlib.Path("logs/archive/sixth_run_20260922")
a = json.load(open(ARCH / f"checkpoints/fullgame_{names[i - 1]}.json"))
b = json.load(open(ARCH / f"checkpoints/fullgame_{seg}.json"))
kept = b["inputs"][a["frames"]:b["frames"]]
out = pathlib.Path("youtube/capture/mind") / seg; out.mkdir(parents=True, exist_ok=True)
emu = BizHawk(log_name="capture_mind.log", clean_sram=False); nav = Navigator(emu)
s0 = emu.load(f"run6/ckpt_fullgame_{names[i - 1]}"); runner.SEG_START = s0
free = seg in runner.REFILL_SOON
search.HEARTS_FREE[0] = free; lookahead.CAUTION_OVERRIDE[0] = 0.12 if free else None
shots = []
orig_step = emu.step
def filmed_step(buttons=(), frames=1):
    s = None
    for _ in range(frames):
        s = orig_step(buttons, 1)
        shots.append(1)
    return s
rec = Recorder(emu)
# film only the frames the recorder plays (branches are not filmed): wrap rec's raw step
raw = rec._raw_step
def raw_filmed(buttons=(), frames=1):
    s = None
    for _ in range(frames):
        s = raw(buttons, 1)
        k = len(rec.inputs)
        shutil.copyfile(emu.screenshot("_mind_tmp"), out / f"{k - 1:04d}.png")
    return s
rec._raw_step = raw_filmed
if search.SETTLE[0]:
    rec.step((), search.SETTLE[0])
lookahead.DECISION_LOG[0] = []
rng = random.Random(seed)
outcome = segs[i][1](nav)(emu, rec, rng, 3000)
mine = [",".join(x) for x in rec.inputs]
match = mine == kept
print(seg, "outcome", outcome, "frames", len(mine), "kept", len(kept), "IDENTICAL" if match else "DIFFERS at " + str(next((j for j in range(min(len(mine), len(kept))) if mine[j] != kept[j]), -1)))
json.dump({"segment": seg, "seed": seed, "frames": len(mine), "identical_to_run": match, "inputs": mine,
           "decisions": lookahead.DECISION_LOG[0]}, open(out / "decisions.json", "w"))
print(len(lookahead.DECISION_LOG[0]), "decisions logged")
emu.close()
