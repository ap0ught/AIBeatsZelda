"""'Things that broke': a 4 x 3 wall of real failure clips, each with its journal title, all playing at once; then one
cell is pulled forward. Input: youtube/broke.json = [{"title": ..., "video": path, "start": s, "dur": s, "crop": [w,h,x,y] or null}, ...]
usage: python youtube/gfx_broke.py [broke.json] [out.mp4]"""
import json, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).parent))
import gfx
from build import render_frames

cfg = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "youtube/broke.json"))
out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("youtube/clips_v3/broke_wall.mp4")
TITLE = sys.argv[3] if len(sys.argv) > 3 else "THINGS THAT BROKE"
out.parent.mkdir(parents=True, exist_ok=True)
COLS, ROWS = 4, 3
CW, CH = 300, 196
GAP = 12
def decode(c, w, h, n):
    vf = (f"crop={c['crop'][0]}:{c['crop'][1]}:{c['crop'][2]}:{c['crop'][3]}," if c.get("crop") else "") + f"scale={w}:{h}:flags=neighbor"
    cmd = ["ffmpeg", "-v", "error", "-ss", str(c["start"]), "-i", c["video"], "-frames:v", str(n), "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE); fr = []; sz = w * h * 3
    while True:
        raw = p.stdout.read(sz)
        if len(raw) < sz: break
        fr.append(Image.frombuffer("RGB", (w, h), raw))
    p.wait(); return fr
dur = max(c["dur"] for c in cfg)
n = int(round(dur * gfx.FPS))
def text_cell(c, w, h):
    """a journal excerpt instead of footage: the entry's title and a few of its real lines"""
    im = Image.new("RGB", (w, h), gfx.PANEL)
    d = ImageDraw.Draw(im)
    d.text((10, 8), c["head"], font=gfx.FB[16], fill=gfx.GOLD)
    import textwrap
    y = 34
    for line in c["text"]:
        for part in textwrap.wrap(line, 38) or [""]:
            d.text((10, y), part, font=gfx.F[13], fill=gfx.TEXT); y += 15
        y += 3
    return [im]
clips = [text_cell(c, CW, CH) if c.get("text") else decode(c, CW, CH, int(round(c["dur"] * gfx.FPS))) for c in cfg]
def frames():
    for v in range(n):
        im = Image.new("RGB", (gfx.W, gfx.H), gfx.BG)
        d = ImageDraw.Draw(im)
        d.text((gfx.W // 2, 20), TITLE, font=gfx.FB[22], fill=gfx.GOLD, anchor="mm")
        for i, (c, fr) in enumerate(zip(cfg, clips)):
            if not fr: continue
            x = GAP + (i % COLS) * (CW + GAP); y = 40 + (i // COLS) * (CH + 24 + GAP)
            im.paste(fr[v % len(fr)], (x, y))
            d.rectangle((x - 1, y - 1, x + CW, y + CH), outline=(50, 58, 72))
            d.text((x + CW // 2, y + CH + 11), c["title"], font=gfx.F[13], fill=gfx.TEXT, anchor="mm")
        yield im
render_frames(frames(), out)
print("wrote", out)
