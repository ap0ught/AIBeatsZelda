"""Where it stands: the six run times as bars against the 27:40 record line, each bar with its one-line reason, then
the time budget of run 6 (scrolls/menus/fanfares, fights, walking, items) as a stacked bar. usage: python youtube/gfx_stands.py [out]"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).parent))
import gfx
from build import render_frames

out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("youtube/clips_v3/stands.mp4")
out.parent.mkdir(parents=True, exist_ok=True)
RUNS = [("RUN 1", 102.35, "first finish: 609 segments, ten minutes of farming"), ("RUN 2", 57.67, "route rewritten, no farming, money from caves"),
        ("RUN 3", 41.25, "one night: go through monsters, not around them"), ("RUN 4", 39.25, "the planner's route"),
        ("RUN 5", 37.32, "the sword that went sideways, fixed"), ("RUN 6", 37.03, "a wider search: ninety attempts a room")]
WR = 27.67
BUDGET = [("scrolls, menus, fanfares", 16.52, gfx.DIM), ("fights", 12.08, gfx.RED), ("walking", 7.57, gfx.BLUE), ("bombs, candle, recorder", 1.69, gfx.SAND)]
def frames():
    n1 = int(9 * gfx.FPS); n2 = int(8 * gfx.FPS)
    for v in range(n1 + n2):
        im, d = gfx.canvas()
        if v < n1:
            t = v / gfx.FPS
            d.text((48, 30), "SIX RUNS, ONE RECORD", font=gfx.FB[26], fill=gfx.GOLD)
            x0, w = 200, 860; scale = w / 105.0
            for i, (name, mins, why) in enumerate(RUNS):
                y = 90 + i * 84
                a = gfx.ease((t - i * 1.1) / 0.8)
                d.text((48, y + 8), name, font=gfx.FB[20], fill=gfx.blend(gfx.TEXT, a))
                bw = int(mins * scale * a)
                d.rectangle((x0, y, x0 + bw, y + 34), fill=gfx.blend(gfx.GOLD if i == 5 else gfx.BLUE, 0.4 + 0.6 * a))
                if a > 0.9:
                    d.text((x0 + bw + 12, y + 8), f"{int(mins // 60)}:{int(mins % 60):02d}:{int(round((mins % 1) * 60)):02d}" if mins >= 60 else f"{int(mins)}:{int(round((mins % 1) * 60)):02d}", font=gfx.FB[20], fill=gfx.TEXT)
                    d.text((x0, y + 42), why, font=gfx.F[16], fill=gfx.DIM)
            xr = x0 + int(WR * scale)
            d.line((xr, 80, xr, 600), fill=gfx.RED, width=3)
            d.text((xr + 8, 604), "human record 27:40 (with glitches)", font=gfx.FB[16], fill=gfx.RED)
        else:
            t = (v - n1) / gfx.FPS
            d.text((48, 30), "RUN 6: WHERE THIRTY-SEVEN MINUTES GO", font=gfx.FB[26], fill=gfx.GOLD)
            total = sum(b for _, b, _ in BUDGET); x = 48; y = 200; w = 1184
            for i, (name, mins, col) in enumerate(BUDGET):
                a = gfx.ease((t - i * 0.8) / 0.8)
                bw = int(w * mins / total * a)
                d.rectangle((x, y, x + bw, y + 80), fill=gfx.blend(col, 0.5 + 0.5 * a))
                if a > 0.9:
                    anchor = "ra" if i == len(BUDGET) - 1 else "la"
                    lx = x + bw - 4 if i == len(BUDGET) - 1 else x + 8
                    d.text((lx, y + 92 + (i % 2) * 44), f"{name}", font=gfx.FB[16], fill=col, anchor=anchor)
                    d.text((lx, y + 114 + (i % 2) * 44), f"{int(mins)}:{int(round((mins % 1) * 60)):02d}", font=gfx.F[16], fill=gfx.TEXT, anchor=anchor)
                x += bw
            if t > 4:
                d.text((48, 420), "only a shorter route touches the first bar; the glitchless route cannot skip the fights", font=gfx.F[18], fill=gfx.DIM)
                d.text((48, 450), "the record route walks through a wall on its first screen. legal there; not here.", font=gfx.F[18], fill=gfx.DIM)
        yield im
render_frames(frames(), out)
print("wrote", out)
