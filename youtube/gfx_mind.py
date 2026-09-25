"""Mind's eye: the real kept take of a fight (run 6) with what the planner saw at every decision drawn over it.
Left: the game at 2.5x. Over it: a box on every monster with its facing and hit points, a heat map of walking
distance to the strike spots, and at each decision a ghost Link at the end of every candidate future, coloured by
score, the chosen one solid. Right: the candidate list with scores.
Data: youtube/capture/mind/<seg>/frames/NNNN.png + decisions.json (capture_mind.py, film_inputs.py).
usage: python youtube/gfx_mind.py <segment> [out.mp4]"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
import gfx                                   # noqa: E402
from build import render_frames               # noqa: E402

seg = sys.argv[1]
out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("youtube/clips_v3") / f"mind_{seg}.mp4"
out.parent.mkdir(parents=True, exist_ok=True)
root = Path("youtube/capture/mind") / seg
d = json.load(open(root / "decisions.json"))
decisions = d["decisions"]
N = d["frames"]
S = 2.5                                      # game scale
GX, GY = 24, 24                              # game origin on the canvas
PX = GX + int(256 * S) + 24                  # panel x
Y_OFF = -8                                   # sprite centre sits at RAM y (calibrated with gfx_mind_calib.py)
NAMES = {0x0B: "Red Darknut", 0x0C: "Blue Darknut", 0x0F: "Red Leever", 0x10: "Blue Leever", 0x27: "Wallmaster",
         0x03: "Zol", 0x1F: "Keese", 0x2B: "Bubble", 0x23: "Wizzrobe", 0x24: "Red Wizzrobe", 0x06: "Goriya",
         0x2F: "Gibdo", 0x1E: "Armos"}
FACE = {1: (1, 0), 2: (-1, 0), 4: (0, 1), 8: (0, -1)}
DIRV = {"Right": (1, 0), "Left": (-1, 0), "Down": (0, 1), "Up": (0, -1)}


def g2c(x, y):
    """game object position (RAM x,y = sprite's top-left) -> canvas centre of its 16x16 box"""
    return GX + (x + 8) * S, GY + (y + Y_OFF + 8) * S


def colour(score, lo, hi):
    t = 0.0 if hi <= lo else max(0.0, min(1.0, (score - lo) / (hi - lo)))
    return (int(235 - 155 * t), int(70 + 160 * t), int(70 + 50 * t))


def frames():
    di = -1
    for k in range(N):
        while di + 1 < len(decisions) and decisions[di + 1]["frame"] <= k:
            di += 1
        dec = decisions[di] if di >= 0 else None
        im = Image.new("RGB", (gfx.W, gfx.H), gfx.BG)
        game = Image.open(root / "frames" / f"{k:04d}.png").convert("RGB").resize((int(256 * S), int(224 * S)), Image.NEAREST)
        im.paste(game, (GX, GY))
        ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        if dec:
            fmax = max((v for _, _, v in dec["field"]), default=1) or 1
            for x, y, v in dec["field"]:
                t = 1.0 - v / fmax
                cx, cy = g2c(x, y)
                od.rectangle((cx - 4 * S, cy - 4 * S, cx + 4 * S, cy + 4 * S), fill=(int(255 * t), int(120 * t), 0, int(70 * t)))
            for slot, typ, ex, ey, hp, face in dec["enemies"]:
                cx, cy = g2c(ex, ey)
                od.rectangle((cx - 8 * S, cy - 8 * S, cx + 8 * S, cy + 8 * S), outline=(255, 80, 80, 230), width=2)
                fx, fy = FACE.get(face, (0, 0))
                if fx or fy:
                    od.line((cx, cy, cx + fx * 14 * S, cy + fy * 14 * S), fill=(255, 80, 80, 230), width=3)
                od.text((cx - 8 * S, cy - 8 * S - 16), f"{NAMES.get(typ, hex(typ))} hp{hp}", font=gfx.F[13], fill=(255, 120, 120, 255))
            lx, ly, ldir = dec["link"]
            cx, cy = g2c(lx, ly)
            od.rectangle((cx - 8 * S, cy - 8 * S, cx + 8 * S, cy + 8 * S), outline=(80, 230, 120, 230), width=2)
            br = dec["branches"]
            scores = [b["score"] for b in br]
            lo, hi = min(scores), max(scores)
            for b in br:
                dx, dy = 0, 0
                if b["macro"] == "hold":
                    v = DIRV[b["dir"]]
                    dx, dy = v[0] * 12, v[1] * 12
                elif b["macro"] == "go_swing":
                    v = DIRV[b["dir"][0]]
                    dx, dy = v[0] * (b["n"] * 1.5), v[1] * (b["n"] * 1.5)
                gx, gy = g2c(lx + dx, ly + dy)
                col = colour(b["score"], lo, hi)
                chosen = [b["macro"], b["dir"], b["n"]] == dec["choice"]
                od.rectangle((gx - 8 * S, gy - 8 * S, gx + 8 * S, gy + 8 * S), fill=col + (150 if chosen else 55,),
                             outline=col + (255,), width=3 if chosen else 1)
                if b["macro"] in ("swing", "go_swing"):
                    sd = b["dir"] if b["macro"] == "swing" else b["dir"][1]
                    v = DIRV[sd]
                    od.line((gx, gy, gx + v[0] * 16 * S, gy + v[1] * 16 * S), fill=col + (255,), width=4 if chosen else 2)
        im = Image.alpha_composite(im.convert("RGBA"), ov).convert("RGB")
        dd = ImageDraw.Draw(im)
        dd.rectangle((PX - 8, 0, gfx.W, gfx.H), fill=gfx.PANEL)
        dd.text((PX, 16), "WHAT THE PLANNER SEES", font=gfx.FB[20], fill=gfx.GOLD)
        dd.text((PX, 44), f"frame {k:4d} of {N}   decision {max(di + 1, 0):2d} of {len(decisions)}", font=gfx.F[16], fill=gfx.TEXT)
        if dec:
            dd.text((PX, 72), f"Link ({dec['link'][0]},{dec['link'][1]})  hearts {dec['hearts']}  "
                              f"{'far mode' if dec['far'] else 'close quarters'}", font=gfx.F[13], fill=gfx.DIM)
            dd.text((PX, 98), "candidate futures, best first", font=gfx.F[13], fill=gfx.DIM)
            y = 118
            for b in dec["branches"][:16]:
                name = b["macro"] if b["macro"] != "go_swing" else "walk+swing"
                dr = b["dir"] if isinstance(b["dir"], str) else ("" if b["dir"] is None else ">".join(b["dir"]))
                chosen = [b["macro"], b["dir"], b["n"]] == dec["choice"]
                col = gfx.GOLD if chosen else gfx.TEXT
                mark = ">" if chosen else " "
                dd.text((PX, y), f"{mark} {name:10s} {dr:12s} {b['score']:8.1f}", font=gfx.F[16], fill=col)
                y += 20
            for j, line in enumerate(("boxes: read from memory, not pixels", "red line: which way the shield faces",
                                      "heat: walking distance to a strike spot", "ghosts: where each future ends, by score",
                                      "", "every 8 frames: snapshot, try them all,", "score, play the best one for real")):
                dd.text((PX, gfx.H - 150 + 18 * j), line, font=gfx.F[13], fill=gfx.DIM)
        yield im
        if dec and dec["frame"] == k:            # hold each decision for a beat so the futures can be read
            for _ in range(20):
                yield im


if __name__ == "__main__":
    render_frames(frames(), out)
    print("wrote", out)
