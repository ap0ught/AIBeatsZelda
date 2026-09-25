"""Where is Link's sprite in the 256x224 frame for a known RAM (x,y)? (calibrates gfx_mind.g2c)"""
import json
from PIL import Image
d = json.load(open("youtube/capture/mind/59_fight/decisions.json"))
for dec in d["decisions"][:6]:
    lx, ly, _ = dec["link"]; k = dec["frame"]
    im = Image.open(f"youtube/capture/mind/59_fight/frames/{k:04d}.png").convert("RGB")
    px = im.load(); pts = []
    for y in range(64, 224):
        for x in range(256):
            r, g, b = px[x, y]
            if g > 150 and r < 140 and b < 120:
                pts.append((x, y))
    if pts:
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        print(f"frame {k}: RAM link ({lx},{ly}) | green pixels x {min(xs)}-{max(xs)} y {min(ys)}-{max(ys)}")
