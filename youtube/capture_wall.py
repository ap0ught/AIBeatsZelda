"""Search-wall footage: run the REAL search on one room from run 6's state, dumping every attempt, then replay each
attempt from the same bookmark in a recording emulator so every window of the wall is a real attempt with its real
outcome (died / cut off as slower than the best / finished, with frames and hearts).

usage: python youtube/capture_wall.py <segment> [scouts] [tries]      -> youtube/capture/wall/<segment>/"""
import json, os, pathlib, shutil, sys, time
sys.path.insert(0, ".")
os.environ["ZELDA_ROUTE"] = "4"
seg = sys.argv[1]; k = int(sys.argv[2]) if len(sys.argv) > 2 else 4; tries = int(sys.argv[3]) if len(sys.argv) > 3 else 60
out = pathlib.Path("youtube/capture/wall") / seg
dump = out / "attempts"
os.environ["ZELDA_SEARCH_DUMP"] = str(dump)
import fullgame as fg
from zelda import runner, search, lookahead
from zelda.emulator import BizHawk
from zelda.overworld import Navigator
segs = fg.segments(); names = [s[0] for s in segs]; i = names.index(seg)
state = f"run6/ckpt_fullgame_{names[i - 1]}"
if not (dump.exists() and any(dump.glob("attempt_*.json"))):
    scouts = [BizHawk(log_name=f"wall_scout{j}.log", clean_sram=False) for j in range(k)]
    navs = [Navigator(e) for e in scouts]
    runner.SEG_START = scouts[0].load(state)
    free = seg in runner.REFILL_SOON
    search.HEARTS_FREE[0] = free; lookahead.CAUTION_OVERRIDE[0] = 0.12 if free else None
    t0 = time.time()
    best = search.parallel_search(scouts, navs, state, segs[i][1], segs[i][2], tries=tries, max_frames=3000, label=seg, log=print)
    print("search done:", best.frames if best else None, f"{time.time() - t0:.0f}s", flush=True)
    for e in scouts: e.close()
# replay every attempt, capturing frames
atts = sorted(dump.glob("attempt_*.json"))
print(len(atts), "attempts dumped", flush=True)
emu = BizHawk(log_name="wall_capture.log", clean_sram=False)
meta = []
for p in atts:
    a = json.loads(p.read_text())
    d = out / p.stem; d.mkdir(parents=True, exist_ok=True)
    want = (a["frames"] + 1) // 2
    if len(list(d.glob("*.png"))) >= want and want > 0:          # already filmed (the capture resumes after a pause)
        meta.append({"attempt": p.stem, "ok": a["ok"], "frames": a["frames"], "hearts_end": a["hearts"], "outcome": a["outcome"]})
        continue
    emu.load(state)
    hearts = []
    for j, b in enumerate(a["inputs"]):
        s = emu.step(tuple(x for x in b.split(",") if x), 1)
        if j % 2 == 0:                                      # 30 fps is plenty for a small window
            shutil.copyfile(emu.screenshot("_wall_tmp"), d / f"{j // 2:04d}.png")
        hearts.append(s.hearts)
    meta.append({"attempt": p.stem, "ok": a["ok"], "frames": a["frames"], "hearts_end": a["hearts"], "outcome": a["outcome"],
                 "hearts": hearts[::2]})
    print(p.stem, a["ok"], a["frames"], a["outcome"], flush=True)
(out / "meta.json").write_text(json.dumps(meta))
emu.close()
