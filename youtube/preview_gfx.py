"""One late frame from every generated animation, in a contact sheet, to check layout before rendering."""
import sys, itertools
sys.path.insert(0, "youtube")
import gfx
from PIL import Image
tests = [("title_card", 12, {}), ("rules_card", 12, {"upto": 5}), ("terminal", 10, {"which": "match"}), ("terminal", 14, {"which": "search"}),
         ("terminal", 12, {"which": "night"}), ("architecture", 16, {}), ("ramvision", 8, {}), ("tilelearn", 14, {}),
         ("quote", 12, {"who": "THE AI'S JOURNAL - ENTRY 6", "text": "A perfect player finishes this game without taking a single hit. Link is never too weak."}),
         ("lookahead", 24, {}), ("disclosure", 20, {}), ("disasm", 12, {}), ("breakdown", 12, {}), ("complaints", 16, {}),
         ("chart", 10, {"upto": 4, "wr": True, "gap": True}), ("wr_route", 20, {}), ("map", 12, {"mode": "reveal"}), ("map", 12, {"mode": "route3"}),
         ("map", 12, {"mode": "route4"}), ("handoff", 8, {})]
only = sys.argv[1:] 
ims = []
for name, dur, kw in tests:
    if only and name not in only:
        continue
    n = gfx.nframes(dur)
    want = {int(n * 0.45), n - 2}
    for k, im in enumerate(gfx.GEN[name](dur, **kw)):
        if k in want:
            ims.append(im.copy().resize((640, 360)))
    print(name, "ok", flush=True)
cols = 2
sheet = Image.new("RGB", (640 * cols, 360 * ((len(ims) + cols - 1) // cols)))
for i, im in enumerate(ims):
    sheet.paste(im, ((i % cols) * 640, (i // cols) * 360))
sheet.save("youtube/sheets/gfx_preview.png"); print(sheet.size)
