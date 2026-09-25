"""The sword that went sideways: the demonstration capture (same room, same frame, same button presses) played side by
side at 3x - old turn vs fixed turn - with the facing byte and the grid line explained. Data: youtube/capture/sideways/.
usage: python youtube/gfx_sideways.py [out.mp4]"""
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).parent))
import gfx
from build import render_frames

out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("youtube/clips_v3/sideways.mp4")
out.parent.mkdir(parents=True, exist_ok=True)
root = Path("youtube/capture/sideways")
meta = json.load(open(root / "meta.json"))
S = 2.25
W2 = int(256 * S); H2 = int(224 * S)
DIRN = {1: "RIGHT", 2: "LEFT", 4: "DOWN", 8: "UP"}
def frames():
    n = min(len(meta["old"]), len(meta["new"]))
    SLOW = 6                                # video frames per game frame (the swing is 16 frames long)
    hold = int(3 * gfx.FPS)
    for v in range(n * SLOW + hold):
        j = min(n - 1, v // SLOW)
        im, d = gfx.canvas()
        d.text((gfx.W // 2, 22), "SAME ROOM, SAME FRAME, SAME BUTTONS: PRESS UP, THEN ATTACK", font=gfx.FB[20], fill=gfx.GOLD, anchor="mm")
        for i, (tag, label) in enumerate((("old", "THE OLD SWING: up for one frame, then A"), ("new", "THE FIX: hold up until he faces up, then A"))):
            x0 = 24 + i * (W2 + 56)
            g = Image.open(root / tag / f"{j:04d}.png").convert("RGB").resize((W2, H2), Image.NEAREST)
            im.paste(g, (x0, 52))
            k, btn, lx, ly, ldir = meta[tag][j]
            d.text((x0, 52 + H2 + 10), label, font=gfx.FB[16], fill=gfx.GOLD if tag == "new" else gfx.RED)
            d.text((x0, 52 + H2 + 34), f"frame {k:2d}   pressing {btn or '-':5s}   Link x={lx}  (x mod 8 = {lx % 8})", font=gfx.F[16], fill=gfx.TEXT)
            d.text((x0, 52 + H2 + 56), f"facing byte = {ldir}  ({DIRN.get(ldir, '?')})", font=gfx.FB[16],
                   fill=gfx.GREEN if ldir == 8 else gfx.RED)
            # the grid line at x=128 and Link's x, drawn on the game
            gx = x0 + 128 * S
            d.line((gx, 52 + 64 * S, gx, 52 + H2), fill=(90, 160, 255), width=1)
            d.text((gx + 4, 52 + H2 - 18), "x=128", font=gfx.F[13], fill=(90, 160, 255))
        d.text((gfx.W // 2, gfx.H - 52), "Zelda only turns Link on an 8-pixel grid line. Off it, a one-frame press slides him sideways to the line first,",
               font=gfx.F[16], fill=gfx.DIM, anchor="mm")
        d.text((gfx.W // 2, gfx.H - 30), "still facing sideways - so the sword came out sideways. For ten days, about half of all perpendicular strikes.",
               font=gfx.F[16], fill=gfx.DIM, anchor="mm")
        d.text((gfx.W // 2, gfx.H - 10), "played at one sixth speed", font=gfx.F[13], fill=gfx.DIM, anchor="mm")
        yield im
render_frames(frames(), out)
print("wrote", out)
