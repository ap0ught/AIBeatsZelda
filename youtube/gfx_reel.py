"""A reel of moments from a run's overlay video, each shown full-size (the 768x672 game area) with a title:
python youtube/gfx_reel.py reel.json out.mp4   where reel.json = [{"title": ..., "video": ..., "start": s, "dur": s}, ...]"""
import json, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).parent))
import gfx
from build import render_frames
cfg = json.load(open(sys.argv[1])); out = Path(sys.argv[2]); out.parent.mkdir(parents=True, exist_ok=True)
W2, H2 = 768, 672
def decode(c, n):
    cmd = ["ffmpeg", "-v", "error", "-ss", str(c["start"]), "-i", c["video"], "-frames:v", str(n), "-vf", "crop=768:672:0:24", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE); fr = []; sz = W2 * H2 * 3
    while True:
        raw = p.stdout.read(sz)
        if len(raw) < sz: break
        fr.append(Image.frombuffer("RGB", (W2, H2), raw))
    p.wait(); return fr
def frames():
    for c in cfg:
        fr = decode(c, int(round(c["dur"] * gfx.FPS)))
        for v, f in enumerate(fr):
            im = Image.new("RGB", (gfx.W, gfx.H), gfx.BG)
            im.paste(f, (32, 24)); d = ImageDraw.Draw(im)
            d.text((832, 60), c["title"], font=gfx.FB[22], fill=gfx.GOLD)
            y = 100
            import textwrap
            for line in c.get("lines", []):
                for part in textwrap.wrap(line, 44):
                    d.text((832, y), part, font=gfx.F[16], fill=gfx.TEXT); y += 22
                y += 6
            d.text((832, gfx.H - 40), c.get("foot", ""), font=gfx.F[13], fill=gfx.DIM)
            yield im
render_frames(frames(), out); print("wrote", out)
