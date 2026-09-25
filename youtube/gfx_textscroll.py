"""A terminal window scrolling the lines of a real text file (the planner's printed decisions, a log, a journal entry):
python youtube/gfx_textscroll.py <file> <seconds> <title> <out.mp4> [lines per second]"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).parent))
import gfx
from build import render_frames
src, dur, title, out = sys.argv[1], float(sys.argv[2]), sys.argv[3], Path(sys.argv[4])
lps = float(sys.argv[5]) if len(sys.argv) > 5 else 3.0
lines = [l.rstrip()[:150] for l in open(src, encoding="utf-8", errors="replace") if l.strip()]
ROWS = 36
def frames():
    n = gfx.nframes(dur)
    for v in range(n):
        top = int(v / gfx.FPS * lps)
        im, d = gfx.canvas()
        d.rectangle((24, 24, gfx.W - 24, gfx.H - 24), fill=(6, 8, 12), outline=(40, 48, 60))
        d.text((40, 34), title, font=gfx.FB[18], fill=gfx.GOLD)
        y = 64
        for k, line in enumerate(lines[top:top + ROWS]):
            col = gfx.TEXT if k == ROWS - 1 or top + k == len(lines) - 1 else gfx.DIM
            d.text((40, y), line, font=gfx.F[13], fill=gfx.GREEN if k == min(ROWS - 1, len(lines) - top - 1) else col)
            y += 17
        yield im
render_frames(frames(), out)
print("wrote", out)
