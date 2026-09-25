"""The search wall: every real attempt at one room playing at once (8 x 6 = 48 windows, real game speed), a live
leaderboard on the right, windows freezing with their time as they finish, the winner going gold - then the winner's
take fills the screen. Data: youtube/capture/wall/<seg>/ (capture_wall.py).
usage: python youtube/gfx_wall.py <segment> [out.mp4]"""
import json, os, sys
from pathlib import Path
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).parent))
import gfx
from build import render_frames

seg = sys.argv[1]
out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("youtube/clips_v3") / f"wall_{seg}.mp4"
out.parent.mkdir(parents=True, exist_ok=True)
root = Path("youtube/capture/wall") / seg
meta = json.load(open(root / "meta.json"))
COLS, ROWS = 8, 6
CW, CH = 128, 112                      # 256x224 at half size
PANEL_X = COLS * CW                    # 1024
best = min(a["frames"] for a in meta if a["ok"])
winner = next(a["attempt"] for a in meta if a["ok"] and a["frames"] == best)
frames_of = {a["attempt"]: a for a in meta}
order = [a["attempt"] for a in meta][:COLS * ROWS]
longest = max(frames_of[a]["frames"] for a in order)
cache = {}

def png(att, j):
    """the j-th filmed frame (every 2nd game frame) of an attempt, cached small"""
    k = (att, j)
    if k not in cache:
        p = root / att / f"{j:04d}.png"
        if not p.exists():
            return None
        im = Image.open(p).convert("RGB").resize((CW, CH), Image.NEAREST)
        if len(cache) > 6000:
            cache.clear()
        cache[k] = im
    return cache[k]

def frames():
    hold = int(2.5 * gfx.FPS)
    total = longest + hold
    leader_font, small = gfx.F[16], gfx.F[13]
    for v in range(total):
        g = v                                         # game frames elapsed: real speed (60 game fps on 60 video fps)
        im = Image.new("RGB", (gfx.W, gfx.H), gfx.BG)
        d = ImageDraw.Draw(im)
        finished = []
        for idx, att in enumerate(order):
            a = frames_of[att]
            cx, cy = (idx % COLS) * CW, (idx // COLS) * CH
            n = a["frames"]
            j = min(g, n - 1) // 2
            tile = png(att, j)
            if tile is not None:
                im.paste(tile, (cx, cy))
            done = g >= n
            if done:
                finished.append((n, att))
                col = gfx.GOLD if att == winner else (gfx.GREEN if a["ok"] else gfx.RED)
                d.rectangle((cx, cy, cx + CW - 1, cy + CH - 1), outline=col, width=2)
                d.rectangle((cx + 2, cy + CH - 18, cx + CW - 3, cy + CH - 3), fill=(0, 0, 0))
                d.text((cx + CW // 2, cy + CH - 10), f"{n} f" if a["ok"] else "DIED", font=small, fill=col, anchor="mm")
            else:
                d.rectangle((cx, cy, cx + CW - 1, cy + CH - 1), outline=(40, 48, 60), width=1)
            d.text((cx + 3, cy + 2), f"{idx + 1}", font=small, fill=(255, 255, 255))
        # leaderboard
        d.rectangle((PANEL_X, 0, gfx.W, gfx.H), fill=gfx.PANEL)
        d.text((PANEL_X + 14, 12), "ONE ROOM, 48 ATTEMPTS", font=gfx.FB[18], fill=gfx.GOLD)
        d.text((PANEL_X + 14, 36), "same bookmark, different seed", font=small, fill=gfx.DIM)
        d.text((PANEL_X + 14, 58), f"game frame {min(g, longest):5d}   {min(g, longest) / 60.0988:5.1f} s", font=leader_font, fill=gfx.TEXT)
        d.text((PANEL_X + 14, 84), "finished, fastest first", font=small, fill=gfx.DIM)
        y = 102
        for n, att in sorted(finished)[:30]:
            col = gfx.GOLD if att == winner else gfx.TEXT
            d.text((PANEL_X + 14, y), f"#{order.index(att) + 1:2d}  {n:5d} frames  {n / 60.0988:4.1f} s", font=small, fill=col)
            y += 16
        if g >= longest:
            d.text((PANEL_X + 14, gfx.H - 60), "kept: the fastest", font=gfx.FB[18], fill=gfx.GOLD)
            d.text((PANEL_X + 14, gfx.H - 36), f"#{order.index(winner) + 1}, {best} frames, {best / 60.0988:.1f} s", font=leader_font, fill=gfx.GOLD)
        yield im
    # the winner fills the screen and plays its take
    n = frames_of[winner]["frames"]
    for v in range(n):
        im = Image.new("RGB", (gfx.W, gfx.H), gfx.BG)
        d = ImageDraw.Draw(im)
        p = root / winner / f"{v // 2:04d}.png"
        if p.exists():
            big = Image.open(p).convert("RGB").resize((768, 672), Image.NEAREST)
            im.paste(big, (32, 24))
        d.text((840, 60), "THE TAKE THAT WAS KEPT", font=gfx.FB[26], fill=gfx.GOLD)
        d.text((840, 100), f"attempt #{order.index(winner) + 1} of 48", font=gfx.F[20], fill=gfx.TEXT)
        d.text((840, 130), f"{best} frames = {best / 60.0988:.1f} seconds", font=gfx.F[20], fill=gfx.TEXT)
        d.text((840, 160), f"slowest attempt: {longest} frames", font=gfx.F[16], fill=gfx.DIM)
        d.text((840, 200), "every button of this take goes into the run;", font=gfx.F[16], fill=gfx.DIM)
        d.text((840, 222), "the other 47 are thrown away", font=gfx.F[16], fill=gfx.DIM)
        d.text((840, 262), f"frame {v:4d}", font=gfx.F[16], fill=gfx.TEXT)
        yield im

render_frames(frames(), out)
print("wrote", out)
