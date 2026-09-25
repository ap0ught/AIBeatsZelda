"""Render one of gfx.py's generators to a clip: python youtube/render_gen.py <name> <seconds> [k=v ...]"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import gfx
from build import render_frames
name, dur = sys.argv[1], float(sys.argv[2])
kw = dict(a.split("=", 1) for a in sys.argv[3:])
suffix = "".join("_" + v for v in kw.values())
out = Path("youtube/clips_v3") / f"{name}{suffix}.mp4"
out.parent.mkdir(parents=True, exist_ok=True)
render_frames(gfx.GEN[name](dur, **kw), out)
print("wrote", out)
