"""The six-run race: the same room from every complete run, side by side, synced at the door; each window freezes
with its time when Link leaves the room. Input: youtube/race.json = {"title": ..., "runs": [{"label": "RUN 1  1:42:21",
"video": path, "start": s, "end": s}, ...]} (start/end in seconds of that overlay video). Clips are the LEFT 768x672
game area of each overlay, so the panel is not shown six times. usage: python youtube/gfx_race.py [race.json] [out.mp4]"""
import json, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).parent))
import gfx
from build import render_frames

cfg = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "youtube/race.json"))
out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("youtube/clips_v3/race.mp4")
out.parent.mkdir(parents=True, exist_ok=True)
runs = cfg["runs"]
COLS, ROWS = 3, 2
CW, CH = 400, 300                         # 768x672 game area scaled to fit
GAP = 16
def read_frames(run):
    """decode the game area of one run's overlay between start and end as 400x300 RGB frames"""
    n = int(round((run["end"] - run["start"]) * gfx.FPS))
    cmd = ["ffmpeg", "-v", "error", "-ss", str(run["start"]), "-i", run["video"], "-frames:v", str(n),
           "-vf", f"crop=768:672:0:24,scale={CW}:{CH}:flags=neighbor", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    fr = []
    sz = CW * CH * 3
    while True:
        raw = p.stdout.read(sz)
        if len(raw) < sz:
            break
        fr.append(Image.frombuffer("RGB", (CW, CH), raw))
    p.wait()
    return fr
clips = [read_frames(r) for r in runs]
longest = max(len(c) for c in clips)
def frames():
    hold = int(3 * gfx.FPS)
    for v in range(longest + hold):
        im = Image.new("RGB", (gfx.W, gfx.H), gfx.BG)
        d = ImageDraw.Draw(im)
        d.text((gfx.W // 2, 22), cfg["title"], font=gfx.FB[22], fill=gfx.GOLD, anchor="mm")
        for i, (r, c) in enumerate(zip(runs, clips)):
            x = GAP + (i % COLS) * (CW + GAP); y = 48 + (i // COLS) * (CH + 30 + GAP)
            j = min(v, len(c) - 1)
            im.paste(c[j], (x, y))
            done = v >= len(c)
            col = gfx.GREEN if done else gfx.TEXT
            d.text((x, y + CH + 6), r["label"], font=gfx.FB[16], fill=col)
            secs = min(v, len(c)) / gfx.FPS
            d.text((x + CW, y + CH + 6), f"{secs:5.1f} s" + ("  done" if done else ""), font=gfx.F[16], fill=col, anchor="ra")
            if done:
                d.rectangle((x - 2, y - 2, x + CW + 1, y + CH + 1), outline=gfx.GREEN, width=3)
        yield im
render_frames(frames(), out)
print("wrote", out, "longest", longest / gfx.FPS, "s")
